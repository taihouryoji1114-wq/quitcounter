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
 def test_store_settings_are_isolated(self):
  fake=Fake();manager=FireTrainingManager(fake)
  manager.save_profile({'store_name':'両国店','address':'東京都'},'shop-a')
  manager.set_check('extinguisher',True,'shop-a')
  self.assertEqual(manager.store_settings('shop-a')['profile']['store_name'],'両国店')
  self.assertTrue(manager.store_settings('shop-a')['checklist']['extinguisher'])
  self.assertEqual(manager.store_settings('shop-b')['profile']['store_name'],'')
 def test_role_plans_are_configurable(self):
  manager=FireTrainingManager(Fake());manager.save_role_plan(3,[{'role':'通報','detail':'119番'}])
  self.assertEqual(manager.store_settings()['role_plans']['3'][0]['role'],'通報')
if __name__=='__main__':unittest.main()
