"""Private, two-person garden. Account identity is supplied by the server."""
from copy import deepcopy
from datetime import date
from uuid import uuid4
from core.data import data
from core.clock import today_jst, now_jst


class CoupleGarden:
    def __init__(self, manager=None):
        self.manager = manager or data

    def state(self, person):
        self.validate(person)
        value = deepcopy(self.manager.data.get('couple_garden', {'days': {}, 'notes': [], 'meetings': {}}))
        value['notes'] = [n for n in value['notes'] if n['owner'] == person or n['shared']]
        return value

    @staticmethod
    def validate(person):
        if person not in ('user1', 'user2'):
            raise ValueError('ふたりのアカウントでログインしてください')

    def root(self, person):
        self.validate(person)
        return self.manager.data.setdefault('couple_garden', {'days': {}, 'notes': [], 'meetings': {}})

    def check(self, person, rainbow=False):
        day = self.root(person)['days'].setdefault(today_jst().isoformat(), {'thanks': [], 'rainbow': []})
        key = 'rainbow' if rainbow else 'thanks'
        if person not in day[key]:
            day[key].append(person)
        self.manager.save()

    def note(self, person, category, text, shared=False):
        self.validate(person)
        text = str(text or '').strip()
        if not text or len(text) > 2000:
            raise ValueError('メモは1〜2000文字で入力してください')
        if category not in ('ありがとう', '気になったこと', '次に話したいこと'):
            raise ValueError('メモの種類を選んでください')
        self.root(person)['notes'].append(dict(id=uuid4().hex, owner=person, category=category,
            text=text, shared=bool(shared), created_at=now_jst().isoformat()))
        self.manager.save()

    def delete_note(self, person, note_id):
        root = self.root(person)
        note = next((n for n in root['notes'] if n['id'] == note_id), None)
        if not note or note['owner'] != person:
            raise ValueError('自分のメモだけ削除できます')
        root['notes'].remove(note)
        self.manager.save()

    def meeting(self, person, day, promise):
        self.validate(person)
        parsed = date.fromisoformat(day)
        if parsed > today_jst():
            raise ValueError('話し合った日は今日以前を選んでください')
        promise = str(promise or '').strip()
        if not promise or len(promise) > 1000:
            raise ValueError('ふたりで決めたことを1〜1000文字で入力してください')
        self.root(person)['meetings'][day] = {'promise': promise, 'by': person}
        self.manager.save()


garden = CoupleGarden()
