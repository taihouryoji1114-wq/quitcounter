"""Saved sales targets are plans, never actual sales or revised forecasts."""
from calendar import monthrange
from copy import deepcopy
from datetime import date
from math import ceil, isfinite
from uuid import uuid4
from core.clock import now_jst
from core.landing_forecast import monthly_forecast


def allocate(total, weights):
    """Largest remainder allocation keeps the yen total exact."""
    if not weights:
        return []
    weights = [max(0, w) for w in weights]
    if not sum(weights):
        weights = [1] * len(weights)
    raw = [total * w / sum(weights) for w in weights]
    amounts = [int(v) for v in raw]
    for i in sorted(range(len(raw)), key=lambda i: raw[i] - amounts[i], reverse=True)[:total-sum(amounts)]:
        amounts[i] += 1
    return amounts


def build_target_plan(records, month, target, as_of, closed_dates=()):
    target = float(target)
    if not isfinite(target) or target <= 0 or target != int(target):
        raise ValueError('月間売上目標は1円以上の整数で入力してください')
    year, number = map(int, month.split('-'))
    monthrange(year, number)  # Validate the month before any allocations.
    if month < as_of.strftime('%Y-%m'):
        raise ValueError('目標を作成できるのは今月以降です')
    forecast = monthly_forecast(records, month, as_of, closed_dates=closed_dates)
    if forecast['missing'] and forecast['imputed'] is None:
        raise ValueError('過去の未入力日を補完する実績がありません。売上を入力してから作成してください')
    baseline = forecast['actual'] + (forecast['imputed'] or 0)
    remaining = max(0, int(target) - baseline)
    estimates = forecast['estimates']
    if remaining and not estimates:
        raise ValueError('残りの営業日がありません。休業日または対象月を確認してください')
    weights = [e['sales'] or 0 for e in estimates]
    amounts = allocate(remaining, weights)
    history = [r for r in records if r.get('amount') is not None and
               0 < (as_of-date.fromisoformat(r['date'])).days <= 84 and
               r.get('lunch_sales') is not None and r.get('dinner_sales') is not None]
    rows = []
    for e, amount in zip(estimates, amounts):
        day = date.fromisoformat(e['date'])
        weekday = [r for r in history if date.fromisoformat(r['date']).weekday() == day.weekday()]
        pool = weekday if len(weekday) >= 2 else history
        lunch = sum(float(r['lunch_sales']) for r in pool)
        dinner = sum(float(r['dinner_sales']) for r in pool)
        split = allocate(amount, [lunch, dinner])
        customers = []
        for session, value in zip(('lunch', 'dinner'), split):
            valid = [r for r in pool if (r.get(session+'_customers') or 0) > 0]
            revenue = sum(float(r[session+'_sales']) for r in valid)
            count = sum(float(r[session+'_customers']) for r in valid)
            customers.append(ceil(value / (revenue/count)) if revenue > 0 and count > 0 else None)
        rows.append({'date':e['date'], 'target':amount, 'lunch':split[0], 'dinner':split[1],
                     'lunch_customers':customers[0], 'dinner_customers':customers[1],
                     'forecast':e['sales'], 'basis':e['basis'],
                     'split_basis':'同曜日の売上比' if pool is weekday and lunch+dinner else '直近12週の売上比' if lunch+dinner else '実績不足のため半分ずつ'})
    return {'month':month,'as_of':as_of.isoformat(),'monthly_target':int(target),
            'actual':forecast['actual'],'imputed':forecast['imputed'] or 0,
            'missing':forecast['missing'],'remaining':remaining,'rows':rows,
            'closed_dates':list(closed_dates),'equal_allocation':not any(weights)}


def save_target_plan(manager, plan):
    saved = deepcopy(plan)
    saved['id'] = uuid4().hex
    saved['created_at'] = now_jst().isoformat()
    manager.data.setdefault('sales_target_plans', {})[saved['id']] = saved
    manager.save()
    return saved


def plan_results(plan, records, as_of):
    actual = {r['date']:r['amount'] for r in records if r.get('amount') is not None and r['date'] < as_of.isoformat()}
    rows = []
    for row in plan['rows']:
        value = actual.get(row['date'])
        rows.append(dict(row, actual=value, difference=None if value is None else value-row['target']))
    return rows


def weekly_adjustment(plan, records, start, as_of):
    """Redistribute only known differences within the selected seven days."""
    from datetime import timedelta
    end = start + timedelta(days=7)
    rows = [r for r in plan_results(plan, records, as_of)
            if start.isoformat() <= r['date'] < end.isoformat()]
    difference = sum(r['difference'] for r in rows if r['difference'] is not None)
    remaining = [r for r in rows if r['date'] >= as_of.isoformat()]
    adjustment = sum(r['difference'] for r in rows if r['difference'] is not None and not r.get('historical_target'))
    required = max(0, sum(r['target'] for r in remaining) - adjustment)
    revised = dict(zip((r['date'] for r in remaining), allocate(required, [r['target'] for r in remaining])))
    return {'rows': [dict(r, revised_target=revised.get(r['date'])) for r in rows],
            'difference': difference,
            'missing': sum(r['actual'] is None and r['date'] < as_of.isoformat() for r in rows),
            'unallocated': required if not remaining else 0}


def with_historical_targets(plan, saved_plans):
    """Fill past gaps from earlier saved versions, without rewriting the plan."""
    result = deepcopy(plan)
    rows = {r['date']:r for r in result['rows']}
    cutoff = plan.get('created_at', plan['as_of']+'T23:59:59')
    earlier = sorted((p for p in saved_plans if p.get('month') == plan['month']
                      and p.get('created_at', '') < cutoff),
                     key=lambda p:p.get('created_at',''), reverse=True)
    for previous in earlier:
        for row in previous['rows']:
            if row['date'] < plan['as_of'] and row['date'] not in rows:
                rows[row['date']] = dict(row, historical_target=True)
    result['rows'] = sorted(rows.values(), key=lambda r:r['date'])
    return result


def recommend_target(records, month, as_of, closed_dates=()):
    """Explainable suggestion, not a learned probability or automatic saved goal."""
    forecast = monthly_forecast(records, month, as_of, closed_dates=closed_dates)
    recent_days = {r['date'] for r in records if r.get('amount') is not None
                   and 0 < (as_of-date.fromisoformat(r['date'])).days <= 84}
    enough = len(recent_days) >= 14 and not forecast['missing']
    uplift = .05 if enough else 0
    available = (month >= as_of.strftime('%Y-%m') and forecast['remaining_days'] > 0
                 and forecast['landing'] is not None and forecast['landing'] > 0)
    suggestion = round(forecast['landing'] + forecast['remaining'] * uplift) if available else None
    reason = ('残りの日の予測売上を5％伸ばす目標です。5％は最初の目安で、達成を保証する数字ではありません。'
              if enough else '未入力の日があるか、直近12週の記録が14日未満のため、上乗せせず予測額を提案します。')
    return dict(forecast=forecast, target=suggestion, uplift=uplift, reason=reason,
                sample_days=len(recent_days), version='remaining-5pct-v1')


def automatic_target_plan(records, month, as_of, closed_dates=()):
    """A read-only current plan, usable without a saved manual target."""
    suggestion = recommend_target(records, month, as_of, closed_dates)
    if suggestion['target'] is None:
        return None
    plan = build_target_plan(records, month, suggestion['target'], as_of, closed_dates)
    plan.update(id='automatic', source='automatic', created_at=as_of.isoformat()+'T00:00:00')
    return plan
