import hashlib,io,json,os,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import app,updater
class UpdateTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.old=app.DATA;app.DATA=self.base/'data';app.init();self.sentinel=app.store('accounts',{'name':'Existing local account'})
  self.home=self.base/'installed';(self.home/'versions'/'2.0.0').mkdir(parents=True)
  (self.home/'versions'/'2.0.0'/'app.py').write_text('# old')
  updater.atomic_json(self.home/'current.json',{'current':'2.0.0','previous':None})
  updater.atomic_json(app.DATA/'update-settings.json',{'feed_url':'https://example.test/latest.json'})
  self.env=patch.dict(os.environ,{'BD_INSTALL_HOME':str(self.home)});self.env.start()
 def tearDown(self):self.env.stop();app.DATA=self.old;self.tmp.cleanup()
 def package(self):
  out=io.BytesIO()
  with zipfile.ZipFile(out,'w') as z:
   for n in ['app.py','bd_features.py','updater.py']:z.writestr(n,'# validated Python source\n')
   for n in ['web/index.html','web/app.js','web/features.js','templates/catalogue.pptx','templates/catalogue-summary.pptx','seed/suppliers.json']:z.writestr(n,'fixture')
   z.writestr('VERSION','999.0.0')
  return out.getvalue()
 def test_update_backup_and_rollback(self):
  raw=self.package();release={'version':'999.0.0','url':'https://example.test/bd.zip','sha256':hashlib.sha256(raw).hexdigest()}
  with patch.object(updater,'fetch',side_effect=[json.dumps(release).encode(),raw]):result=updater.apply(app,release)
  self.assertEqual(result['active_version'],'999.0.0');self.assertTrue(result['restart_required']);self.assertTrue(Path(result['backup']).exists())
  self.assertEqual(updater.rollback(app)['active_version'],'2.0.0')
  self.assertEqual(app.records('accounts')[0]['id'],self.sentinel['id'])
  self.assertEqual(len(app.records('suppliers')),len(json.loads((app.ROOT/'seed/suppliers.json').read_text())))
 def test_checksum_rejection(self):
  release={'version':'999.0.0','url':'https://example.test/bd.zip','sha256':'0'*64}
  with patch.object(updater,'fetch',side_effect=[json.dumps(release).encode(),self.package()]):
   with self.assertRaises(ValueError):updater.apply(app,release)
  self.assertEqual(updater.status(app)['active_version'],'2.0.0')
 def test_unsafe_zip_rejected(self):
  out=io.BytesIO()
  with zipfile.ZipFile(out,'w') as z:z.writestr('../outside.py','bad')
  with self.assertRaises(ValueError):updater.unpack_package(out.getvalue(),self.base/'staging','999.0.0')
  self.assertFalse((self.base/'outside.py').exists())
 def test_no_feed_and_non_https(self):
  with self.assertRaises(ValueError):updater.https_url('http://example.test/feed')
  updater.atomic_json(app.DATA/'update-settings.json',{'feed_url':''})
  with self.assertRaises(ValueError):updater.check(app)
if __name__=='__main__':unittest.main()
