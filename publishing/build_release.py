"""Build immutable public packages and the permanent update manifest. No user data.
Run from any directory after changing VERSION:
  python publishing/build_release.py --notes "Describe the update"
Commit source, both generated ZIPs and latest.json together. Never overwrite a published version.
"""
import argparse,hashlib,json,re,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='https://raw.githubusercontent.com/engaliasiri2012-lab/bd-workspace-updates/main'
p=argparse.ArgumentParser();p.add_argument('--notes',required=True);args=p.parse_args()
version=(ROOT/'VERSION').read_text().strip()
if not re.fullmatch(r'\d+\.\d+\.\d+',version):p.error('VERSION must be X.Y.Z')
if not (ROOT/'vendor/pypdf/__init__.py').exists():p.error('Install the bundled dependency first: python -m pip install -r requirements.txt --target vendor')
release_dir=ROOT/'releases';release_dir.mkdir(exist_ok=True)
update=release_dir/f'bd-{version}.zip';setup=release_dir/f'BD-Workspace-Setup-{version}.zip'
if update.exists() or setup.exists():p.error('Version package already exists. Use a new version for every published release.')
files=[ROOT/n for n in ['app.py','bd_features.py','updater.py','VERSION','README.md','START-HERE.html']]
for folder in ['web','templates','vendor']:
 files.extend(sorted(f for f in (ROOT/folder).rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.suffix!='.pyc'))
def build(path,prefix='',installer=False):
 with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED) as z:
  for file in files:z.write(file,prefix+file.relative_to(ROOT).as_posix())
  # All real company records are private local data, even if a developer has populated a seed.
  z.writestr(prefix+'seed/suppliers.json','[]\n')
  if installer:
   for name in ['install.py','launcher.py','INSTALL-ONCE.cmd','START-WINDOWS.cmd']:
    z.write(ROOT/name,prefix+name)
build(update);build(setup,'BD-Workspace/',True)
manifest={'version':version,'url':BASE+'/releases/'+update.name,'sha256':hashlib.sha256(update.read_bytes()).hexdigest(),'notes':args.notes}
(ROOT/'latest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'version':version,'update':str(update),'setup':str(setup),'sha256':manifest['sha256']},indent=2))
