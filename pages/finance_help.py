from nicegui import ui


def finance_help(title, paragraphs):
    """Details on demand; material missing-data notices stay on the page."""
    with ui.dialog() as dialog, ui.card().classes('surface-card w-full').style('max-width:480px'):
        ui.label(title).classes('text-lg font-bold')
        for paragraph in paragraphs:
            ui.label(paragraph).classes('text-sm')
        ui.button('閉じる',on_click=dialog.close).classes('self-end')
    return ui.button(icon='help_outline',on_click=dialog.open).props('flat round dense aria-label="'+title+'の説明"').tooltip(title+'の説明')
