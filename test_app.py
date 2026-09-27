"""Run with python -m unittest -v test_app. Uses a temporary database, no paid API calls."""
import base64
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
import app

class WorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        app.DATA=Path(cls.temp.name);app.init()
        cls.server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        app.PORT=cls.server.server_address[1]
        cls.base='http://127.0.0.1:'+str(app.PORT)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.temp.cleanup()
    def request(self,path,data=None,headers=None,raw=False):
        hdr={'X-BD-Client':'1'}
        if data is not None:hdr.update({'Content-Type':'application/json','X-BD-Token':app.TOKEN})
        if headers:hdr.update(headers)
        req=urllib.request.Request(self.base+'/api/'+path,headers=hdr,data=json.dumps(data).encode() if data is not None else None)
        with urllib.request.urlopen(req) as r:return r.read() if raw else json.load(r)
    def save(self,kind,record):return self.request('save',{'kind':kind,'record':record})
    def test_01_reference_and_guard(self):
        state=self.request('state');s=[r for r in state['records'] if r['kind']=='suppliers']
        self.assertEqual(len(s),len(json.loads((app.ROOT/'seed/suppliers.json').read_text())))
        self.assertTrue(all(r['verified_date']=='' for r in s))
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('state',headers={'Host':'attacker.test'})
        self.assertEqual(e.exception.code,403)
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('save',{'kind':'actions','record':{'name':'Unsafe'}},headers={'Origin':'https://attacker.test'})
        self.assertEqual(e.exception.code,403)
        with self.assertRaises(urllib.error.HTTPError) as e:self.request('save',{'kind':'actions','record':{'name':'Unsafe'}},headers={'X-BD-Token':'wrong'})
        self.assertEqual(e.exception.code,403)
    def test_02_crud_and_conflict(self):
        r=self.save('opportunities',{'name':'Test opportunity اختبار','stage':'Qualified','value':200,'currency':'SAR','probability':25})
        self.assertEqual(r['value'],200)
        updated=self.request('save',{'kind':r['kind'],'id':r['id'],'version':r['version'],'record':{**r,'value':300}})
        self.assertEqual(updated['version'],2)
        with self.assertRaises(urllib.error.HTTPError):self.request('save',{'kind':r['kind'],'id':r['id'],'version':1,'record':r})
        self.assertEqual(next(x for x in self.request('state')['records'] if x['id']==r['id'])['value'],300)
        self.request('delete',{'id':r['id'],'version':2})
        self.assertFalse(any(x['id']==r['id'] for x in self.request('state')['records']))
    def test_03_validation(self):
        for r in [{'name':'Bad','website':'javascript:alert(1)'},{'name':'Bad','verified_date':'yesterday'}]:
            with self.assertRaises(urllib.error.HTTPError):self.save('suppliers',r)
        with self.assertRaises(urllib.error.HTTPError):self.save('opportunities',{'name':'Bad','value':-4})
    def test_04_exports_and_source_extraction(self):
        r=self.save('sources',{'name':'مصدر اختباري','content':'مرحبا\nCommercial evidence','enabled':True})
        data=self.request('export',{'kind':'sources','ids':[r['id']],'columns':['name','content'],'format':'xlsx'},raw=True)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in z.namelist():ET.fromstring(z.read(name))
            self.assertIn('مصدر اختباري',z.read('xl/worksheets/sheet1.xml').decode())
        doc=self.request('report',{'title':'تقرير','text':'A & B\nاختبار'},raw=True)
        with zipfile.ZipFile(io.BytesIO(doc)) as z:
            ET.fromstring(z.read('word/document.xml'))
        extracted=self.request('extract',{'name':'report.docx','data':base64.b64encode(doc).decode()})
        self.assertIn('A & B',extracted['text']);self.assertIn('اختبار',extracted['text'])
        self.assertIn("'=SUM",app.csv_bytes([{'name':'=SUM(1,2)'}],['name']).decode('utf-8-sig'))
    def test_05_backup_restore_and_files(self):
        r=self.save('accounts',{'name':'Backup account'})
        self.request('upload',{'record_id':r['id'],'name':'sample.txt','data':base64.b64encode(b'original file').decode()})
        backup=self.request('backup',raw=True)
        self.request('delete',{'id':r['id'],'version':r['version']})
        result=self.request('restore',{'data':base64.b64encode(backup).decode()})
        self.assertEqual(result['added'],1)
        a=self.request('attachments?id='+r['id']);self.assertEqual(len(a),1)
        self.assertEqual(self.request('file/'+a[0]['id'],raw=True),b'original file')
    def test_06_import_duplicates(self):
        result=self.request('import',{'kind':'actions','records':[{'name':'Unique imported action'},{'name':'Unique imported action'}]})
        self.assertEqual(result,{'added':1,'skipped':1})
    def test_07_research_source_scoping(self):
        allowed=self.save('sources',{'name':'Selected','url':'https://example.com/company','content':'SELECTED_EVIDENCE','enabled':True})
        disabled=self.save('sources',{'name':'Disabled','url':'https://other.example/','content':'DO_NOT_SEND','enabled':False})
        captured=[]
        response={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'Evidence [S1]. Source','annotations':[{'type':'url_citation','url':'https://example.com','title':'Source','start_index':15,'end_index':21}]}]}]}
        def fake(req,timeout):
            captured.append(json.loads(req.data));return io.BytesIO(json.dumps(response).encode())
        with patch.object(app,'AI_KEY','test-key'),patch.object(app.urllib.request,'urlopen',fake):
            for mode in ['local','domains','web']:
                result=app.research({'query':'Assess this supplier','mode':mode,'source_ids':[allowed['id'],disabled['id']],'consent':True})
                self.assertEqual(len(result['source_manifest']),1)
                sent=captured[-1];self.assertIn('SELECTED_EVIDENCE',sent['input']);self.assertNotIn('DO_NOT_SEND',sent['input'])
                if mode=='local':self.assertEqual(sent['tools'],[])
                elif mode=='domains':self.assertEqual(sent['tools'][0]['filters']['allowed_domains'],['example.com'])
                else:self.assertNotIn('filters',sent['tools'][0])
                self.assertFalse(sent['store'])
            with self.assertRaises(ValueError):app.research({'query':'No consent','mode':'web'})
        self.assertEqual(len(captured),3)

if __name__=='__main__':unittest.main()
