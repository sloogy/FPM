"""Full Auto Mode: zentrale, erklärbare Entscheidungslogik.

Der normale Modus liefert Empfehlungen. Full Auto Mode darf Entscheidungen treffen,
aber jede Entscheidung muss erklärbar und protokollierbar bleiben.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from database.models import AppSettings, OverrideLog
from i18n.translator import t

RULE_GROUPS = {
    "safety": "auto_mode.group.safety",
    "maintenance": "auto_mode.group.maintenance",
    "rotation": "auto_mode.group.rotation",
    "pen": "auto_mode.group.pen",
    "ink": "auto_mode.group.ink",
    "ink_fill": "auto_mode.group.ink_fill",
    "consumption": "auto_mode.group.consumption",
    "nib": "auto_mode.group.nib",
    "paper": "auto_mode.group.paper",
    "collector": "auto_mode.group.collector",
}


def group_label(group: str | None) -> str:
    """Localized label for rule groups; returns the raw group as fallback."""
    if not group:
        return "—"
    key = RULE_GROUPS.get(group, f"auto_mode.group.{group}")
    label = t(key)
    return group if label == key else label


def action_label(action: str) -> str:
    """Localized label for internal Full-Auto actions."""
    key = f"auto_mode.action.{action or 'manual'}"
    label = t(key)
    return action if label == key else label




@dataclass
class AutoDecision:
    enabled: bool
    action: str  # allow / warn / reject / require_override
    explanation: str
    blocking_rule_ids: list[int]
    score: Optional[int] = None


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "ja", "on"}


class AutoModeService:
    @staticmethod
    def rules_enabled(session) -> bool:
        return _truthy(AppSettings.get(session, "rules_enabled", "1"), True)

    @staticmethod
    def full_auto_enabled(session) -> bool:
        return _truthy(AppSettings.get(session, "full_auto_mode", "0"), False)

    @staticmethod
    def group_enabled(session, group: str | None) -> bool:
        if not group:
            return True
        key = f"rule_group_{group}_enabled"
        return _truthy(AppSettings.get(session, key, "1"), True)

    @staticmethod
    def ink_fill_rules_enabled(session) -> bool:
        """Schaltet Regeln rund um Befüllen/Übernehmen separat."""
        return AutoModeService.group_enabled(session, "ink_fill")

    @staticmethod
    def ui_mode(session) -> str:
        """easy/expert. Im Easy Mode bleibt Verbrauchsautomatik bewusst aus."""
        return str(AppSettings.get(session, "ui_mode", "easy") or "easy").strip().lower()

    @staticmethod
    def consumption_tracking_enabled(session) -> bool:
        """Schaltet automatische Restmengen-/Verbrauchsbuchung separat.

        Sicherheitsregel:
        - Easy Mode: Verbrauch/Restmenge nie automatisch buchen.
        - Expert Mode: nur wenn die Regelgruppe consumption aktiv ist.
        """
        if AutoModeService.ui_mode(session) != "expert":
            return False
        return AutoModeService.group_enabled(session, "consumption")

    @staticmethod
    def decide(session, pen, ink, violations: Iterable, score: Optional[int] = None) -> AutoDecision:
        if not AutoModeService.full_auto_enabled(session):
            return AutoDecision(False, "manual", t("auto_mode.disabled"), [], score)

        can_reject = _truthy(AppSettings.get(session, "full_auto_can_reject", "1"), True)
        can_override = _truthy(AppSettings.get(session, "full_auto_can_override", "0"), False)
        blocking = [v for v in violations if v.warn_level == "blocked" or v.rule_type == "hard"]
        critical = [v for v in violations if v.warn_level == "critical"]
        warning = [v for v in violations if v.warn_level == "warning"]

        pen_name = f"{getattr(pen, 'brand', '')} {getattr(pen, 'model', '')}".strip()
        ink_name = f"{getattr(ink, 'brand', '')} {getattr(ink, 'name', '')}".strip()
        intro = t("auto_mode.intro", pen=pen_name, ink=ink_name)

        if blocking:
            names = "; ".join(v.rule_name for v in blocking)
            if can_reject:
                return AutoDecision(True, "reject", t("auto_mode.reject_blocking", intro=intro, names=names), [v.rule_id for v in blocking], score)
            if can_override:
                return AutoDecision(True, "require_override", t("auto_mode.require_override_hard_auto", intro=intro, names=names), [v.rule_id for v in blocking], score)
            return AutoDecision(True, "require_override", t("auto_mode.require_override_hard_manual", intro=intro, names=names), [v.rule_id for v in blocking], score)

        if critical:
            names = "; ".join(v.rule_name for v in critical)
            return AutoDecision(True, "warn", t("auto_mode.warn_critical", intro=intro, names=names), [v.rule_id for v in critical], score)

        if warning:
            names = "; ".join(v.rule_name for v in warning)
            return AutoDecision(True, "warn", t("auto_mode.warn_warning", intro=intro, names=names), [v.rule_id for v in warning], score)

        return AutoDecision(
            True,
            "allow",
            t("auto_mode.allow", intro=intro, score=score if score is not None else t("auto_mode.score_na")),
            [],
            score,
        )

    @staticmethod
    def log_decision(session, rule_ids: list[int], pen_id: int, ink_id: int, decision: AutoDecision, reason: str = "") -> None:
        if not _truthy(AppSettings.get(session, "full_auto_logging", "1"), True):
            return
        ids = rule_ids or [None]
        for rule_id in ids:
            if rule_id is None:
                continue
            session.add(OverrideLog(
                rule_id=rule_id,
                pen_id=pen_id,
                ink_id=ink_id,
                decision_mode="full_auto" if decision.enabled else "manual",
                action=decision.action,
                score_snapshot=decision.score,
                reason=reason or t("rotation.note_full_auto_decision"),
                explanation=decision.explanation,
            ))
