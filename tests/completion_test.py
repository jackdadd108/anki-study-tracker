import importlib.util, unittest, copy
from pathlib import Path
spec=importlib.util.spec_from_file_location('server',Path(__file__).resolve().parents[1]/'server.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class CompletionTest(unittest.TestCase):
 def test_idempotency_revision_and_mark(self):
  data={'decks':[{'id':'d','current_index':0}],'cards':[{'id':'c','deck_id':'d'}],'attempts':[]}
  event={'id':'one','deck_id':'d','card_id':'c','correct_option':'A','selected_option':'A','current_index':1}
  m.record_completion(data,event);snapshot=copy.deepcopy(data);m.record_completion(data,event);self.assertEqual(snapshot,data);self.assertEqual(data['attempts'][0]['study_kind'],'new');self.assertTrue(data['attempts'][0]['is_correct'])
  event['id']='two';m.record_completion(data,event);self.assertEqual(len(data['attempts']),2);self.assertEqual(data['attempts'][1]['study_kind'],'revision')
  event.update(id='three',correct_option=None);m.record_completion(data,event);m.record_completion(data,event);self.assertEqual(len(data['daily_completions']),1);self.assertEqual(len(data['attempts']),2);self.assertEqual(data['daily_completions'][0]['study_kind'],'revision')
  self.assertEqual(data['decks'][0]['current_index'],1)
if __name__=='__main__':unittest.main()
