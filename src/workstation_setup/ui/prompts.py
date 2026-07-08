from __future__ import annotations

import questionary

from workstation_setup.steps.base import ExistingAction


def confirm_step(message: str, *, default: bool = True) -> bool:
    return bool(questionary.confirm(message, default=default).ask())


def checkbox_select(message: str, choices: list[questionary.Choice]) -> list[str]:
    return questionary.checkbox(message, choices=choices).ask() or []


def text_input(message: str, *, default: str = "") -> str:
    return questionary.text(message, default=default).ask() or ""


def select_existing_action(title: str) -> ExistingAction:
    """Asked whenever a Step is already installed — never assume "skip".
    Gives the user a real choice instead of silently doing nothing.
    """
    choice = questionary.select(
        f"{title} is already installed. What would you like to do?",
        choices=[
            questionary.Choice(title="Reinstall / Modify", value=ExistingAction.REINSTALL),
            questionary.Choice(title="Leave as is", value=ExistingAction.LEAVE),
            questionary.Choice(title="Cancel", value=ExistingAction.CANCEL),
        ],
    ).ask()
    return choice or ExistingAction.CANCEL
