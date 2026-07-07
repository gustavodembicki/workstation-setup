from __future__ import annotations

import questionary


def confirm_step(message: str, *, default: bool = True) -> bool:
    return bool(questionary.confirm(message, default=default).ask())


def checkbox_select(message: str, choices: list[questionary.Choice]) -> list[str]:
    return questionary.checkbox(message, choices=choices).ask() or []


def text_input(message: str, *, default: str = "") -> str:
    return questionary.text(message, default=default).ask() or ""
