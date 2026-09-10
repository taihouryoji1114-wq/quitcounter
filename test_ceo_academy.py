from pathlib import Path
import unittest
ROOT=Path(__file__).parent/'static'/'ceo-academy'
class CEOAcademyTests(unittest.TestCase):
 def test_files(self):
  for f in ('index.html','style.css','game.js'): self.assertTrue((ROOT/f).exists())
 def test_question_bank(self):
  js=(ROOT/'game.js').read_text();self.assertGreaterEqual(js.count("],\n['"),20);self.assertIn('間違えた問題を復習',(ROOT/'index.html').read_text())
 def test_learning_state(self):
  js=(ROOT/'game.js').read_text();self.assertIn('localStorage',js);self.assertIn('lesson',js);self.assertIn('source',js)
if __name__=='__main__':unittest.main()
