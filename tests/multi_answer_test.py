import json,sys,copy,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import answers,server
class MultiAnswerTest(unittest.TestCase):
 def test_parsing_and_grading(self):
  for f in json.loads(Path(__file__).with_name('multi-answer-fixtures.json').read_text()):
   with self.subTest(f['name']):self.assertEqual(answers.resolve(f['card'],f['card']['options']),f['expected'])
  self.assertTrue(answers.grade(['C'],['A','C','D']))
  self.assertFalse(answers.grade(['B'],['A','C','D']))
  self.assertFalse(answers.grade(['A','B','C','D'],['A','C','D']))
 def test_one_submission_one_attempt(self):
  data={'cards':[{'id':'c','deck_id':'d'}],'decks':[{'id':'d'}],'attempts':[]}
  event={'id':'once','deck_id':'d','card_id':'c','selected_options':['C'],'correct_options':['A','C','D'],'current_index':1}
  server.record_completion(data,event);server.record_completion(data,event)
  self.assertEqual(len(data['attempts']),1);self.assertTrue(data['attempts'][0]['is_correct']);self.assertEqual(data['attempts'][0]['selected_option'],'C')
  server.record_completion(data,dict(event,id='revision',selected_options=['B']))
  self.assertEqual(len(data['attempts']),2);self.assertFalse(data['attempts'][1]['is_correct'])
  server.record_completion(data,dict(event,id='mark',correct_options=None))
  self.assertEqual(len(data['attempts']),2);self.assertEqual(len(data['daily_completions']),1)
if __name__=='__main__':unittest.main()
