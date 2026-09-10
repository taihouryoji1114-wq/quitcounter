import unittest
from core.fire_training import COURSE_URL,FireTrainingManager
class Fake:
 def __init__(self):self.data={};self.saved=0
 def save(self):self.saved+=1
class FireTrainingTests(unittest.TestCase):
 def test_official_url(self):self.assertTrue(COURSE_URL.startswith('https://www.tfd.metro.tokyo.lg.jp/'))
 def test_completion(self):
  fake=Fake();manager=FireTrainingManager(fake);record=manager.complete('スタッフA')
  self.assertEqual(record['staff_name'],'スタッフA');self.assertEqual(fake.saved,1);self.assertIn('スタッフA',manager.completions())
 def test_name_required(self):
  with self.assertRaises(ValueError):FireTrainingManager(Fake()).complete('')
if __name__=='__main__':unittest.main()
