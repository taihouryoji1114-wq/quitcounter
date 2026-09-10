from pathlib import Path
import unittest

ROOT=Path(__file__).parent/'static'/'miniature-war'
class MiniatureWarTests(unittest.TestCase):
    def test_assets_exist(self):
        for name in ('index.html','style.css','game.js'): self.assertTrue((ROOT/name).exists())
    def test_armies_are_fifty_each(self):
        js=(ROOT/'game.js').read_text()
        self.assertIn('for(let i=0;i<50;i++)',js)
        self.assertIn("i<20?'spear':i<40?'sword':'archer'",js)
    def test_tactical_systems(self):
        js=(ROOT/'game.js').read_text()
        for feature in ('morale','flank','shoot','battleOver'): self.assertIn(feature,js)
if __name__=='__main__': unittest.main()
