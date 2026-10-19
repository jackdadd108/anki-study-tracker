import importlib.util, tempfile, zipfile, sqlite3, json, io, base64, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('server',Path(__file__).resolve().parents[1]/'server.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class MediaTest(unittest.TestCase):
 def test_media_mapping_and_unsafe_types(self):
  with tempfile.TemporaryDirectory() as t:
   old=m.ROOT;m.ROOT=Path(t);(m.ROOT/'static').mkdir()
   try:
    db=Path(t)/'test.db';c=sqlite3.connect(db);c.execute('create table col(models text)');c.execute('insert into col values(?)',(json.dumps({'1':{'flds':[{'name':'Front'},{'name':'Back'}]}}),));c.execute('create table notes(id integer,mid integer,flds text)');c.execute('insert into notes values(1,1,?)',('Question\x1fAnswer<img src="picture.png"><img src="bad.svg"><img src="https://example.com/private.png">',));c.commit();c.close();b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:
     z.writestr('collection.anki2',db.read_bytes());z.writestr('media',json.dumps({'0':'picture.png','1':'bad.svg'}));z.writestr('0',base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='));z.writestr('1','<svg onload="alert(1)"></svg>')
    _,cards=m.import_apkg(b.getvalue(),'Test');self.assertEqual(len(cards[0]['answer_images']),1);self.assertTrue((m.ROOT/'static'/cards[0]['answer_images'][0].lstrip('/')).exists());self.assertEqual(cards[0]['question_images'],[])
   finally:m.ROOT=old
if __name__=='__main__':unittest.main()
