"""Shared, persistent mobile navigation; pages retain their own access checks."""
from nicegui import ui
from store_preview.core.auth import has_permission


def bottom_navigation(app_name):
    try:
        path = ui.context.client.request.url.path
    except (RuntimeError, AttributeError):
        return
    if '/login' in path:
        return
    if app_name == 'mirai-kessan':
        entries = [('ホーム','home','/mirai-kessan/dashboard'),('入力','edit_note','/mirai-kessan/input'),
                   ('予測','query_stats','/mirai-kessan/forecast'),('記録','folder_open','/mirai-kessan/reports')]
        if not has_permission('future_dashboard'):
            entries = [entries[1]]
        section = 2 if any(x in path for x in ('forecast','block-map','targets')) else 3 if any(x in path for x in ('/reports','/evaluation','/audit')) else 1 if any(x in path for x in ('input','sales','shiire','staffing','advances','details','attendance')) else 0
        ui.add_head_html('<link rel="stylesheet" href="/static/mirai-navy.css?v=finance-organize-20261024">')
    else:
        entries = [('ホーム','home','/store-preview'),('在庫','inventory_2','/store-preview/inventory'),
                   ('仕入れ','shopping_basket','/store-preview/orders'),('シフト','calendar_month','/store-preview/shift-board'),
                   ('その他','apps','/store-preview/more')]
        section = 1 if 'inventory' in path else 2 if any(x in path for x in ('purchase-list','order-requests','orders')) else 3 if 'shift' in path else 0 if path in ('/store-preview','/store-preview/me') else 4
    ui.add_css('''.app-bottom-nav{position:fixed;bottom:0;left:0;right:0;z-index:1500;display:flex;justify-content:center;background:#fffefaf5;border-top:1px solid #d5ddd7;padding:7px 8px calc(7px + env(safe-area-inset-bottom));backdrop-filter:blur(14px)}.app-bottom-link{flex:1;max-width:150px;display:flex;align-items:center;flex-direction:column;gap:3px;color:#76837a;text-decoration:none;font-size:11px;padding:6px 0;border-radius:12px}.app-bottom-link.active{background:#e7eee8;color:#28513c;font-weight:bold}.app-bottom-link .q-icon{font-size:23px}.app-shell{padding-bottom:110px!important}@media print{.app-bottom-nav{display:none!important}.app-shell{padding-bottom:0!important}}''')
    with ui.element('nav').classes('app-bottom-nav').props('aria-label="アプリメニュー"'):
        for i,(label,icon,url) in enumerate(entries):
            with ui.link(target=url).classes('app-bottom-link'+(' active' if path==url or (len(entries)>1 and i==section) else '')).props('aria-label="'+label+'"'):
                ui.icon(icon);ui.label(label)
