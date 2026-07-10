#!/usr/bin/env python3
"""KILLCRITIC 1000-Loop-Invarianten-Audit für v0.2.88 (Locale & Currency Hardening).

Release-/Logik-/UI-Invarianten × 20 Wiederholungen (Anzahl dynamisch, Ausgabe nennt die Summe).
Übernommen aus dem parallelen KILLCRITIC-RC und auf diesen Merge-Stand
portiert. Bewusst schnell und deterministisch (die Wiederholungen sind ein
Stabilitäts-Smoke, keine Zufallsläufe); die tiefe Prüfung bleibt pytest.

Enthält als dauerhafte Guards genau die Schwächen, die der Vergleich der
vorherigen 0.2.86-Merges aufgedeckt hat (Doppelpfad, Reject-Lücke, Tinten- statt
Paar-Sperre, Legacy-Setting-Seeding).
"""
from __future__ import annotations
import json
import sys
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def j(rel: str):
    return json.loads(read(rel))


def path_exists(rel: str) -> bool:
    return (ROOT / rel).exists()


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
    ("version_app", lambda: 'APP_VERSION = "0.2.88"' in read('app_info.py')),
    ("version_build", lambda: 'locale-currency-hardening' in read('app_info.py')),
    ("version_json", lambda: j('version.json')['version'] == '0.2.88'),
    ("version_info", lambda: 'Build: locale-currency-hardening' in read('VERSION_INFO.txt')),
    ("latest_root", lambda: 'v0.2.88' in read('latest.json.template')),
    ("latest_docs", lambda: 'v0.2.88' in read('docs/latest.json.template')),
    ("installer_version", lambda: '#define MyAppVersion "0.2.88"' in read('installer/FountainPenManager_Setup.iss')),
    ("readme_title", lambda: '# FountainPen Manager v0.2.88' in read('README.md')),
    ("changelog_exists", partial(path_exists, 'CHANGELOG_0.2.88_LOCALE_CURRENCY_HARDENING.md')),
    ("report_exists", partial(path_exists, 'RELEASE_REPORT_v0.2.88_LOCALE_CURRENCY_HARDENING.md')),
    ("branch_history_a", partial(path_exists, 'CHANGELOG_0.2.79A_MANUFACTURER_FIRST_ROTATION_UX.md')),
    ("branch_history_b", partial(path_exists, 'RELEASE_REPORT_v0.2.79B_MANUFACTURER_FIRST_RELEASE_UI_RANDOM.md')),
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
    ("pen_widget_overlay_wired", lambda: 'build_image_search_urls(brand, model, data_dir=data_dir)' in read('ui/pen_widget.py')),
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
    ("dash_four_cards", lambda: '_card_pens' not in read('ui/dashboard_widget.py')),
    ("dash_inventory_line", lambda: 'dashboard.inventory_line' in read('ui/dashboard_widget.py')),
    ("dash_timer_due_filter", lambda: '0.8 * r["max"]' in read('ui/dashboard_widget.py')),
    ("dash_limits", lambda: '.limit(8)' in read('ui/dashboard_widget.py') and 'limit=6,' in read('ui/dashboard_widget.py')),
    ("dash_compact_heights", lambda: 'setMaximumHeight(150)' in read('ui/dashboard_widget.py')),
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
    # ── Hilfe-Abdeckung ────────────────────────────────────
    ("help_rotation_tab", lambda: '_add_rotation_tab' in read('ui/help_widget.py')),
    ("help_research_tab", lambda: '_add_research_tab' in read('ui/help_widget.py')),
    ("help_overlay_documented", lambda: all('manufacturer_domains.json' in j(f'i18n/{l}.json')['help']['research']['overlay_body'] for l in ('de', 'en', 'fr'))),
    ("help_generate_tooltip", lambda: '"rotation.generate_tooltip"' in read('ui/rotation_widget.py')),
    # ── Benutzerhandbuch ───────────────────────────────────
    ("manual_exists", partial(path_exists, 'docs/BENUTZERHANDBUCH_DE.md')),
    ("manual_linked_readme", lambda: 'docs/BENUTZERHANDBUCH_DE.md' in read('README.md')),
    ("manual_linked_help", lambda: 'help.manual_title' in read('ui/help_widget.py')),
    # ── Recherche-Query-Regression ────────────────────────
    ("site_query_helper", lambda: 'def _site_query_terms' in read('logic/pen_dimensions_service.py')),
    ("site_query_minimal_dim", lambda: 'f"site:{domain} {site_terms}"' in read('logic/pen_dimensions_service.py')),
    ("site_query_no_full_phrase", lambda: 'f"site:{domain} {query}"' not in read('logic/pen_dimensions_service.py')),
    ("auto_search_stable_endpoint", lambda: 'html.duckduckgo.com/html/' in read('logic/pen_dimensions_service.py')),
    # bewusst asymmetrische Reihenfolge (Nutzervorgabe)
    ("dim_search_ai_first", lambda: _order_ok('build_dimension_search_urls', ai_before_site=True)),
    ("img_search_manufacturer_first", lambda: _order_ok('build_image_search_urls', ai_before_site=False)),
    ("search_cascade_ai_stage", lambda: 'ai_mode=True' in read('logic/pen_dimensions_service.py')),
    ("auto_lookup_manufacturer_first", lambda: 'manufacturer_domains_for_brand' in read('logic/pen_dimensions_service.py').split('def _phase_plan')[1].split('def ')[0]),
    # ── Neue 0.2.84-Features (aus Parallelzweig übernommen) ─────────
    ("media_service_exists", partial(path_exists, 'logic/media_storage_service.py')),
    ("media_service_size_cap", lambda: 'MAX_MEDIA_BYTES' in read('logic/media_storage_service.py')),
    ("media_service_path_guard", lambda: 'def is_inside' in read('logic/media_storage_service.py')),
    ("size_compare_dialog", lambda: 'size_compare_mode_overlay' in read('ui/pen_widget.py')),
    ("size_compare_metrics", lambda: all(k in read('ui/pen_widget.py') for k in ('size_compare_metric_closed', 'size_compare_metric_posted'))),
    # ── v0.2.88 Erststart, Backup, DB und Release-Härtung ─────────────
    ("fresh_db_no_sample_inks", lambda: '_insert_default_inks()' not in read('database/db.py')),
    ("tour_ink_before_pen", lambda: read('ui/tour_controller.py').find('"ink_add"') < read('ui/tour_controller.py').find('"pen_add"')),
    ("tour_action_stays_on_cancel", lambda: 'if not execute_step_action(step, self.main_window)' in read('ui/tour_controller.py')),
    ("tour_module_round_before_setup", lambda: read('ui/tour_controller.py').find('step("expert_intro"') < read('ui/tour_controller.py').find('step("setup_intro"') < read('ui/tour_controller.py').find('"ink_add"')),
    ("tour_expert_mode_temporary", lambda: 'mode="expert"' in read('ui/tour_controller.py') and 'mode="original"' in read('ui/tour_controller.py') and '_restore_original_mode' in read('ui/tour_controller.py')),
    ("rotation_toolbar_generates", lambda: 'self._run_page_action(5, "generate_suggestions")' in read('ui/main_window.py')),
    ("full_backup_service", partial(path_exists, 'logic/backup_service.py')),
    ("backup_manifest_checksums", lambda: 'sha256' in read('logic/backup_service.py') and 'PRAGMA integrity_check' in read('logic/backup_service.py')),
    ("restore_fallback", lambda: 'pre_restore_' in read('ui/settings_widget.py') and 'restore_backup_rollback_success' in read('ui/settings_widget.py')),
    ("foreign_keys_enabled", lambda: 'PRAGMA foreign_keys=ON' in read('database/db.py')),
    ("migration_fail_fast", lambda: 'raise RuntimeError(f"Datenbankmigration' in read('database/db.py')),
    ("manual_packaged_spec", lambda: 'BENUTZERHANDBUCH_DE.md' in read('FPM.spec')),
    ("manual_packaged_installer", lambda: 'BENUTZERHANDBUCH_DE.md' in read('installer/FountainPenManager_Setup.iss')),
    ("linux_ci_runtime_deps", lambda: 'pip install -r requirements.txt pytest' in read('.github/workflows/release-check.yml')),
    ("linux_ci_gui_smoke", lambda: 'python tools/gui_smoke_test.py' in read('.github/workflows/release-check.yml')),
    ("windows_ci_gui_smoke", lambda: 'python tools/gui_smoke_test.py' in read('.github/workflows/windows-release.yml')),
    ("updater_zip_fail_closed", lambda: 'Unsicherer Pfad im Update-Archiv' in read('updater/common.py')),
    # ── v0.2.88 Locale- und Währungshärtung ─────────────────────────
    ("locale_spinbox_central", partial(path_exists, 'ui/locale_widgets.py')),
    ("locale_parse_both_separators", lambda: 'parse_localized_number' in read('i18n/translator.py')),
    ("currency_iso_stable", lambda: 'normalize_currency_code' in read('i18n/translator.py')),
    ("currency_affix_dynamic", lambda: 'bind_currency_combo' in read('ui/locale_widgets.py')),
    ("currency_affix_live_locale_refresh", lambda: '_fpm_currency_code' in read('ui/locale_widgets.py') and 'QApplication.allWidgets()' in read('ui/settings_widget.py')),
    ("pen_currency_bound", lambda: 'bind_currency_combo(self.price_currency_combo, self.price_spin)' in read('ui/pen_widget.py')),
    ("expense_currency_bound", lambda: 'bind_currency_combo(self.currency_combo, self.amt_spin' in read('ui/expenses_widget.py')),
    ("fx_locale_parse", lambda: 'LocaleService.parse_localized_number' in read('ui/settings_widget.py')),
    ("separator_groups_independent", lambda: 'self.decimal_group = QButtonGroup' in read('ui/settings_widget.py') and 'self.thousands_group = QButtonGroup' in read('ui/settings_widget.py')),
    ("separator_space_supported", lambda: 'self.thou_space_rb' in read('ui/settings_widget.py') and '"FR":' in read('i18n/translator.py') and '"thousands_sep": " "' in read('i18n/translator.py')),
    ("separator_conflict_blocked", lambda: 'settings.separators_must_differ' in read('ui/settings_widget.py') and 'normalize_number_separators' in read('i18n/translator.py')),
    ("separator_empty_persists", lambda: 'if thousands_raw is None:' in read('i18n/translator.py')),
    ("currency_regression_tests", partial(path_exists, 'tests/test_locale_currency_consistency_0288.py')),
]


def main() -> int:
    loops = 20
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
