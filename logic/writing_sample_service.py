"""Schreibproben-Logik für Enthusiasten und Hobby-Sammler.

Die UI soll wie ein kleiner Scrivener-Binder wirken: links Gruppen/Ordner,
rechts die konkreten Proben. Dieses Modul ist bewusst Qt-frei und testbar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Mapping, Any


@dataclass(frozen=True)
class SampleIssue:
    """Kompakter Hinweis zu einer Schreibprobe."""

    code: str
    severity: str
    detail: str = ""


@dataclass
class BinderNode:
    """Scrivener-artiger Binder-Knoten.

    node_type:
      * root/group: reiner Ordner
      * sample: echte Schreibprobe
    """

    title: str
    node_type: str = "group"
    sample_id: int | None = None
    children: list["BinderNode"] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def add_child(self, child: "BinderNode") -> "BinderNode":
        self.children.append(child)
        return child


def _label(obj: Any, *fields: str, fallback: str = "—") -> str:
    if obj is None:
        return fallback
    values = [str(getattr(obj, f, "") or "").strip() for f in fields]
    text = " ".join(v for v in values if v).strip()
    return text or fallback


def _sample_title(sample: Any) -> str:
    title = str(getattr(sample, "title", "") or "").strip()
    return title or f"Sample #{getattr(sample, 'id', '—')}"


def suggested_sample_title(pen: Any = None, ink: Any = None, paper: Any = None) -> str:
    """DAU-freundlicher Titel aus der Kombination.

    So muss der Nutzer nicht jedes Mal selbst einen sinnvollen Namen erfinden.
    """
    parts = [
        _label(pen, "brand", "model", fallback=""),
        _label(ink, "brand", "name", fallback=""),
        _label(paper, "brand", "name", fallback=""),
    ]
    parts = [p for p in parts if p]
    return " · ".join(parts) if parts else "Neue Schreibprobe"


def evaluate_sample(sample: Any) -> list[SampleIssue]:
    """Findet fachliche Warnungen ohne GUI-Abhängigkeit."""
    issues: list[SampleIssue] = []
    if not getattr(sample, "pen_id", None):
        issues.append(SampleIssue("missing_pen", "warning"))
    if not getattr(sample, "ink_id", None):
        issues.append(SampleIssue("missing_ink", "warning"))
    if not getattr(sample, "paper_id", None):
        issues.append(SampleIssue("missing_paper", "info"))
    if not (getattr(sample, "image_path", None) or getattr(sample, "sample_text", None)):
        issues.append(SampleIssue("missing_evidence", "info"))

    feathering = int(getattr(sample, "feathering_level", 1) or 1)
    bleed = int(getattr(sample, "bleedthrough_level", 1) or 1)
    dry = getattr(sample, "dry_time_seconds", None)
    rating = int(getattr(sample, "overall_rating", 3) or 3)

    if feathering >= 4:
        issues.append(SampleIssue("heavy_feathering", "critical", str(feathering)))
    if bleed >= 4:
        issues.append(SampleIssue("heavy_bleedthrough", "critical", str(bleed)))
    if dry is not None and float(dry) >= 45:
        issues.append(SampleIssue("slow_dry", "warning", str(int(float(dry)))))
    if rating <= 2:
        issues.append(SampleIssue("low_rating", "warning", str(rating)))
    return issues


def sample_quality_score(sample: Any) -> int:
    """Ein einfacher Sortierscore: Lieblingskombinationen nach oben."""
    rating = int(getattr(sample, "overall_rating", 3) or 3)
    feathering = int(getattr(sample, "feathering_level", 1) or 1)
    bleed = int(getattr(sample, "bleedthrough_level", 1) or 1)
    flow = int(getattr(sample, "flow_level", 3) or 3)
    feedback = int(getattr(sample, "feedback_level", 3) or 3)
    evidence_bonus = 5 if (getattr(sample, "image_path", None) or getattr(sample, "sample_text", None)) else 0
    # Mittelwerte um 3 sind neutral; extreme Probleme ziehen stärker ab.
    return rating * 20 + flow * 3 + feedback * 2 + evidence_bonus - feathering * 8 - bleed * 8


def _group_node(parent: BinderNode, title: str, key: str, seen: dict[str, BinderNode]) -> BinderNode:
    full_key = f"{parent.title}/{key}"
    if full_key in seen:
        return seen[full_key]
    node = BinderNode(title=title, node_type="group", meta={"key": key})
    parent.add_child(node)
    seen[full_key] = node
    return node


def build_binder_tree(
    samples: Iterable[Any],
    pens_by_id: Mapping[int, Any] | None = None,
    inks_by_id: Mapping[int, Any] | None = None,
    papers_by_id: Mapping[int, Any] | None = None,
) -> BinderNode:
    """Baut eine Scrivener-artige Struktur.

    Aufbau:
      Sammlung
      ├─ Nach Füller
      │  └─ Marke Modell
      │     └─ Probe
      ├─ Nach Tinte
      ├─ Nach Papier
      ├─ Highlights
      └─ Prüfen
    """
    pens_by_id = pens_by_id or {}
    inks_by_id = inks_by_id or {}
    papers_by_id = papers_by_id or {}
    ordered = sorted(
        list(samples),
        key=lambda s: (getattr(s, "written_at", None) or datetime.min),
        reverse=True,
    )

    root = BinderNode("Sammlung", "root")
    by_pen = root.add_child(BinderNode("Nach Füller"))
    by_ink = root.add_child(BinderNode("Nach Tinte"))
    by_paper = root.add_child(BinderNode("Nach Papier"))
    highlights = root.add_child(BinderNode("Highlights"))
    review = root.add_child(BinderNode("Prüfen"))
    seen: dict[str, BinderNode] = {}

    for sample in ordered:
        sid = getattr(sample, "id", None)
        title = _sample_title(sample)
        pen = pens_by_id.get(getattr(sample, "pen_id", None))
        ink = inks_by_id.get(getattr(sample, "ink_id", None))
        paper = papers_by_id.get(getattr(sample, "paper_id", None))
        issues = evaluate_sample(sample)
        meta = {
            "quality_score": sample_quality_score(sample),
            "issues": [i.code for i in issues],
        }
        sample_node = BinderNode(title, "sample", sid, meta=meta)

        pen_group = _group_node(by_pen, _label(pen, "brand", "model", fallback="Ohne Füller"), f"pen:{getattr(sample, 'pen_id', None)}", seen)
        pen_group.add_child(sample_node)
        ink_group = _group_node(by_ink, _label(ink, "brand", "name", fallback="Ohne Tinte"), f"ink:{getattr(sample, 'ink_id', None)}", seen)
        ink_group.add_child(BinderNode(title, "sample", sid, meta=meta.copy()))
        paper_group = _group_node(by_paper, _label(paper, "brand", "name", fallback="Ohne Papier"), f"paper:{getattr(sample, 'paper_id', None)}", seen)
        paper_group.add_child(BinderNode(title, "sample", sid, meta=meta.copy()))

        if int(getattr(sample, "overall_rating", 3) or 3) >= 5:
            highlights.add_child(BinderNode(title, "sample", sid, meta=meta.copy()))
        if issues:
            review.add_child(BinderNode(title, "sample", sid, meta=meta.copy()))

    # Leere Spezialordner sichtbar lassen, aber mit Meta markieren.
    for node in (highlights, review):
        node.meta["empty"] = not bool(node.children)
    return root


def flatten_sample_ids(node: BinderNode) -> list[int]:
    """Hilfsfunktion für Tests/Filter: alle Sample-IDs in Anzeige-Reihenfolge."""
    ids: list[int] = []
    if node.node_type == "sample" and node.sample_id is not None:
        ids.append(int(node.sample_id))
    for child in node.children:
        ids.extend(flatten_sample_ids(child))
    return ids

@dataclass(frozen=True)
class SampleComparisonRow:
    """Eine Probe in der Vergleichsansicht."""

    sample_id: int | None
    title: str
    pen_label: str
    ink_label: str
    paper_label: str
    quality_score: int
    dry_time_seconds: float | None
    feathering_level: int
    bleedthrough_level: int
    shading_level: int
    sheen_level: int
    flow_level: int
    feedback_level: int
    overall_rating: int
    verdict: str


@dataclass(frozen=True)
class SampleComparison:
    rows: list[SampleComparisonRow]
    winner_id: int | None
    warnings: list[str]


def compare_samples(
    samples: Iterable[Any],
    pens_by_id: Mapping[int, Any] | None = None,
    inks_by_id: Mapping[int, Any] | None = None,
    papers_by_id: Mapping[int, Any] | None = None,
) -> SampleComparison:
    """Vergleicht 2–4 Schreibproben nebeneinander.

    Die Funktion ist bewusst tolerant: Sie bricht bei fehlenden Links nicht ab,
    sondern erzeugt Warnungen. Dadurch bleibt die Vergleichsansicht optional und
    nutzbar, auch wenn der Nutzer nur Textproben ohne vollständige Verknüpfung
    angelegt hat.
    """
    pens_by_id = pens_by_id or {}
    inks_by_id = inks_by_id or {}
    papers_by_id = papers_by_id or {}
    all_samples = list(samples)
    selected = all_samples[:4]
    warnings: list[str] = []
    if len(selected) < 2:
        warnings.append("need_at_least_two")
    if len(all_samples) > 4:
        warnings.append("limited_to_four")

    rows: list[SampleComparisonRow] = []
    for sample in selected:
        issues = evaluate_sample(sample)
        score = sample_quality_score(sample)
        if any(issue.severity == "critical" for issue in issues):
            verdict = "problem"
        elif int(getattr(sample, "overall_rating", 3) or 3) >= 5 and score >= 85:
            verdict = "excellent"
        elif score >= 65:
            verdict = "good"
        else:
            verdict = "check"
        rows.append(SampleComparisonRow(
            sample_id=getattr(sample, "id", None),
            title=_sample_title(sample),
            pen_label=_label(pens_by_id.get(getattr(sample, "pen_id", None)), "brand", "model", fallback="—"),
            ink_label=_label(inks_by_id.get(getattr(sample, "ink_id", None)), "brand", "name", fallback="—"),
            paper_label=_label(papers_by_id.get(getattr(sample, "paper_id", None)), "brand", "name", fallback="—"),
            quality_score=score,
            dry_time_seconds=getattr(sample, "dry_time_seconds", None),
            feathering_level=int(getattr(sample, "feathering_level", 1) or 1),
            bleedthrough_level=int(getattr(sample, "bleedthrough_level", 1) or 1),
            shading_level=int(getattr(sample, "shading_level", 3) or 3),
            sheen_level=int(getattr(sample, "sheen_level", 0) or 0),
            flow_level=int(getattr(sample, "flow_level", 3) or 3),
            feedback_level=int(getattr(sample, "feedback_level", 3) or 3),
            overall_rating=int(getattr(sample, "overall_rating", 3) or 3),
            verdict=verdict,
        ))
    winner_id = None
    if rows:
        eligible = [row for row in rows if row.verdict != "problem"]
        if not eligible:
            eligible = rows
            warnings.append("winner_has_problem")
        winner = max(eligible, key=lambda r: (r.quality_score, r.overall_rating, -r.feathering_level, -r.bleedthrough_level))
        winner_id = winner.sample_id
    return SampleComparison(rows=rows, winner_id=winner_id, warnings=warnings)
