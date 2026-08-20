#!/usr/bin/env python3
"""KILLCRITIC 1000-Loop-Invarianten-Audit für den aktuellen Release-Stand.

Release-/Logik-/UI-Invarianten × 1000 Wiederholungen (Anzahl dynamisch, Ausgabe nennt die Summe).
Übernommen aus dem parallelen KILLCRITIC-RC und auf diesen Merge-Stand
portiert. Bewusst schnell und deterministisch (die Wiederholungen sind ein
Stabilitäts-Smoke, keine Zufallsläufe); die tiefe Prüfung bleibt pytest.

Enthält als dauerhafte Guards genau die Schwächen, die der Vergleich der
beiden 0.2.88-Merges aufgedeckt hat (Doppelpfad, Reject-Lücke, Tinten- statt
Paar-Sperre, Legacy-Setting-Seeding).
"""
from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app_info import APP_BUILD, APP_VERSION  # noqa: E402


@lru_cache(maxsize=None)
def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def j(rel: str):
    return json.loads(read(rel))


@lru_cache(maxsize=None)
def _order_ok(func_name: str, *, ai_before_site: bool) -> bool:
    """Prüft die Stufenreihenfolge im Quelltext eines URL-Builders.

    Maße: KI-Prompt vor der site:-Schleife. Bilder: umgekehrt.
    """
    src = read('logic/pen_dimensions_service.py')
    body = src.split(f'def {func_name}')[1].split('\ndef ')[0]
    ai_pos = body.find('ai_mode=True')
    site_pos = body.find('manufacturer_domains_for_brand')
    if ai_pos < 0 or site_pos < 0:
        return False
    return (ai_pos < site_pos) if ai_before_site else (site_pos < ai_pos)


