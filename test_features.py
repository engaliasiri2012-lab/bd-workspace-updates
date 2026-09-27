"""Tests for document intake, paid-request boundaries, catalogue exports and evidence fields."""
import base64, io, json, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
import xml.etree.ElementTree as E
import app, bd_features as f

class FeatureTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=app.DATA;app.DATA=Path(self.tmp.name);app.init()
 def tearDown(self):app.DATA=self.old;self.tmp.cleanup()
 def test_extract_office_and_duplicates(self):
  x=app.xlsx_bytes([{'name':'مورد','contact':'sales@example.test'}],['name','contact'])
  self.assertIn('sales@example.test',f.extract(x,'a.xlsx')['text'])
  raw=app.docx_bytes('Meeting','PDC drill bits\nDrilling')
  b={'name':'meeting.docx','data':base64.b64encode(raw).decode(),'task':'partner'}
  a=f.ingest(app,b);again=f.ingest(app,b)
  self.assertEqual(a['record']['id'],again['record']['id']);self.assertTrue(again['duplicate'])
  with app.db() as c:self.assertEqual(c.execute('select count(*) from attachments where record_id=?',(a['record']['id'],)).fetchone()[0],1)
  with self.assertRaises(ValueError):f.extract(b'data','old.xls')
 def test_schema_and_research_pipeline(self):
  source=app.store('sources',{'name':'Reference','content':'Provided evidence','enabled':True})
  candidate={k:'' for k in f.FIELDS};candidate.update(name='Example Engineering',country='UK',award_status='awarded',awards='Example award, 2024, Example organiser',award_evidence='https://example.test/award',aramco_status='vendor_registration',saudi_status='unknown',innovation_status='unknown')
  responses=[{'status':'completed','output':[{'content':[{'type':'output_text','text':'Research evidence [S1] https://example.test/award','annotations':[]}]}]}, {'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps({'summary':'Draft evidence','candidates':[candidate,candidate]}),'annotations':[]}]}]}]
  captured=[]
  def fake(req,timeout):captured.append(json.loads(req.data));return io.BytesIO(json.dumps(responses.pop(0)).encode())
  with patch.object(app,'AI_KEY','mock'),patch.object(app.urllib.request,'urlopen',fake):
   result=f.discover(app,{'query':'Award winning drilling','mode':'web','source_ids':[source['id']],'consent':True,'criteria':{'awards':True,'aramco':True},'criteria_logic':'any'})
  self.assertEqual(len(result['candidates']),1);self.assertTrue(result['criteria']['awards'])
  self.assertEqual(captured[0]['tools'][0]['type'],'web_search');self.assertEqual(captured[1]['tools'],[])
  self.assertEqual(captured[1]['text']['format']['type'],'json_schema')
  self.assertIn('vendor_registration',f.schema()['properties']['candidates']['items']['properties']['aramco_status']['enum'])
  self.assertEqual(len(app.records('research')),1)
  with patch.object(app,'AI_KEY','mock'),patch.object(app.urllib.request,'urlopen') as network:
   with self.assertRaises(ValueError):f.discover(app,{'query':'No consent'})
   network.assert_not_called()
 def test_failed_format_preserves_research(self):
  raw=app.store('research',{'name':'Saved search','answer':'Evidence','source_manifest':[],'discovery_pending':True})
  with patch.object(app,'research',return_value={'answer':'invalid JSON','status':'completed'}):
   with self.assertRaises(ValueError):f.structure(app,raw)
  self.assertEqual(app.records('research')[0]['answer'],'Evidence')
 def test_financial_formula(self):
  r={'tam':'20000000','market_share':'15','gross_margin':'30','currency':'USD','financial_basis':'Annual estimate'}
  self.assertEqual(f.gp(r),'USD 900,000.00')
  self.assertEqual(f.gp({**r,'market_share':'150'}),'');self.assertEqual(f.gp({**r,'financial_basis':''}),'')
 def test_pptx_and_report_content(self):
  row={k:'' for k in f.FIELDS};row.update(name='Example Company',opportunity='Drill tools',sources='https://example.test/reference',products='A long description '+('extended specification '*150),technology_edge='Test only')
  result=app.store('research',{'name':'Test catalogue','summary':'Test output, not commercial findings','candidates':[row],'source_manifest':[{'label':'S1','name':'Test source'}]})
  raw=f.pptx_bytes(app,result,[row])
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   names=[n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
   texts=[]
   for n in names:
    root=E.fromstring(z.read(n));texts.extend(x.text or '' for x in root.iter() if x.tag.endswith('}t'))
   joined='\n'.join(texts);self.assertNotIn('{{',joined);self.assertIn('Example Company',joined)
   self.assertEqual(joined.count('extended'),150);self.assertEqual(joined.count('specification'),150)
   for n in z.namelist():
    if n.endswith(('.xml','.rels')):E.fromstring(z.read(n))
  title,text=f.report_text(result,[row],True);self.assertIn('الشركة',text);self.assertIn('https://example.test/reference',text)
 def test_pdf_reader(self):
  from pypdf import PdfWriter
  writer=PdfWriter();writer.add_blank_page(width=200,height=200);out=io.BytesIO();writer.write(out)
  result=f.extract(out.getvalue(),'scan.pdf');self.assertTrue(result['warnings']);self.assertEqual(result['sections'],1)
if __name__=='__main__':unittest.main()
