import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from reportlab.platypus import PageBreak
from core.financial_report_data import build_financial_report
from core.financial_report_pdf import create_financial_report_pdf

class MonthlyLayoutTests(unittest.TestCase):
    def test_genres_start_on_separate_pages(self):
        report=build_financial_report('2026-10-01','2026-10-31')
        with tempfile.TemporaryDirectory() as folder, patch('core.financial_report_pdf.SimpleDocTemplate.build') as build:
            create_financial_report_pdf(Path(folder)/'report.pdf',report)
        sections=[[]]
        for item in build.call_args.args[0]:
            if isinstance(item,PageBreak):sections.append([])
            else:sections[-1].append(item)
        titles=[[getattr(item,'text','') for item in items] for items in sections]
        self.assertEqual(len(titles),5)
        self.assertIn('重要な経営比率',titles[0])
        self.assertIn('利益ブロック',titles[0])
        self.assertEqual([v[0] for v in titles[1:]],['営業経費の内訳','決済方法別集計','仕入れ先別集計','日別売上明細'])
