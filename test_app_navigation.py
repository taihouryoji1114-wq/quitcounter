from types import SimpleNamespace
from unittest.mock import patch
import unittest
from nicegui import ui
from pages.app_navigation import bottom_navigation

class NavigationTest(unittest.TestCase):
    def test_navigation_renders_for_both_apps_and_restricted_input(self):
        for app_name,path,allowed in [('mirai-kessan','/mirai-kessan/forecast',True),('mirai-kessan','/mirai-kessan/input',False),('store-ops','/store-ops/inventory',True)]:
            with ui.column():
                client=ui.context.client
                with patch.object(type(client),'request',new_callable=lambda:property(lambda _:SimpleNamespace(url=SimpleNamespace(path=path)))),patch('pages.app_navigation.has_permission',return_value=allowed):
                    bottom_navigation(app_name)
    def test_compact_finance_home_renders_without_data(self):
        from pages.finance_home import compact_finance_home
        with patch('pages.finance_home.data',SimpleNamespace(data={})),patch('pages.finance_home.financials',SimpleNamespace(sales_records=lambda:[])):
            with ui.column():compact_finance_home('2026-10')
