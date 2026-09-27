"""HTTPS release feed, versioned installation, SQLite snapshot and rollback."""
import hashlib, io, json, os, re, shutil, tempfile, threading, urllib.parse, urllib.request, uuid, zipfile
from pathlib import Path
LOCK=threading.Lock()
MAX_PACKAGE=25*1024*1024
DEFAULT_FEED="https://raw.githubusercontent.com/engaliasiri2012-lab/bd-workspace-updates/main/latest.json"

def version_tuple(value):
 if not isinstance(value,str) or not re.fullmatch(r'\d+\.\d+\.\d+',value):raise ValueError('Version must have the form 2.0.1.')
 return tuple(map(int,value.split('.')))

def install_home():
 path=os.environ.get('BD_INSTALL_HOME')
 return Path(path).resolve() if path else None

def json_read(path,default):
 try:return json.loads(path.read_text(encoding='utf-8'))
 except FileNotFoundError:return default

def atomic_json(path,data):
 temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
 temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(temp,path)

def status(app):
 home=install_home();settings=json_read(app.DATA/'update-settings.json',{})
 current=(app.ROOT/'VERSION').read_text().strip()
 pointer=json_read(home/'current.json',{}) if home else {}
 return {'installed':bool(home and pointer),'running_version':current,'active_version':pointer.get('current',current),'previous_version':pointer.get('previous'),'feed_url':settings.get('feed_url',DEFAULT_FEED),'restart_required':pointer.get('current',current)!=current}

def https_url(url):
 p=urllib.parse.urlsplit(url)
 if p.scheme!='https' or not p.hostname or p.username or p.password:raise ValueError('Use an HTTPS update-feed URL without credentials.')
 return url

def fetch(url,limit):
 req=urllib.request.Request(https_url(url),headers={'User-Agent':'BD-Workspace-Updater/2.0'})
 try:
  with urllib.request.urlopen(req,timeout=90) as r:
   https_url(r.geturl())
   data=r.read(limit+1)
 except Exception as e:
  if isinstance(e,ValueError):raise
  raise ValueError('Could not download the update. Check the update address and internet connection.') from e
 if len(data)>limit:raise ValueError('Update file exceeds the permitted download size.')
 return data

def check(app):
 s=status(app)
 if not s['feed_url']:raise ValueError('An update source has not been connected yet. Configure its permanent HTTPS manifest URL once.')
 try:m=json.loads(fetch(s['feed_url'],1024*1024))
 except (json.JSONDecodeError,UnicodeError):raise ValueError('The update address did not return a valid release manifest.')
 version_tuple(m.get('version'));https_url(m.get('url',''))
 if not re.fullmatch('[a-fA-F0-9]{64}',str(m.get('sha256',''))):raise ValueError('The release is missing a SHA-256 checksum.')
 return {**s,'available':version_tuple(m['version'])>version_tuple(s['active_version']),'release':{'version':m['version'],'url':m['url'],'sha256':m['sha256'].lower(),'notes':str(m.get('notes',''))[:10000]}}

def unpack_package(raw,dest,version):
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  if len(z.infolist())>3000 or sum(x.file_size for x in z.infolist())>100*1024*1024:raise ValueError('Expanded update is too large.')
  allowed_files={'app.py','bd_features.py','updater.py','VERSION','README.md','START-HERE.html'}
  seen=set()
  for info in z.infolist():
   p=Path(info.filename)
   if '\\' in info.filename or p.is_absolute() or '..' in p.parts or ':' in info.filename:raise ValueError('Unsafe update path.')
   if info.filename in seen:raise ValueError('Duplicate file in update.')
   seen.add(info.filename)
   if (info.external_attr>>16)&0o170000==0o120000:raise ValueError('Update contains a symbolic link.')
   if info.is_dir():continue
   if len(p.parts)==1 and p.name not in allowed_files:raise ValueError('Unexpected update file: '+p.name)
   if len(p.parts)>1 and p.parts[0] not in ('web','templates','vendor','seed'):raise ValueError('Unexpected update folder.')
   if p.parts[0]=='seed' and str(p).replace('\\','/')!='seed/suppliers.json':raise ValueError('Private source documents must not be distributed in update packages.')
   target=dest/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(info))
  required=['app.py','bd_features.py','updater.py','VERSION','web/index.html','web/app.js','web/features.js','templates/catalogue.pptx','templates/catalogue-summary.pptx','seed/suppliers.json']
  if any(not (dest/p).is_file() for p in required):raise ValueError('Update package is incomplete.')
  if (dest/'VERSION').read_text().strip()!=version:raise ValueError('Package version does not match its manifest.')
  for p in dest.glob('*.py'):compile(p.read_text(encoding='utf-8'),str(p),'exec')

