#!/usr/bin/env python3
"""KILLCRITIC 1000-Loop-Invarianten-Audit für v0.2.87 (Merge-Stand M).

Release-/Logik-/UI-Invarianten × 20 Wiederholungen (Anzahl dynamisch, Ausgabe nennt die Summe).
Übernommen aus dem parallelen KILLCRITIC-RC und auf diesen Merge-Stand
portiert. Bewusst schnell und deterministisch (die Wiederholungen sind ein
Stabilitäts-Smoke, keine Zufallsläufe); die tiefe Prüfung bleibt pytest.

Enthält als dauerhafte Guards genau die Schwächen, die der Vergleich der
beiden 0.2.87-Merges aufgedeckt hat (Doppelpfad, Reject-Lücke, Tinten- statt
Paar-Sperre, Legacy-Setting-Seeding).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def j(rel: str):
    return json.loads(read(rel))


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
    ("version_app", lambda: 'APP_VERSION = "0.2.87"' in read('app_info.py')),
    ("version_build", lambda: 'release-audit-media-hardening' in read('app_info.py')),
    ("version_json", lambda: j('version.json')['version'] == '0.2.87'),
    ("version_info", lambda: 'Build: release-audit-media-hardening' in read('VERSION_INFO.txt')),
    ("latest_root", lambda: 'v0.2.87' in read('latest.json.template')),
    ("latest_docs", lambda: 'v0.2.87' in read('docs/latest.json.template')),
    ("installer_version", lambda: '#define MyAppVersion "0.2.87"' in read('installer/FountainPenManager_Setup.iss')),
    ("readme_title", lambda: '# FountainPen Manager v0.2.87' in read('README.md')),
    ("changelog_exists", lambda: (ROOT / 'CHANGELOG_0.2.87_RELEASE_AUDIT.md').exists()),
    ("report_exists", lambda: (ROOT / 'RELEASE_REPORT_v0.2.87_RELEASE_AUDIT.md').exists()),
    ("branch_history_a", lambda: (ROOT / 'CHANGELOG_0.2.79A_MANUFACTURER_FIRST_ROTATION_UX.md').exists()),
    ("branch_history_b", lambda: (ROOT / 'RELEASE_REPORT_v0.2.79B_MANUFACTURER_FIRST_RELEASE_UI_RANDOM.md').exists()),
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
    # ── Hilfe-Abdeckung (v0.2.87) ────────────────────────────────────
    ("help_rotation_tab", lambda: '_add_rotation_tab' in read('ui/help_widget.py')),
    ("help_research_tab", lambda: '_add_research_tab' in read('ui/help_widget.py')),
    ("help_overlay_documented", lambda: all('manufacturer_domains.json' in j(f'i18n/{l}.json')['help']['research']['overlay_body'] for l in ('de', 'en', 'fr'))),
    ("help_generate_tooltip", lambda: '"rotation.generate_tooltip"' in read('ui/rotation_widget.py')),
    # ── Benutzerhandbuch (v0.2.87) ───────────────────────────────────
    ("manual_exists", lambda: (ROOT / 'docs' / 'BENUTZERHANDBUCH_DE.md').exists()),
    ("manual_linked_readme", lambda: 'docs/BENUTZERHANDBUCH_DE.md' in read('README.md')),
    ("manual_linked_help", lambda: 'help.manual_title' in read('ui/help_widget.py')),
    # ── Recherche-Query-Regression (v0.2.87) ────────────────────────
    ("site_query_helper", lambda: 'def _site_query_terms' in read('logic/pen_dimensions_service.py')),
    ("site_query_minimal_dim", lambda: 'f"site:{domain} {site_terms}"' in read('logic/pen_dimensions_service.py')),
    ("site_query_no_full_phrase", lambda: 'f"site:{domain} {query}"' not in read('logic/pen_dimensions_service.py')),
    ("auto_search_stable_endpoint", lambda: 'html.duckduckgo.com/html/' in read('logic/pen_dimensions_service.py')),
    # v0.2.87: bewusst asymmetrische Reihenfolge (Nutzervorgabe)
    ("dim_search_ai_first", lambda: _order_ok('build_dimension_search_urls', ai_before_site=True)),
    ("img_search_manufacturer_first", lambda: _order_ok('build_image_search_urls', ai_before_site=False)),
    ("search_cascade_ai_stage", lambda: 'ai_mode=True' in read('logic/pen_dimensions_service.py')),
    ("auto_lookup_manufacturer_first", lambda: 'manufacturer_domains_for_brand' in read('logic/pen_dimensions_service.py').split('def _phase_plan')[1].split('def ')[0]),
    # ── Neue 0.2.84-Features (aus Parallelzweig übernommen) ─────────
    ("media_service_exists", lambda: (ROOT / 'logic' / 'media_storage_service.py').exists()),
    ("media_service_size_cap", lambda: 'MAX_MEDIA_BYTES' in read('logic/media_storage_service.py')),
    ("media_service_path_guard", lambda: 'def is_inside' in read('logic/media_storage_service.py')),
    ("size_compare_dialog", lambda: 'size_compare_mode_overlay' in read('ui/pen_widget.py')),
    ("size_compare_metrics", lambda: all(k in read('ui/pen_widget.py') for k in ('size_compare_metric_closed', 'size_compare_metric_posted'))),
    # ── Release-Analyse v0.2.87: Datenverlust-Guards ────────────────
    ("media_import_non_fatal_pen", lambda: 'except Exception as exc:' in read('ui/pen_widget.py').split('def _store_pen_image_if_needed')[1].split('\n    def ')[0]),
    ("media_import_non_fatal_sample", lambda: 'except Exception as exc:' in read('ui/writing_samples_widget.py').split('def _store_sample_image_if_needed')[1].split('\n    def ')[0]),
    ("media_warning_after_commit", lambda: read('ui/pen_widget.py').count('self._warn_media_import_failed()') == 3),
    ("pen_add_rolls_back", lambda: 'session.rollback()' in read('ui/pen_widget.py').split('def _add(self):')[1].split('\n    def ')[0]),
    ("media_warning_keys", lambda: all('{error}' in j(f'i18n/{l}.json')['media']['import_failed_body'] for l in ('de', 'en', 'fr'))),
    ("lookup_opens_two_stages", lambda: '_open_first_stages' in read('ui/pen_widget.py')),
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
