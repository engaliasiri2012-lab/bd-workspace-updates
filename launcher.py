"""Stable launcher installed once. Keeps data separate and restarts after updates."""
import json, os, subprocess, sys
from pathlib import Path
HOME_DIR=Path(__file__).resolve().parent

def main():
 while True:
  state=json.loads((HOME_DIR/'current.json').read_text(encoding='utf-8'))
  version=state['current']
  if not __import__('re').fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('Invalid installed version')
  folder=HOME_DIR/'versions'/version
  env={**os.environ,'BD_INSTALL_HOME':str(HOME_DIR)}
  result=subprocess.run([sys.executable,str(folder/'app.py')],cwd=folder,env=env)
  if result.returncode!=42:return result.returncode
if __name__=='__main__':
 try:sys.exit(main())
 except Exception as e:print('Unable to start BD Workspace:',e);input('Press Enter to close.')
