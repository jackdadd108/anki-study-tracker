import sys,tempfile,json,unittest,time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import review_sync as r,anki_bridge as b
class ReviewsTest(unittest.TestCase):
 def test_history_native_and_retry(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'journal.json';path.write_text(json.dumps({'profile':'test','enabled_at_ms':r.timestamp('2026-10-16T10:00:00Z'),'records':{}}))
   note={'noteId':1,'cards':[10],'fields':{'Front':{'value':'Q'}},'tags':[]};data={'cards':[{'id':'c','deck_id':'d','question':'Q'}],'attempts':[{'id':'old','card_id':'c','deck_id':'d','answered_at':'2026-10-15T10:00:00Z','is_correct':False},{'id':'new','card_id':'c','deck_id':'d','answered_at':'2026-10-16T11:00:00Z','is_correct':True}]};logs=[];native_calls=[]
   def call(action,**params):
    if action=='getReviewsOfCards':return {'10':list(logs)}
    if action=='insertReviews':
     for row in params['reviews']:logs.append({'id':row[0],'ease':row[3]})
    elif action=='answerCards':
     native_calls.append(params);logs.append({'id':int(time.time()*1000),'ease':params['answers'][0]['ease']});return [True]
   with patch.object(r,'JOURNAL',path),patch.object(b,'call',side_effect=call),patch.dict(b.CACHE,{'notes':[note]}):
    result=r.sync(data,b.index_notes([note]),'test');self.assertEqual(result['history_imported'],1);self.assertEqual(result['reviews_recorded'],1);self.assertEqual(native_calls[0]['answers'],[{'cardId':10,'ease':3}]);r.sync(data,b.index_notes([note]),'test');self.assertEqual(len(logs),2);self.assertEqual(len(native_calls),1)
    # A lost scheduler response must never trigger another answerCards call.
    j=json.loads(path.read_text());j['records']['new']['state']='pending';j['records']['new']['before']=[];j['records']['new']['started_ms']=0;path.write_text(json.dumps(j));r.sync(data,b.index_notes([note]),'test');self.assertEqual(len(native_calls),1)
    with self.assertRaises(RuntimeError):r.sync(data,b.index_notes([note]),'other-profile')
if __name__=='__main__':unittest.main()
