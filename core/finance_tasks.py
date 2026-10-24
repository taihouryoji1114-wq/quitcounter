"""Read-only, actionable checks; no invented missing purchase days."""
from datetime import date, timedelta
from core.business_audit import BusinessAuditManager
from core.staff_identity import staff_display_name


def build_finance_tasks(manager, month, today, outlook):
    first=date.fromisoformat(month+'-01')
    if first>today:return []
    closures=set(manager.data.get('landing_forecast_settings',{}).get('closed_dates',[]))
    groups={}
    def add(area,title,detail,path,day='',level='確認'):
        key=(area,title)
        group=groups.setdefault(key,dict(area=area,title=title,level=level,items=[]))
        group['items'].append(dict(date=day,detail=detail,path=path))
    for issue in BusinessAuditManager(manager).inspect(month,today-timedelta(days=1))['issues']:
        if issue['title']=='売上が未入力です' and issue['date'] in closures:continue
        if issue['title']=='売上が0円です':continue  # An explicit zero is a recorded amount.
        path=issue['path']
        if issue['area']=='月次費用':path='/mirai-kessan/details?month='+month
        if issue['area']=='人件費':path='/mirai-kessan/staffing/day?date='+issue['date']
        title=issue['title']
        names=set(manager.data.get('business_staff_wages',{}))
        for staff_rows in manager.data.get('business_staff_hours',{}).values():
            if isinstance(staff_rows,dict):names.update(staff_rows)
        for name in names:title=title.replace(name,staff_display_name(name))
        add(issue['area'],title,issue['detail'],path,issue['date'],'入力' if issue['level']=='missing' else '修正' if issue['level']=='danger' else '確認')
    raw=manager.data
    published=raw.get('store_manual_shift_board',{}).get(month,{}).get('published') or {}
    hours=raw.get('business_staff_hours',{})
    for name,entries in published.get('entries',{}).items():
        for day,text in entries.items():
            if not str(day).isdigit():continue
            try:target=date.fromisoformat(f'{month}-{int(day):02d}')
            except ValueError:continue
            cell=published.get('cells',{}).get(name,{}).get(str(day),{})
            if target>=today or cell.get('kind')=='off' or str(text).strip() in ('','—','休み','絶対休み'):continue
            actual=hours.get(target.isoformat(),{}).get(name,{})
            if actual.get('entry_confirmed') or actual.get('attended') or any(actual.get(k) for k in ('lunch_start','lunch_end','dinner_start','dinner_end')):continue
            add('人件費','出勤予定日の勤務実績が未入力',staff_display_name(name)+'：実際の勤務時間、または休みを入力してください。','/mirai-kessan/staffing/day?date='+target.isoformat(),target.isoformat(),'入力')
    for issue in outlook.get('payroll_issues',[]):
        reason=issue['reason'];day=issue['date']
        path='/store-ops/shift-board' if '未公開' in reason or '勤務時間' in reason else '/mirai-kessan/staffing'
        if day<today.isoformat():path='/mirai-kessan/staffing/day?date='+day
        add('人件費予測',reason,staff_display_name(issue['staff'])+'：'+('店舗管理で勤務時間を確認してシフトを公開してください。' if path.startswith('/store-ops') else '給与・勤務の登録を確認してください。'),path,day,'未反映')
    tax=outlook.get('report',{}).get('settlement',{}).get('tax',{})
    if tax.get('issues'):
        add('税金','月次経費の税区分が未設定','仕入の消費税は自動控除済みです。家賃などの税区分を設定すると、残額の概算が更新されます。','/mirai-kessan/taxes?month='+month,level='設定')
    return list(groups.values())
