import ast
from pathlib import Path
import unittest
from unittest.mock import patch

class PreviewTests(unittest.TestCase):
    def test_data_and_managers_are_separate(self):
        from core.data import data as live
        from store_preview.core.data import data as preview
        from core.store_ops import store_ops as live_store
        from store_preview.core.store_ops import store_ops as preview_store
        self.assertNotEqual(live.file_path.resolve(), preview.file_path.resolve())
        self.assertEqual(preview.file_path.name, 'store-preview.json')
        self.assertIsNot(live.data, preview.data)
        self.assertIs(live_store._data_manager, live)
        self.assertIs(preview_store._data_manager, preview)
        original=live.file_path.read_bytes()
        preview.data['preview_test']='isolated'
        preview.save()
        self.assertNotIn('preview_test',live.data)
        self.assertEqual(live.file_path.read_bytes(),original)
        preview.data.pop('preview_test');preview.save()

    def test_no_production_manager_imports(self):
        for p in Path('store_preview').rglob('*.py'):
            for n in ast.walk(ast.parse(p.read_text())):
                if isinstance(n,ast.ImportFrom) and n.module:
                    self.assertFalse(n.module.startswith('core.') and n.module!='core.auth', str(p))
                    self.assertFalse(n.module.startswith('pages.'), str(p))

    def test_page_routes_are_namespaced(self):
        import store_preview.register
        from nicegui import app
        routes=[r for r in app.routes if getattr(getattr(r,'endpoint',None),'__module__','').startswith('store_preview')]
        self.assertGreater(len(routes),10)
        for r in routes:self.assertTrue(r.path.startswith('/store-preview'),r.path)

    def test_owner_only(self):
        from store_preview.core import auth
        with patch.object(auth,'_require_app_access',return_value=True),patch.object(auth,'current_role',return_value='staff'),patch.object(auth.ui.navigate,'to') as navigate:
            self.assertFalse(auth.require_app_access('store_ops'))
            navigate.assert_called_once_with('/store-ops')
        with patch.object(auth,'_require_app_access',return_value=True),patch.object(auth,'current_role',return_value='owner'):
            self.assertTrue(auth.require_app_access('store_ops'))

    def test_preview_pages_render_without_changing_live_data(self):
        from contextlib import ExitStack
        from types import SimpleNamespace
        from nicegui import ui
        from core.data import data as live
        from store_preview.pages import store_dashboard, store_sections, store_shift_board
        pages=[store_dashboard.store_dashboard_page,store_dashboard.store_more_page,store_dashboard.store_orders_hub,store_sections.inventory_page,store_shift_board.shift_board_page]
        before=live.file_path.read_bytes()
        with ExitStack() as stack:
            stack.enter_context(patch.object(ui,"run_javascript"))
            for module in (store_dashboard,store_sections,store_shift_board):
                stack.enter_context(patch.object(module,'require_app_access',return_value=True))
                if hasattr(module,'current_role'):stack.enter_context(patch.object(module,'current_role',return_value='owner'))
                if hasattr(module,'has_permission'):stack.enter_context(patch.object(module,'has_permission',return_value=True))
            stack.enter_context(patch('store_preview.pages.app_navigation.has_permission',return_value=True))
            client=ui.context.client
            stack.enter_context(patch.object(type(client),'request',new_callable=lambda:property(lambda _:SimpleNamespace(url=SimpleNamespace(path='/store-preview')))))
            for page in pages:
                with ui.column():page()
        self.assertEqual(live.file_path.read_bytes(),before)
