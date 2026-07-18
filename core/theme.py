from nicegui import ui


class Theme:

    @staticmethod
    def page(title: str = "Habitory"):

        ui.colors(
            primary="#4CAF50",
            secondary="#81C784",
            positive="#43A047",
        )

        ui.page_title(title)


def habit_card(
    icon: str,
    title: str,
    subtitle: str,
    color: str,
    callback,
):

    with ui.card().classes(
        "w-80 q-pa-md cursor-pointer transition-all duration-300 hover:shadow-xl"
    ).on(
        "click",
        lambda _: callback(),
    ):

        with ui.row().classes(
            "w-full items-center justify-between"
        ):

            with ui.row().classes("items-center"):

                ui.label(icon).classes("text-4xl")

                with ui.column().classes("ml-3"):

                    ui.label(title).classes(
                        f"text-xl font-bold text-{color}"
                    )

                    ui.label(subtitle).classes(
                        "text-grey-6"
                    )

            ui.icon(
                "chevron_right"
            ).classes("text-grey-5")