def apply(app,b):
 if not LOCK.acquire(blocking=False):raise ValueError('Another update operation is running.')
 staging=None
 try:
  info=check(app);home=install_home()
  if not info['installed']:raise ValueError('Run the one-time installer first: py -3 install.py')
  if not info['available']:raise ValueError('No newer release is available.')
  release=info['release']
  if release['version']!=b.get('version') or release['sha256']!=b.get('sha256'):raise ValueError('The release changed. Check for updates again.')
  raw=fetch(release['url'],MAX_PACKAGE)
  if hashlib.sha256(raw).hexdigest()!=release['sha256']:raise ValueError('Checksum mismatch. Update rejected; your current version is unchanged.')
  versions=home/'versions';versions.mkdir(exist_ok=True)
  staging=Path(tempfile.mkdtemp(prefix='stage-',dir=versions));unpack_package(raw,staging,release['version'])
  dest=versions/release['version']
  if dest.exists():raise ValueError('This version already exists locally. Use rollback or ask for a release with a new version number.')
  # Back up the live SQLite database using its online backup interface.
  backup_dir=app.DATA/'update-backups';backup_dir.mkdir(exist_ok=True)
  backup=backup_dir/('before-'+release['version']+'-'+uuid.uuid4().hex[:8]+'.sqlite3')
  with app.db() as source,app.sqlite3.connect(backup) as target:source.backup(target)
  os.replace(staging,dest);staging=None
  pointer=json_read(home/'current.json',{})
  atomic_json(home/'current.json',{'current':release['version'],'previous':pointer['current']})
  return {**status(app),'backup':str(backup)}
 finally:
  if staging and staging.exists():shutil.rmtree(staging)
  LOCK.release()

def rollback(app):
 if not LOCK.acquire(blocking=False):raise ValueError('Another update operation is running.')
 try:
  home=install_home()
  if not home:raise ValueError('A managed installation is required.')
  pointer=json_read(home/'current.json',{});previous=pointer.get('previous')
  if not previous or not (home/'versions'/previous/'app.py').exists():raise ValueError('No previous installed version is available.')
  version_tuple(previous)
  atomic_json(home/'current.json',{'current':previous,'previous':pointer['current']})
  return status(app)
 finally:LOCK.release()

def handle(app,h,path,b):
 if path=='/api/update/status':h.send(status(app));return True
 if path=='/api/update/settings':
  url=str(b.get('feed_url','')).strip()
  if url:https_url(url)
  atomic_json(app.DATA/'update-settings.json',{'feed_url':url});h.send(status(app));return True
 if path=='/api/update/check':h.send(check(app));return True
 if path=='/api/update/apply':h.send(apply(app,b));return True
 if path=='/api/update/rollback':h.send(rollback(app));return True
 if path=='/api/update/restart':
  if not install_home():raise ValueError('Use the installed desktop shortcut to restart automatically.')
  if app.AI_LOCK.locked() or LOCK.locked():raise ValueError('Wait for the active research or update to finish.')
  h.send({'restarting':True});app.EXIT_CODE=42;threading.Timer(1,h.server.shutdown).start();return True
 return False