CHECKS = [
    # ── Version & Release-Dateien ────────────────────────────────────
    ("version_app", lambda: f'APP_VERSION = "{APP_VERSION}"' in read('app_info.py')),
    ("version_build", lambda: f'APP_BUILD = "{APP_BUILD}"' in read('app_info.py')),
    ("version_json", lambda: j('version.json')['version'] == APP_VERSION),
    ("version_info", lambda: f'Build: {APP_BUILD}' in read('VERSION_INFO.txt')),
    ("latest_root", lambda: f'v{APP_VERSION}' in read('latest.json.template')),
    ("latest_docs", lambda: f'v{APP_VERSION}' in read('docs/latest.json.template')),
    ("installer_version", lambda: f'#define MyAppVersion "{APP_VERSION}"' in read('installer/FountainPenManager_Setup.iss')),
    ("readme_title", lambda: f'# FountainPen Manager v{APP_VERSION}' in read('README.md')),
    ("changelog_exists", lambda: (ROOT / 'CHANGELOG.md').exists()),
    ("report_exists", lambda: (ROOT / 'RELEASE_REPORT.md').exists()),
    ("branch_history_a", lambda: (ROOT / 'docs/history/CHANGELOG_0.2.79A_MANUFACTURER_FIRST_ROTATION_UX.md').exists()),
    ("branch_history_b", lambda: (ROOT / 'docs/history/RELEASE_REPORT_v0.2.79B_MANUFACTURER_FIRST_RELEASE_UI_RANDOM.md').exists()),
    # ── Hersteller-zuerst ────────────────────────────────────────────
    ("manufacturer_catalog", lambda: 'MANUFACTURER_DOMAINS: dict[str, tuple[str, ...]]' in read('logic/pen_dimensions_service.py')),
    ("manufacturer_multi_domain", lambda: '"pilot": ("pilotpen.eu", "pilotpen.com")' in read('logic/pen_dimensions_service.py')),
    ("manufacturer_overlay", lambda: 'manufacturer_domains.json' in read('logic/pen_dimensions_service.py')),
    ("manufacturer_token_match", lambda: 'set(key_tokens) <= brand_tokens' in read('logic/pen_dimensions_service.py')),
    ("manufacturer_subdomain_match", lambda: 'host.endswith("." + d)' in read('logic/pen_dimensions_service.py')),
    ("manufacturer_source_prefix", lambda: 'manufacturer:' in read('logic/pen_dimensions_service.py')),
    ("manufacturer_early_stop", lambda: 'confidence >= 0.65' in read('logic/pen_dimensions_service.py')),
    ("manufacturer_link_filter", lambda: 'links = [u for u in links if _host_matches(u, domain)]' in read('logic/pen_dimensions_service.py')),
    ("online_builder_exists", lambda: 'def build_online_dimension_search_urls' in read('logic/pen_dimensions_service.py')),
    ("pen_widget_overlay_wired", lambda: 'build_image_search_urls(brand, model, data_dir=data_dir)' in read('ui/pen_dialogs.py')),
    # ── Zufall: Ein-Pfad-Architektur (Guards aus dem RC-Vergleich) ───
    ("random_percent_setting", lambda: '"rotation_randomness_percent"' in read('logic/rotation_engine.py')),
    ("random_single_path", lambda: '_build_random_suggestion_set' not in read('logic/rotation_engine.py')),
    ("random_no_legacy_toggle", lambda: 'rotation_random_mode' not in read('logic/rotation_engine.py')),
    ("random_reject_filter", lambda: 'combo.get("auto_action") == "reject"' in read('logic/rotation_engine.py')),
    ("random_fixed_exempt", lambda: 'not combo.get("is_fixed") and (combo.get("has_blocked")' in read('logic/rotation_engine.py')),
    ("random_delta_tracked", lambda: '"random_delta"' in read('logic/rotation_engine.py')),
    ("random_pct_hint", lambda: 't("rotation.hint_random_mode", pct=' in read('logic/rotation_engine.py')),
    ("db_seeds_percent_only", lambda: '"rotation_randomness_percent": "0"' in read('database/db.py') and 'rotation_random_mode' not in read('database/db.py')),
    # ── Reroll: Paar-Sperre statt Tintensperre ───────────────────────
    ("reroll_pair_signature", lambda: 'avoid_pairs: set[tuple[int, int]] | None = None' in read('logic/rotation_engine.py')),
    ("reroll_pair_exclusion", lambda: '(pen.id, ink.id) in avoid and pen.fixed_ink_id != ink.id' in read('logic/rotation_engine.py')),
    ("reroll_fallback", lambda: 'respect_avoid=False' in read('logic/rotation_engine.py')),
    ("reroll_repeat_hint", lambda: 'rotation.hint_repeat_round' in read('logic/rotation_engine.py')),
    ("widget_pair_memory", lambda: '_avoid_pairs.update((s["pen_id"], s["ink_id"])' in read('ui/rotation_widget.py')),
    # ── UI-Klarheit ──────────────────────────────────────────────────
    ("dash_tile_class", lambda: 'class DashboardTile' in read('ui/dashboard_widget.py')),
    ("dash_single_detail", lambda: 'group.setVisible(selected)' in read('ui/dashboard_widget.py')),
    ("dash_focus_on_expand", lambda: 'table.setFocus(Qt.FocusReason.OtherFocusReason)' in read('ui/dashboard_widget.py')),
    ("dash_double_click_navigation", lambda: 'cellDoubleClicked.connect' in read('ui/dashboard_widget.py') and 'double_clicked.emit(self.page)' in read('ui/dashboard_widget.py')),
    ("dash_expert_tab_navigation", lambda: 'def _navigate_from_dashboard' in read('ui/main_window.py') and 'self.sidebar.set_mode(EXPERT_MODE)' in read('ui/main_window.py')),
    ("dash_click_debounce", lambda: '_single_click_timer.stop()' in read('ui/dashboard_widget.py')),
    ("dash_responsive_tiles", lambda: 'tile_columns, action_columns = 3, 4' in read('ui/dashboard_widget.py')),
    # v0.3.01: Timer-Schwelle/Limits leben nach der refresh()-Zerlegung im
    # Qt-freien logic.dashboard_service bzw. der Repository-Schicht.
    ("dash_timer_due_filter", lambda: 'TIMER_SOON_RATIO = 0.8' in read('logic/dashboard_service.py')
        and 'soon_ratio * r["max"]' in read('logic/dashboard_service.py')),
    ("dash_limits", lambda: 'activity_limit: int = 8' in read('logic/dashboard_service.py')
        and 'health_limit: int = 6' in read('logic/dashboard_service.py')
        and '.limit(limit)' in read('database/repositories.py')),
    ("rotation_wordwrap_off", lambda: 'sug_table.setWordWrap(False)' in read('ui/rotation_widget.py')),
    ("rotation_compact_hints", lambda: 'hint_parts[:2]' in read('ui/rotation_widget.py')),
    ("rotation_multiline_tooltip", lambda: '"\\n".join(full_lines)' in read('ui/rotation_widget.py')),
    ("rules_overview_top", lambda: 'rules.overview_explain' in read('ui/rules_widget.py')),
    ("rules_no_stacked_hints", lambda: 'regeln_sind_jetzt_in_reitern' not in read('ui/rules_widget.py')),
    ("rules_level_filter", lambda: 'level_filter' in read('ui/rules_widget.py')),
    ("rules_i18n_leak_fixed", lambda: '"Nein (Gruppe aus)"' not in read('ui/rules_widget.py')),
    ("settings_percent_spin", lambda: 'setRange(0, 100)' in read('ui/settings_widget.py')),
    ("settings_instant_refresh", lambda: '_refresh_all_widgets()' in read('ui/settings_widget.py').split('def _save_rotation_settings')[1].split('def ')[0]),
    # ── i18n-Parität der neuen Kerne ─────────────────────────────────
    ("i18n_pct_params", lambda: all('{pct}' in j(f'i18n/{l}.json')['rotation']['hint_random_mode'] for l in ('de', 'en', 'fr'))),
    # ── Hilfe-Abdeckung (v0.2.88) ────────────────────────────────────
    ("help_rotation_tab", lambda: '_add_rotation_tab' in read('ui/help_widget.py')),
    ("help_research_tab", lambda: '_add_research_tab' in read('ui/help_widget.py')),
    ("help_overlay_documented", lambda: all('manufacturer_domains.json' in j(f'i18n/{l}.json')['help']['research']['overlay_body'] for l in ('de', 'en', 'fr'))),
    ("help_generate_tooltip", lambda: '"rotation.generate_tooltip"' in read('ui/rotation_widget.py')),
    # ── Benutzerhandbuch (v0.2.88) ───────────────────────────────────
    ("manual_exists", lambda: (ROOT / 'docs' / 'BENUTZERHANDBUCH_DE.md').exists()),
    ("manual_linked_readme", lambda: 'docs/BENUTZERHANDBUCH_DE.md' in read('README.md')),
    ("manual_linked_help", lambda: 'help.manual_title' in read('ui/help_widget.py')),
    ("manuals_all_languages", lambda: all((ROOT / 'docs' / name).exists() for name in ('BENUTZERHANDBUCH_DE.md', 'USER_MANUAL_EN.md', 'MANUEL_UTILISATEUR_FR.md'))),
    ("help_search", lambda: 'def _filter_help' in read('ui/help_widget.py') and 'help.search_placeholder' in read('ui/help_widget.py')),
    ("context_help", lambda: 'def _open_context_help' in read('ui/main_window.py')),
    ("pen_unsaved_guard", lambda: 'def _has_unsaved_changes' in read('ui/pen_dialogs.py') and 'pen.discard_changes' in read('ui/pen_dialogs.py')),
    # ── Recherche-Query-Regression (v0.2.88) ────────────────────────
    ("site_query_helper", lambda: 'def _site_query_terms' in read('logic/pen_dimensions_service.py')),
    ("site_query_minimal_dim", lambda: 'f"site:{domain} {site_terms}"' in read('logic/pen_dimensions_service.py')),
    ("site_query_no_full_phrase", lambda: 'f"site:{domain} {query}"' not in read('logic/pen_dimensions_service.py')),
    ("auto_search_stable_endpoint", lambda: 'html.duckduckgo.com/html/' in read('logic/pen_dimensions_service.py')),
    # v0.2.88: bewusst asymmetrische Reihenfolge (Nutzervorgabe)
    ("dim_search_ai_first", lambda: _order_ok('build_dimension_search_urls', ai_before_site=True)),
    ("img_search_manufacturer_first", lambda: _order_ok('build_image_search_urls', ai_before_site=False)),
    ("search_cascade_ai_stage", lambda: 'ai_mode=True' in read('logic/pen_dimensions_service.py')),
    ("auto_lookup_manufacturer_first", lambda: 'manufacturer_domains_for_brand' in read('logic/pen_dimensions_service.py').split('def _phase_plan')[1].split('def ')[0]),
    # ── Neue 0.2.84-Features (aus Parallelzweig übernommen) ─────────
    ("media_service_exists", lambda: (ROOT / 'logic' / 'media_storage_service.py').exists()),
    ("media_service_size_cap", lambda: 'MAX_MEDIA_BYTES' in read('logic/media_storage_service.py')),
    ("media_service_path_guard", lambda: 'def is_inside' in read('logic/media_storage_service.py')),
    ("size_compare_dialog", lambda: 'size_compare_mode_overlay' in read('ui/pen_dialogs.py')),
    ("size_compare_metrics", lambda: all(k in read('ui/pen_dialogs.py') for k in ('size_compare_metric_closed', 'size_compare_metric_posted'))),
    # ── Release-Analyse v0.2.88: Datenverlust-Guards ────────────────
    ("media_import_non_fatal_pen", lambda: 'except Exception as exc:' in read('ui/pen_widget.py').split('def _store_pen_image_if_needed')[1].split('\n    def ')[0]),
    ("media_import_non_fatal_sample", lambda: 'except Exception as exc:' in read('ui/writing_samples_widget.py').split('def _store_sample_image_if_needed')[1].split('\n    def ')[0]),
    ("media_warning_after_commit", lambda: read('ui/pen_widget.py').count('self._warn_media_import_failed()') == 3),
    ("pen_add_rolls_back", lambda: 'session.rollback()' in read('ui/pen_widget.py').split('def _add(self):')[1].split('\n    def ')[0]),
    ("media_warning_keys", lambda: all('{error}' in j(f'i18n/{l}.json')['media']['import_failed_body'] for l in ('de', 'en', 'fr'))),
    ("lookup_opens_two_stages", lambda: '_open_first_stages' in read('ui/pen_dialogs.py')),
    # ── v0.2.88: Medien-Härtung + Cross-Platform ────────────────────
    ("media_magic_bytes", lambda: 'def detect_image_suffix' in read('logic/media_storage_service.py')),
    ("media_http_only", lambda: 'ALLOWED_DOWNLOAD_SCHEMES' in read('logic/media_storage_service.py')),
    ("media_safe_redirect", lambda: '_SafeRedirectHandler' in read('logic/media_storage_service.py')),
    ("media_timeout_lowered", lambda: 'DOWNLOAD_TIMEOUT_S = 8' in read('logic/media_storage_service.py')),
    ("media_worker_thread", lambda: (ROOT / 'ui' / 'media_download.py').exists() and 'QThread' in read('ui/media_download.py')),
    ("widgets_prefetch_off_thread", lambda: all('_prefetch_remote_image' in read(f'ui/{w}.py') for w in ('pen_widget', 'writing_samples_widget'))),
    ("reset_cleans_media_tree", lambda: 'reverse=True' in read('database/db.py').split('media_root = _data_dir')[1][:900]),
    ("crossplatform_spec", lambda: (ROOT / 'FPM.spec').exists()),
    ("crossplatform_build", lambda: (ROOT / 'tools' / 'build_release_assets.py').exists()),
    ("crossplatform_linux_docs", lambda: (ROOT / 'docs' / 'LINUX_RELEASE.md').exists()),
    # ── v0.2.92: Locale-/Währungs-Härtung ───────────────────────────
    ("localized_spinbox_exists", lambda: (ROOT / 'ui' / 'localized_inputs.py').exists()),
    ("no_raw_doublespinbox", lambda: all('QDoubleSpinBox()' not in read(f'ui/{w}.py') for w in ('pen_widget', 'ink_widget', 'paper_widget', 'expenses_widget', 'wishlist_widget', 'writing_samples_widget', 'enthusiast_lab_widget'))),
    ("parser_rejects_bad_groups", lambda: 'def _fail_if_bad_groups' in read('i18n/translator.py')),
    ("csv_uses_locale_parser", lambda: 'parse_number' in read('ui/pen_widget.py').split('def to_float')[1].split('def ')[0]),
    ("currency_codes_iso_fixed", lambda: '"CHF", "EUR", "USD", "GBP"' in read('ui/expenses_widget.py')),
    # ── v0.2.95: Füller-Formular-Datenerhalt ─────────────────────────
    ("spinbox_affix_strip", lambda: 'def strip_spinbox_affixes' in read('ui/localized_inputs.py')),
    ("spinbox_parser_uses_clean_text", lambda: 'parse_number(self._number_text(text))' in read('ui/localized_inputs.py')),
    ("spinbox_invalid_preserves_value", lambda: 'return float(self.value())' in read('ui/localized_inputs.py')),
    ("pen_input_regression_test", lambda: (ROOT / 'tests' / 'test_pen_numeric_input_persistence_0295.py').exists()),
    ("dashboard_tile_regression_test", lambda: (ROOT / 'tests' / 'test_dashboard_focus_tiles_0296.py').exists()),
    # ── v0.3.00: Onboarding-Neustart + Enterprise-Security ───────────
    ("onboarding_force_checked_tour", lambda: 'onboarding_force_next_start' in read('ui/tour_controller.py').split('def should_show_tour')[1].split('def ')[0]),
    ("onboarding_force_checked_wizard", lambda: 'onboarding_force_next_start' in read('ui/onboarding_wizard.py').split('def should_show_wizard')[1].split('def ')[0]),
    ("onboarding_reset_forces_next_start", lambda: 'AppSettings.set(session, "onboarding_force_next_start", "1")' in read('ui/tour_controller.py').split('def reset_tour')[1].split('def ')[0]),
    ("onboarding_completion_clears_force", lambda: all('AppSettings.set(session, "onboarding_force_next_start", "0")' in read(path) for path in ('ui/tour_controller.py', 'ui/onboarding_wizard.py'))),
    ("onboarding_wizard_single_entry", lambda: 'def start_onboarding_wizard' in read('ui/main_window.py') and 'wizard_sig.connect(self.start_onboarding_wizard)' in read('ui/main_window.py')),
    ("onboarding_wizard_settings_signal", lambda: 'wizard_requested = Signal()' in read('ui/settings_widget.py') and 'self.wizard_requested.emit()' in read('ui/settings_widget.py')),
    ("onboarding_i18n_all_languages", lambda: all('wizard_button' in j(f'i18n/{l}.json')['tour']['triggers'] and 'wizard_tooltip' in j(f'i18n/{l}.json')['tour']['triggers'] for l in ('de', 'en', 'fr'))),
    ("onboarding_regression_tests", lambda: (ROOT / 'tests' / 'test_onboarding_rerun_0300.py').exists()),
    ("image_url_ssrf_guard", lambda: 'def _is_safe_remote_image_url' in read('logic/image_url_security.py')
        and 'class _SafeImageRedirectHandler' in read('logic/image_url_security.py')
        and 'from logic.image_url_security import' in read('ui/pen_widget.py')
        and 'from logic.image_url_security import' in read('ui/pen_dialogs.py')),
    ("image_url_security_tests", lambda: (ROOT / 'tests' / 'test_enterprise_security_0300.py').exists()),
    ("bandit_release_gate", lambda: 'python -m bandit' in read('.github/workflows/release-check.yml') and 'bandit>=' in read('requirements-build.txt')),
    ("migration_static_sql", lambda: 'column_defs =' not in read('database/db.py') and 'insert_columns =' not in read('database/db.py')),
    # ── v0.3.01: Enterprise-Follow-up (Architektur, Coverage, Supply-Chain) ──
    ("dashboard_service_module", lambda: (ROOT / 'logic' / 'dashboard_service.py').exists()
        and 'def collect_dashboard_data' in read('logic/dashboard_service.py')
        and 'def build_timer_rows' in read('logic/dashboard_service.py')),
    ("dashboard_uses_service", lambda:
        'from logic.dashboard_service import collect_dashboard_data' in read('ui/dashboard_widget.py')
        and 'def _render_timer' in read('ui/dashboard_widget.py')
        and 'def _render_service' in read('ui/dashboard_widget.py')),
    ("dashboard_widget_query_free", lambda: read('ui/dashboard_widget.py').count('session.query(') == 0),
    ("repository_layer", lambda: (ROOT / 'database' / 'repositories.py').exists()
        and 'class PenRepository' in read('database/repositories.py')
        and 'class InkLoadRepository' in read('database/repositories.py')
        and 'def all_sorted' in read('database/repositories.py')),
    ("widgets_use_repositories", lambda:
        'PenRepository' in read('ui/pen_widget.py')
        and 'PenRepository(session).all_sorted()' in read('ui/pen_widget.py')
        and 'InkRepository' in read('ui/ink_widget.py')
        and 'InkRepository(session).all_sorted()' in read('ui/ink_widget.py')
        and 'InkRepository(session).usable_sorted()' in read('ui/pen_dialogs.py')),
    ("exception_ratchet_tool", lambda: (ROOT / 'tools' / 'exception_audit.py').exists()
        and 'BROAD_EXCEPTION_LIMIT = 146' in read('tools/exception_audit.py')
        and 'BARE_EXCEPT_LIMIT = 0' in read('tools/exception_audit.py')),
    ("db_access_ratchet_tool", lambda: (ROOT / 'tools' / 'db_access_audit.py').exists()
        and 'TOTAL_UI_QUERY_LIMIT = 49' in read('tools/db_access_audit.py')
        and '"dashboard_widget.py"' in read('tools/db_access_audit.py')),
    ("hardening_ratchets_in_ci", lambda:
        'python tools/exception_audit.py' in read('.github/workflows/release-check.yml')
        and 'python tools/db_access_audit.py' in read('.github/workflows/release-check.yml')
        and 'python tools/gen_lockfile.py --check' in read('.github/workflows/release-check.yml')),
    ("log_unexpected_helper", lambda: (ROOT / 'logic' / 'log_utils.py').exists()
        and 'def log_unexpected' in read('logic/log_utils.py')),
    ("dependency_lock_tool", lambda: (ROOT / 'tools' / 'gen_lockfile.py').exists()
        and '--generate-hashes' in read('tools/gen_lockfile.py')
        and 'def check(platform_name: str)' in read('tools/gen_lockfile.py')),
    ("windows_release_hash_install", lambda:
        'constraints-windows.lock' in read('.github/workflows/windows-release.yml')
        and 'constraints-linux.lock' in read('.github/workflows/windows-release.yml')
        and '--require-hashes --only-binary=:all:' in read('.github/workflows/windows-release.yml')),
    ("behavior_tests_present", lambda: all((ROOT / 'tests' / n).exists() for n in (
        'test_updater_behavior_0301.py',
        'test_rule_engine_behavior_0301.py',
        'test_rotation_engine_behavior_0301.py',
        'test_dashboard_service_0301.py',
        'test_pen_services_0302.py'))),
    ("sqlalchemy_stub_conditional", lambda:
        'except ImportError:' in read('tests/_stub_env.py')
        and 'import sqlalchemy' in read('tests/_stub_env.py')
        and 'install_sqlalchemy_stub()' in read('tests/conftest.py')),
    # ── v0.3.02: Pen-Zerlegung, Import-Smoke, Lock-CI ────────────────────
    ("pen_split_facade", lambda: (ROOT / 'ui' / 'pen_common.py').exists()
        and (ROOT / 'ui' / 'pen_dialogs.py').exists()
        and 'class PenDialog(' in read('ui/pen_dialogs.py')
        and 'from ui.pen_dialogs import' in read('ui/pen_widget.py')),
    ("pen_query_free_trio", lambda:
        read('ui/pen_widget.py').count('session.query(') == 0
        and read('ui/pen_dialogs.py').count('session.query(') == 0
        and read('ui/ink_widget.py').count('session.query(') == 0),
    ("pen_service_module", lambda: (ROOT / 'logic' / 'pen_service.py').exists()
        and 'def sync_purchase_expense_for_pen' in read('logic/pen_service.py')
        and 'def find_or_create_nib_format' in read('logic/pen_service.py')),
    ("import_smoke_gate", lambda: (ROOT / 'tools' / 'import_smoke.py').exists()
        and 'python tools/import_smoke.py' in read('.github/workflows/release-check.yml')),
    ("stub_env_module", lambda:
        'def install_sqlalchemy_stub' in read('tests/_stub_env.py')
        and 'def install_pyside6_stub' in read('tests/_stub_env.py')),
    ("lockfile_ci_workflow", lambda:
        (ROOT / '.github' / 'workflows' / 'generate-lockfile.yml').exists()
        and 'workflow_dispatch' in read('.github/workflows/generate-lockfile.yml')
        and 'gh pr create' in read('.github/workflows/generate-lockfile.yml')
        and 'upload-artifact' in read('.github/workflows/generate-lockfile.yml')),
    ("gui_smoke_dialog_paths", lambda:
        'dashboard.refresh()' in read('tools/gui_smoke_test.py')
        and 'PenDialog(window)' in read('tools/gui_smoke_test.py')
        and 'LoadInkDialog(window' in read('tools/gui_smoke_test.py')),
    # ── v0.3.04: Audit-Härtung (Namens-Gate, Split-Verlust-Schutz) ───────
    ("name_audit_gate", lambda: (ROOT / 'tools' / 'name_audit.py').exists()
        and 'UNUSED_IMPORT_LIMIT = 0' in read('tools/name_audit.py')
        and 'undefined_total' in read('tools/name_audit.py')
        and 'python tools/name_audit.py' in read('.github/workflows/release-check.yml')),
    ("service_help_restored", lambda: 'SERVICE_HELP = ' in read('ui/pen_dialogs.py')
        and "SERVICE_HELP.get(lang, SERVICE_HELP['de'])" in read('ui/pen_dialogs.py')),
    ("dialog_imports_complete", lambda: all(
        m in read('ui/pen_dialogs.py') for m in (
            'QInputDialog', 'from ui.ink_widget import InkDialog',
            'from ui.nib_widget import NibDialog',
            'from ui.role_prefs_dialog import RolePrefsDialog'))),
]


def main() -> int:
    raw_loops = os.environ.get("FPM_KILLCRITIC_LOOPS", "1000")
    try:
        loops = int(raw_loops)
    except ValueError:
        print(f"Ungültiger FPM_KILLCRITIC_LOOPS-Wert: {raw_loops!r}")
        return 2
    if loops < 1 or loops > 10000:
        print("FPM_KILLCRITIC_LOOPS muss zwischen 1 und 10000 liegen")
        return 2
    failures: list[str] = []
    for name, fn in CHECKS:
        for _ in range(loops):
            try:
                ok = bool(fn())
            except Exception as exc:  # noqa: BLE001 - Audit soll weiterlaufen
                ok = False
                failures.append(f"{name}: EXCEPTION {exc}")
                break
            if not ok:
                failures.append(name)
                break
    total = len(CHECKS) * loops
    if failures:
        print(f"KILLCRITIC 1000-loop audit: {len(failures)} FINDINGS bei {total} Checks")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"KILLCRITIC 1000-loop audit: OK ({len(CHECKS)} Invarianten × {loops} = {total} Checks, 0 Findings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
