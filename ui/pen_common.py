"""Gemeinsame Füller-Helfer (v0.3.02, aus ui/pen_widget.py ausgelagert).

Label- und Optionslisten, die sowohl das Verwaltungs-Widget als auch die
Füller-Dialoge (ui/pen_dialogs.py) benötigen – ohne Zirkularimport.
"""
from __future__ import annotations

from i18n.translator import t

FILL_SYSTEM_KEYS = ['piston', 'vac', 'converter', 'cartridge', 'eyedropper']

def _fill_systems():
    return [(key, t(f'pen.fill_systems.{key}')) for key in FILL_SYSTEM_KEYS]

def _fill_system_label(key: str | None) -> str:
    return dict(_fill_systems()).get(key, key or '')
TAG_KEYS = ['grail', 'problem', 'collector', 'vintage']

def _tag_label(key: str) -> str:
    return t(f'pen.tags_list.{key}') if key else ''

def _rotation_roles():
    return [('writer', t('rotation.role_writer')), ('edc', t('rotation.role_edc')), ('agenda', t('rotation.role_agenda')), ('journal', t('rotation.role_journal')), ('work', t('rotation.role_work')), ('creative', t('rotation.role_creative')), ('letter', t('rotation.role_letter')), ('collector', t('rotation.role_collector')), ('vintage', t('rotation.role_vintage')), ('problem', t('rotation.role_problem')), ('fine', t('rotation.role_fine')), ('broad', t('rotation.role_broad'))]
ROTATION_ROLES = _rotation_roles()

def _rotation_themes():
    return [(None, t('rotation.theme_auto')), ('edc', t('rotation.theme_edc')), ('agenda', t('rotation.theme_agenda')), ('journal', t('rotation.theme_journal')), ('work', t('rotation.theme_work')), ('creative', t('rotation.theme_creative')), ('letter', t('rotation.theme_letter')), ('archive', t('rotation.theme_archive')), ('cheap_paper', t('rotation.theme_cheap')), ('fine_nib', t('rotation.theme_fine_nib')), ('broad_nib', t('rotation.theme_broad_nib')), ('sheen_showcase', t('rotation.theme_sheen')), ('testing', t('rotation.theme_testing'))]
ROTATION_THEMES = _rotation_themes()
BLOCKING_STATUSES = {'problem', 'service', 'blocked', 'dry_risk'}


def _status_label(key: str | None) -> str:
    return t(f'dashboard.status_labels.{key}') if key else ''
