"""Manually confirmed shifts, independent of requests and generated schedules."""
from calendar import monthrange
from copy import deepcopy
from datetime import date
from core.clock import now_jst
from core.data import data
from core.staffing import StaffingManager


class ShiftBoardManager:
    STAFF = StaffingManager.STAFF

    def __init__(self, data_manager=None):
        self.data = data_manager or data

    @staticmethod
    def key(year, month):
        return date(int(year), int(month), 1).strftime('%Y-%m')

    def month(self, year, month):
        return deepcopy(self.data.data.get('store_manual_shift_board', {}).get(
            self.key(year, month), {'draft': {}, 'published': None}))

    def save_staff(self, year, month, staff, entries):
        if staff not in self.STAFF:
            raise ValueError('スタッフを選択してください')
        key = self.key(year, month)
        last = monthrange(int(year), int(month))[1]
        cleaned = {}
        for day, text in entries.items():
            if not str(day).isdigit() or not 1 <= int(day) <= last:
                raise ValueError('日付が正しくありません')
            text = str(text).strip()
            if len(text) > 100:
                raise ValueError('勤務内容は100文字以内で入力してください')
            if text:
                cleaned[str(int(day))] = text
        board = self.month(year, month)
        board['draft'][staff] = cleaned
        self.data.data.setdefault('store_manual_shift_board', {})[key] = board
        self.data.save()

    def publish(self, year, month):
        board = self.month(year, month)
        if not any(board['draft'].values()):
            raise ValueError('先に勤務予定か「休み」を入力・保存してください')
        board['published'] = {'entries': deepcopy(board['draft']),
                              'updated_at': now_jst().strftime('%Y/%m/%d %H:%M')}
        self.data.data.setdefault('store_manual_shift_board', {})[self.key(year, month)] = board
        self.data.save()


shift_board = ShiftBoardManager()
