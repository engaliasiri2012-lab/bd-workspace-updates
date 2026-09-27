"""One-time user installation. Does not delete or relocate the user's database."""
import json, os, shutil, subprocess, sys
from pathlib import Path
SOURCE=Path(__file__).resolve().parent
DEFAULT_FEED="https://raw.githubusercontent.com/engaliasiri2012-lab/bd-workspace-updates/main/latest.json"

def main():
 version=(SOURCE/'VERSION').read_text().strip()
 base=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))
 target=base/'MidadBDApp';versions=target/'versions';versions.mkdir(parents=True,exist_ok=True)
 dest=versions/version
 if not dest.exists():
  import tempfile
  staging=Path(tempfile.mkdtemp(prefix='install-',dir=versions))
  try:
   shutil.copytree(SOURCE,staging,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc','test_*.py','.git','releases','publishing'))
   os.replace(staging,dest)
  finally:
   if staging.exists():shutil.rmtree(staging)
 else:print('This version is already installed:',version)
 pointer=target/'current.json'
 previous=json.loads(pointer.read_text(encoding='utf-8')) if pointer.exists() else {}
 if not previous or tuple(map(int,version.split('.'))) >= tuple(map(int,previous['current'].split('.'))):
  shutil.copy2(SOURCE/'launcher.py',target/'launcher.py')
  if previous.get('current')!=version:
   import sqlite3,uuid
   database=base/'MidadBDWorkspace'/'workspace.sqlite3'
   if database.exists():
    backup_dir=database.parent/'update-backups';backup_dir.mkdir(exist_ok=True)
    with sqlite3.connect(database) as live,sqlite3.connect(backup_dir/('before-install-'+version+'-'+uuid.uuid4().hex[:8]+'.sqlite3')) as backup:live.backup(backup)
   new_pointer=pointer.with_suffix('.tmp')
   new_pointer.write_text(json.dumps({'current':version,'previous':previous.get('current')}),encoding='utf-8');os.replace(new_pointer,pointer)
 settings_dir=base/'MidadBDWorkspace';settings_dir.mkdir(exist_ok=True)
 settings_path=settings_dir/'update-settings.json'
 settings=json.loads(settings_path.read_text(encoding='utf-8')) if settings_path.exists() else {}
 if not settings.get('feed_url'):
  settings_path.write_text(json.dumps({**settings,'feed_url':DEFAULT_FEED}),encoding='utf-8')

 if os.name=='nt':
  import ctypes
  buf=ctypes.create_unicode_buffer(260)
  ctypes.windll.shell32.SHGetFolderPathW(None,0,None,0,buf)
  desktop=Path(buf.value)
  shortcut=desktop/'BD Workspace.cmd'
  shortcut.write_text('@echo off\nchcp 65001 >nul\n"'+sys.executable+'" "'+str(target/'launcher.py')+'"\npause\n',encoding='utf-8')
  print('Desktop shortcut created: BD Workspace')
 print('Installed in:',target)
 print('Your existing data stays in:',base/'MidadBDWorkspace')
 print('Stop any older running copy with Ctrl+C before starting this installation.')
 if '--no-start' not in sys.argv:subprocess.run([sys.executable,str(target/'launcher.py')])
if __name__=='__main__':main()
