"""Manually confirmed shifts, independent of requests and generated schedules."""
from calendar import monthrange
from copy import deepcopy
from datetime import date
from core.clock import now_jst
from core.data import data
from core.staffing import StaffingManager


class ShiftBoardManager:
    STAFF = tuple(s for s in StaffingManager.STAFF if s != "副社長")

    def __init__(self, data_manager=None):
        self.data = data_manager or data

    @staticmethod
    def key(year, month):
        return date(int(year), int(month), 1).strftime('%Y-%m')

    def month(self, year, month):
        key = self.key(year, month)
        board = deepcopy(self.data.data.get('store_manual_shift_board', {}).get(
            key, {'draft': {}, 'published': None}))
        published = board.get('published')
        changed = False
        if published:
            cells = published.setdefault('cells', {})
            for staff, entries in published.get('entries', {}).items():
                if staff not in self.STAFF:
                    continue
                for day, text in entries.items():
                    if day not in cells.setdefault(staff, {}):
                        # One-time backfill uses accepted submissions, never pending requests.
                        cells[staff][day] = self.resolve(year, month, staff, day, text)
                        changed = True
            if changed:
                self.data.data.setdefault('store_manual_shift_board', {})[key] = deepcopy(board)
                self.data.save()
        return board

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

    @staticmethod
    def days(year, month, half):
        last = monthrange(int(year), int(month))[1]
        return range(1, 16) if half == 'first' else range(16, last + 1)

    def resolve(self, year, month, staff, day, text):
        from core.shift_submissions import ShiftSubmissionManager
        import re
        text = str(text or '').strip()
        result = {'text': text or '—', 'kind': 'off', 'warning': ''}
        if text in ('', '休み', '絶対休み', '—'):
            return result
        kind = next((k for k in ('通し', 'ランチ', 'ディナー') if k in text), '時間指定')
        result['kind'] = kind
        submission = ShiftSubmissionManager(self.data).submission(staff, year, month, 'first' if int(day) <= 15 else 'second')
        wish = submission['days'].get(str(day), {})
        warnings = []
        wanted = wish.get('type', '')
        if not submission['submitted_at'] or not wanted:
            warnings.append('この日の希望がありません')
        elif wanted == '絶対休み':
            warnings.append('休み希望の日です')
        elif kind != '時間指定' and wanted not in (kind, '通し'):
            warnings.append('希望は' + wanted + 'です')
        start, end = wish.get('start', ''), wish.get('end', '')
        times = re.findall(r'\d{1,2}:\d{2}', text)
        wish_time = start + '〜' + end
        if times:
            if (start and times[0] != start) or (end and times[-1] != end):
                warnings.append('入力時間と希望時間が異なります（希望 ' + wish_time + '）')
            if kind == '時間指定':
                warnings.append('勤務区分を確認してください')
        elif (start or end) and wanted not in ('', '絶対休み'):
            result['text'] = text + '\n希望 ' + wish_time
            if wanted != kind:
                warnings.append('希望時間は' + wanted + '全体の時間です。勤務時間を確認してください')
        if submission['pending_change']:
            warnings.append('希望の変更申請が確認待ちです')
        result['warning'] = '／'.join(warnings)
        return result

    def resolved(self, year, month, entries):
        return {staff: {day: self.resolve(year, month, staff, day, text)
                        for day, text in values.items()}
                for staff, values in entries.items() if staff in self.STAFF}

    def apply_approved_change(self, staff, year, month, half):
        """Refresh only this person's already published half; never publish drafts."""
        board = self.month(year, month)
        published = board.get('published')
        if not published or staff not in self.STAFF:
            return
        days = {str(d) for d in self.days(year, month, half)}
        entries = published.get('entries', {}).get(staff, {})
        affected = {day: text for day, text in entries.items() if day in days}
        if not affected:
            return
        cells = published.setdefault('cells', {}).setdefault(staff, {})
        for day, text in affected.items():
            cells[day] = self.resolve(year, month, staff, day, text)
        stamp = now_jst().strftime('%Y/%m/%d %H:%M')
        if not published.get('periods'):
            published['periods'] = dict(first=published['updated_at'], second=published['updated_at'])
        published['periods'][half] = stamp
        published['updated_at'] = stamp
        self.data.data['store_manual_shift_board'][self.key(year, month)] = board
        # The approval caller persists submission and board together in one save.

    def publish(self, year, month, half=None, expected=None):
        board = self.month(year, month)
        entries = {s: dict(v) for s, v in board['draft'].items() if s in self.STAFF}
        if half:
            days = {str(d) for d in self.days(year, month, half)}
            entries = {s: {d: t for d, t in v.items() if d in days} for s, v in entries.items()}
        if not any(entries.values()):
            raise ValueError('先に勤務予定か「休み」を入力・保存してください')
        resolved = self.resolved(year, month, entries)
        if expected is not None and resolved != expected:
            raise ValueError('希望または下書きが更新されました。確認画面を開き直してください')
        previous = board.get('published') or {}
        combined = deepcopy(previous.get('entries', {})) if half else {}
        cells = deepcopy(previous.get('cells', {})) if half else {}
        if half:
            for staff in set(combined) | set(entries):
                combined[staff] = {d: t for d, t in combined.get(staff, {}).items() if d not in days}
                cells[staff] = {d: t for d, t in cells.get(staff, {}).items() if d not in days}
        for staff, values in entries.items():
            combined.setdefault(staff, {}).update(values)
            cells.setdefault(staff, {}).update(resolved[staff])
        periods = dict(previous.get('periods', {}))
        stamp = now_jst().strftime('%Y/%m/%d %H:%M')
        if not previous.get('periods') and previous:
            periods = dict(first=previous['updated_at'], second=previous['updated_at'])
        for period in ([half] if half else ['first','second']):
            periods[period] = stamp
        board['published'] = {'entries': combined, 'cells': cells, 'periods': periods, 'updated_at': stamp}
        self.data.data.setdefault('store_manual_shift_board', {})[self.key(year, month)] = board
        self.data.save()


shift_board = ShiftBoardManager()
