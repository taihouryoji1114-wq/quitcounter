"""Read published shift-board snapshots without changing timecards or drafts."""
from calendar import monthrange
from copy import deepcopy
from datetime import date
import re


def board_shift(cell, template):
    text = str(cell.get('text', '')).strip()
    kind = cell.get('kind', '')
    empty = dict(lunch_start='', lunch_end='', dinner_start='', dinner_end='', break_minutes=0)
    if kind == 'off' or text in ('休み', '絶対休み', '—'):
        return empty, False
    # A request for a whole day must not become a dinner-only working interval.
    if '希望時間は' in cell.get('warning', '') and '\n希望' in text:
        return None, False
    times = re.findall(r'(?<!\d)(\d{1,2}:\d{2})(?!\d)', text)
    if times:
        if len(times) not in (2, 4):
            return None, False
        if any(not (0 <= int(t.split(':')[0]) < 24 and 0 <= int(t.split(':')[1]) < 60) for t in times):
            return None, False
        if any(times[i] == times[i+1] for i in range(0, len(times), 2)):
            return None, False
        keys = ('lunch', 'dinner') if len(times) == 4 else ('dinner' if kind == 'ディナー' else 'lunch',)
        for i, prefix in enumerate(keys):
            empty[prefix+'_start'], empty[prefix+'_end'] = times[i*2:i*2+2]
        empty['break_minutes'] = template.get('break_minutes', 0)
        return empty, False
    keys = {'ランチ': ('lunch',), 'ディナー': ('dinner',), '通し': ('lunch', 'dinner')}.get(kind)
    if not keys or any(not template.get(k, {}).get('sample_count') for k in keys):
        return None, False
    for prefix in keys:
        empty[prefix+'_start'] = template[prefix]['start']
        empty[prefix+'_end'] = template[prefix]['end']
    empty['break_minutes'] = template.get('break_minutes', 0)
    return empty, True


def effective_plans(manager, month, as_of):
    """Published board cells override legacy plans per person, including explicit off.

    Missing board entries retain legacy plans; unresolved published work NEVER
    silently falls back to a stale legacy shift. No writes/backfill on this path.
    """
    raw = manager._data_manager.data
    plans = {d: deepcopy(v) for d,v in raw.get('business_staff_shift_plans', {}).items()
             if d.startswith(month) and d > as_of.isoformat()}
    published = raw.get('store_manual_shift_board', {}).get(month, {}).get('published') or {}
    templates = manager.shift_templates(as_of)
    cells = published.get('cells', {})
    board_count = learned = unknown_wages = 0
    y,m = map(int, month.split('-'))
    for name, entries in published.get('entries', {}).items():
        if name not in manager.HOURLY_STAFF:
            continue
        for day, text in entries.items():
            if not str(day).isdigit() or not 1 <= int(day) <= monthrange(y,m)[1]:
                continue
            target = f'{month}-{int(day):02d}'
            if target <= as_of.isoformat():
                continue
            cell = cells.get(name, {}).get(str(day))
            if cell is None:
                # Legacy entries have no approved-time snapshot: explicit times
                # or labels only, never fresh/unapproved submission requests.
                kind = next((k for k in ('通し','ランチ','ディナー') if k in text), '時間指定')
                cell = {'text': text, 'kind': kind}
            shift, inferred = board_shift(cell, templates[name])
            plans.setdefault(target, {}).pop(name, None)
            if shift is not None:
                plans[target][name] = shift
                board_count += 1
                learned += int(inferred)
            if (shift is None or manager._worked(shift)) and manager.wages()[name] <= 0:
                unknown_wages += 1
    active = [name for name in manager.HOURLY_STAFF if manager.wages()[name] > 0]
    missing = {name: [] for name in active}
    closures = raw.get('landing_forecast_settings', {}).get('closed_dates', [])
    for d in range(1,monthrange(y,m)[1]+1):
        target = f'{month}-{d:02d}'
        if target <= as_of.isoformat() or target in closures:
            continue
        for name in active:
            if name not in plans.get(target, {}):
                missing[name].append(target)
    # Normalise sparse plans for all existing payroll loops.
    for shifts in plans.values():
        for name in manager.HOURLY_STAFF:
            shifts.setdefault(name, {})
    return plans, dict(board_cells=board_count, learned_cells=learned,
                       unknown_wages=unknown_wages, missing_by_staff=missing)
