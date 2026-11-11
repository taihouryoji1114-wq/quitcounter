"""Preview-only daily checks; 04:00 never deletes stored handover results."""
from copy import deepcopy
from datetime import timedelta
from store_preview.core.clock import JAPAN, now_jst
from store_preview.core.data import data


class LiveBoardReviewManager:
    CHECKS = 'store_live_board_daily_checks'
    HANDOVER = 'store_live_board_handover_results'

    def __init__(self, data_manager):
        self._data_manager = data_manager

    @staticmethod
    def day_key(at=None):
        current = at or now_jst()
        current = current.replace(tzinfo=JAPAN) if current.tzinfo is None else current.astimezone(JAPAN)
        return (current - timedelta(hours=4)).date().isoformat()

    def checked(self, item_id, at=None):
        return bool(self._data_manager.data.get(self.CHECKS, {}).get(self.day_key(at), {}).get(item_id))

    def initialize_handover(self, items, acknowledged=None):
        """Preserve pre-upgrade confirmed results without pre-checking today."""
        if self.HANDOVER in self._data_manager.data:
            return
        self._data_manager.data[self.HANDOVER] = {
            item['id']: self._snapshot(item) for item in items
            if item.get('reviewed') and item.get('source') != 'daily_order'
        }
        for item_id, snapshot in self._data_manager.data[self.HANDOVER].items():
            snapshot['handover_acknowledged'] = bool((acknowledged or {}).get(item_id))
        self._data_manager.save()

    @staticmethod
    def _snapshot(item):
        result = deepcopy(item)
        result['handover_acknowledged'] = False
        return result

    def record(self, item, at=None):
        current = at or now_jst()
        self._data_manager.data.setdefault(self.CHECKS, {}).setdefault(self.day_key(current), {})[item['id']] = True
        snapshot = self._snapshot(item)
        snapshot['confirmed_at'] = current.isoformat(timespec='seconds')
        self._data_manager.data.setdefault(self.HANDOVER, {})[item['id']] = snapshot
        self._data_manager.save()

    def update_note(self, item):
        snapshot = self._data_manager.data.get(self.HANDOVER, {}).get(item['id'])
        if snapshot is not None:
            snapshot['note'] = item.get('note', '')
            self._data_manager.save()

    def uncheck(self, item_ids, at=None):
        checks = self._data_manager.data.setdefault(self.CHECKS, {}).setdefault(self.day_key(at), {})
        for item_id in item_ids:
            checks[item_id] = False
        self._data_manager.save()

    def handovers(self, visible_ids=None):
        values = self._data_manager.data.get(self.HANDOVER, {}).values()
        return [deepcopy(item) for item in values if visible_ids is None or item['id'] in visible_ids]

    def acknowledge(self, item_id, checked):
        value = self._data_manager.data.get(self.HANDOVER, {}).get(item_id)
        if value is None:
            raise ValueError('引き継ぎ項目が見つかりません')
        value['handover_acknowledged'] = bool(checked)
        self._data_manager.save()


live_board_review = LiveBoardReviewManager(data)
