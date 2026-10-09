import unittest
from pages.shift_submission import submission_overview_html

class SubmissionOverviewTest(unittest.TestCase):
    def test_compact_cells_and_partial_times(self):
        period={'year':2026,'month':10,'start':1,'end':15}
        html=submission_overview_html(period,{'スタッフA':{'days':{'1':{'type':'ランチ','start':'11:00','end':''},'2':{'type':'ディナー','start':'','end':'22:00'},'3':{'type':'通し'}}}})
        self.assertIn('11:00〜',html)
        self.assertIn('22:00',html)
        self.assertNotIn('未指定',html)
        self.assertNotIn('副社長',html)
        self.assertIn('Ha',html)
        self.assertIn('class="both"',html)
        self.assertEqual(html.count('<tr>'),16)
        self.assertNotIn('colspan',html)
        self.assertIn('未提出',html)

    def test_time_content_is_escaped(self):
        html=submission_overview_html({'year':2026,'month':10,'start':1,'end':1},{'スタッフA':{'days':{'1':{'type':'ランチ','start':'<img>','end':''}}}})
        self.assertNotIn('<img>',html)
        self.assertIn('&lt;img&gt;',html)
