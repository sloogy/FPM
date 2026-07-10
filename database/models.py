"""
FountainPen Manager – Datenbankmodelle
Alle SQLAlchemy-Entitäten für Füller, Tinten, Federn, Papier, etc.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Integer, String, Float, Boolean, DateTime, Text, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Füller
# ---------------------------------------------------------------------------
class Pen(Base):
    __tablename__ = "pens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(100))
    color: Mapped[Optional[str]] = mapped_column(String(100))
    fill_system: Mapped[str] = mapped_column(String(20), default="converter")

    purchase_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    purchase_price: Mapped[Optional[float]] = mapped_column(Float)
    purchase_currency: Mapped[Optional[str]] = mapped_column(String(3))
    current_market_value: Mapped[Optional[float]] = mapped_column(Float)
    market_currency: Mapped[Optional[str]] = mapped_column(String(3))
    insurance_value: Mapped[Optional[float]] = mapped_column(Float)
    insurance_currency: Mapped[Optional[str]] = mapped_column(String(3))

    # Abmessungen
    length_mm: Mapped[Optional[float]] = mapped_column(Float)          # geschlossen / capped
    length_uncapped_mm: Mapped[Optional[float]] = mapped_column(Float) # offen / uncapped
    length_posted_mm: Mapped[Optional[float]] = mapped_column(Float)   # gepostet
    diameter_mm: Mapped[Optional[float]] = mapped_column(Float)        # größter Durchmesser
    section_diameter_mm: Mapped[Optional[float]] = mapped_column(Float)# Griffdurchmesser
    weight_g: Mapped[Optional[float]] = mapped_column(Float)

    # Tags (kommagetrennt: grail, problem, collector, vintage)
    tags: Mapped[Optional[str]] = mapped_column(String(200))

    # Notizen
    writing_feel_notes: Mapped[Optional[str]] = mapped_column(Text)
    problem_notes: Mapped[Optional[str]] = mapped_column(Text)
    cleaning_notes: Mapped[Optional[str]] = mapped_column(Text)

    image_path: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Sperr-/Service-Status (Rotation soll diese Füller ignorieren)
    availability_status: Mapped[str] = mapped_column(String(30), default="available")  # available / problem / service / blocked / dry_risk
    rotation_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    blocked_until: Mapped[Optional[datetime]] = mapped_column(DateTime)
    service_start_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    service_days: Mapped[Optional[int]] = mapped_column(Integer)
    service_cost: Mapped[Optional[float]] = mapped_column(Float)
    service_currency: Mapped[Optional[str]] = mapped_column(String(3))
    service_notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # FK zur Feder (optional, da Federn manchmal fest eingebaut)
    nib_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("nibs.id"))

    # Rotation & Verbrauch
    ink_capacity_ml: Mapped[Optional[float]] = mapped_column(Float)
    popularity_rating: Mapped[int] = mapped_column(Integer, default=3)  # 1=selten, 5=Liebling
    must_include_in_rotation: Mapped[bool] = mapped_column(Boolean, default=False)
    fixed_ink_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("inks.id"))
    rotation_role: Mapped[Optional[str]] = mapped_column(String(50), default="writer")  # edc / agenda / journal / work / creative / ...
    rotation_theme: Mapped[Optional[str]] = mapped_column(String(50))  # Standard-Kontext für Vorschläge

    # Feder-Kompatibilität am Füller
    compatible_nibs: Mapped[Optional[str]] = mapped_column(Text)
    incompatible_nibs: Mapped[Optional[str]] = mapped_column(Text)
    nib: Mapped[Optional["Nib"]] = relationship("Nib", back_populates="pens", foreign_keys=[nib_id])
    fixed_ink: Mapped[Optional["Ink"]] = relationship("Ink", foreign_keys=[fixed_ink_id])
    nib_setups: Mapped[List["PenNibSetup"]] = relationship(
        "PenNibSetup", back_populates="pen", cascade="all, delete-orphan"
    )

    ink_loads: Mapped[List["InkLoad"]] = relationship(
        "InkLoad", back_populates="pen", cascade="all, delete-orphan"
    )
    writing_samples: Mapped[List["WritingSample"]] = relationship(
        "WritingSample", back_populates="pen", cascade="all, delete-orphan"
    )
    cleaning_logs: Mapped[List["CleaningLog"]] = relationship(
        "CleaningLog", back_populates="pen", cascade="all, delete-orphan"
    )
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="pen", cascade="all, delete-orphan"
    )

    @property
    def active_nib_setup(self) -> Optional["PenNibSetup"]:
        """Aktuelle Einbau-/Setup-Ebene: diese Feder in diesem Füller mit diesem Feed.

        Das alte Feld ``pen.nib`` bleibt als schnelle/kompatible Verknüpfung erhalten.
        Die Regeln sollen aber bevorzugt das aktive Setup lesen, weil Schreibgefühl
        und Feed vom konkreten Einbau abhängen.
        """
        for setup in self.nib_setups:
            if setup.is_active and setup.removed_date is None:
                return setup
        return None

    @property
    def current_ink_load(self) -> Optional["InkLoad"]:
        for load in self.ink_loads:
            if load.cleaned_date is None:
                return load
        return None

    @property
    def tags_list(self) -> List[str]:
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    def __repr__(self):
        return f"<Pen {self.brand} {self.model}>"


# ---------------------------------------------------------------------------
# Feder
# ---------------------------------------------------------------------------
class NibFormat(Base):
    """Format/Standard einer Feder (z.B. Bock #6, Jowo #6, Pilot #10).

    Bestimmt die KOMPATIBILITÄT mit Füller-Häusern (passt in welchen Füller),
    NICHT das Schreibgefühl. Ein Format wird typischerweise von vielen
    Exemplaren (Nib-Units) geteilt.
    """
    __tablename__ = "nib_formats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manufacturer: Mapped[str] = mapped_column(String(100))                 # Bock, Jowo, Schmidt, Pilot …
    physical_size: Mapped[Optional[str]] = mapped_column(String(30))       # #5, #6, #8, Pilot #10, Lamy 2000 …
    is_proprietary: Mapped[bool] = mapped_column(Boolean, default=False)
    compatible_with: Mapped[Optional[str]] = mapped_column(Text)           # Freitext-Liste: Füller/Häuser, die dieses Format aufnehmen
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    units: Mapped[List["Nib"]] = relationship("Nib", back_populates="format")

    @property
    def label(self) -> str:
        bits = [self.manufacturer or "", self.physical_size or ""]
        if self.is_proprietary:
            bits.append("(proprietär)")
        return " ".join(b for b in bits if b).strip() or "Unbekanntes Format"

    def __repr__(self):
        return f"<NibFormat {self.label}>"


class Nib(Base):
    """Exemplar/Einheit einer Feder.

    Trägt das individuelle SCHREIBGEFÜHL (Material, Schliff, Bezug/Tuner,
    Feed, Steifigkeit, Smoothness …). Verweist über `format_id` auf das
    Kompatibilitäts-Format. Zwei Bock #6 vom selben Tuner sind unterschiedliche
    Exemplare – Duplikate werden NICHT mehr automatisch verschmolzen.
    """
    __tablename__ = "nibs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    format_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("nib_formats.id"))
    # Legacy-Felder: bleiben als Fallback erhalten (alte DBs, schnelle Filter).
    # Bei vorhandenem Format hat das Format Vorrang (siehe effective_* / display_label).
    manufacturer: Mapped[Optional[str]] = mapped_column(String(100))
    physical_size: Mapped[Optional[str]] = mapped_column(String(30))
    is_proprietary: Mapped[bool] = mapped_column(Boolean, default=False)
    # Exemplar-Felder (Feel)
    size: Mapped[Optional[str]] = mapped_column(String(20))                # Feinheit: EF, F, M, B, Stub 1.1
    material: Mapped[Optional[str]] = mapped_column(String(50))            # Stahl, 14k, 18k, Titan
    grind: Mapped[Optional[str]] = mapped_column(String(100))              # Italic, CI, Custom
    nibmeister: Mapped[Optional[str]] = mapped_column(String(100))         # Person, die geschliffen hat
    source: Mapped[Optional[str]] = mapped_column(String(100))             # NEU: Bezug/Tuner: Gravitas, FNF, Shop …
    feed_type: Mapped[Optional[str]] = mapped_column(String(50))           # NEU: Standard, Ebonit, Custom
    feed_notes: Mapped[Optional[str]] = mapped_column(Text)                # NEU: freie Feed-Beschreibung
    stiffness_level: Mapped[int] = mapped_column(Integer, default=4)       # NEU: 1=sehr weich/flex … 5=sehr steif
    feedback_level: Mapped[int] = mapped_column(Integer, default=3)        # 1=nano-smooth … 5=sehr rau
    is_flexible: Mapped[bool] = mapped_column(Boolean, default=False)      # bleibt für Kompatibilität; aus stiffness ableitbar
    tuning_notes: Mapped[Optional[str]] = mapped_column(Text)              # NEU: was wurde getunt, von wem
    label: Mapped[Optional[str]] = mapped_column(String(120))              # NEU: Spitzname, z.B. "Gravitas-tuned"
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    format: Mapped[Optional["NibFormat"]] = relationship("NibFormat", back_populates="units")
    pens: Mapped[List["Pen"]] = relationship("Pen", back_populates="nib")
    setups: Mapped[List["PenNibSetup"]] = relationship(
        "PenNibSetup", back_populates="nib"
    )
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="nib", cascade="all, delete-orphan"
    )

    # ── effektive Werte: Format hat Vorrang, Legacy als Fallback ────────
    @property
    def effective_manufacturer(self) -> Optional[str]:
        if self.format and self.format.manufacturer:
            return self.format.manufacturer
        return self.manufacturer

    @property
    def effective_physical_size(self) -> Optional[str]:
        if self.format and self.format.physical_size:
            return self.format.physical_size
        return self.physical_size

    @property
    def effective_is_proprietary(self) -> bool:
        if self.format is not None:
            return bool(self.format.is_proprietary)
        return bool(self.is_proprietary)

    @property
    def display_label(self) -> str:
        """Lesbarer Name fürs UI, der Exemplar UND Format zeigt."""
        if self.label:
            return self.label
        parts: list[str] = []
        mfr = self.effective_manufacturer
        phys = self.effective_physical_size
        if mfr: parts.append(mfr)
        if phys: parts.append(phys)
        if self.size: parts.append(self.size)
        if self.grind: parts.append(self.grind)
        if self.material: parts.append(self.material)
        if self.source: parts.append(f"({self.source})")
        return " ".join(parts).strip() or "Unbenannte Feder"

    def __repr__(self):
        return f"<Nib {self.display_label}>"


class PenNibSetup(Base):
    """Einbau-/Setup-Ebene: eine konkrete Feder in einem konkreten Füller.

    Warum getrennt von Nib?
    - NibFormat beschreibt mechanische Kompatibilität (z.B. Bock #6).
    - Nib beschreibt das Feder-Exemplar (z.B. Gravitas-getunte EF).
    - PenNibSetup beschreibt, wie genau dieses Exemplar in DIESEM Füller
      mit DIESEM Feed schreibt (Flow, Steifigkeitseindruck, Feedback).

    Beispiel: dieselbe Bock #6 kann im Gravitas Sentry anders wirken als
    im Jinhao x750, weil Feed und Gehäuse den Flow/Feel verändern.
    """
    __tablename__ = "pen_nib_setups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pen_id: Mapped[int] = mapped_column(Integer, ForeignKey("pens.id"), nullable=False)
    nib_id: Mapped[int] = mapped_column(Integer, ForeignKey("nibs.id"), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    installed_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    removed_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    setup_label: Mapped[Optional[str]] = mapped_column(String(150))
    install_reason: Mapped[Optional[str]] = mapped_column(Text)
    removal_reason: Mapped[Optional[str]] = mapped_column(Text)
    feed_type: Mapped[Optional[str]] = mapped_column(String(80))
    feed_notes: Mapped[Optional[str]] = mapped_column(Text)
    flow_level: Mapped[int] = mapped_column(Integer, default=3)             # 1=trocken … 5=sehr nass
    wetness_feel_level: Mapped[int] = mapped_column(Integer, default=3)     # praktischer Eindruck im Füller
    stiffness_feel_level: Mapped[int] = mapped_column(Integer, default=3)   # 1=weicher … 5=steifer Eindruck
    feedback_level: Mapped[int] = mapped_column(Integer, default=3)         # 1=glatt … 5=feedback/kratzig
    compatibility_notes: Mapped[Optional[str]] = mapped_column(Text)
    feel_notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    pen: Mapped["Pen"] = relationship("Pen", back_populates="nib_setups")
    nib: Mapped["Nib"] = relationship("Nib", back_populates="setups")

    @property
    def display_label(self) -> str:
        nib_label = self.nib.display_label if self.nib else "Feder"
        pen_label = f"{self.pen.brand} {self.pen.model}" if self.pen else "Füller"
        if self.setup_label:
            return self.setup_label
        return f"{nib_label} in {pen_label}"

    def __repr__(self):
        return f"<PenNibSetup {self.display_label}>"


# ---------------------------------------------------------------------------
# Tinte
# ---------------------------------------------------------------------------
class Ink(Base):
    __tablename__ = "inks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))
    color_hex: Mapped[Optional[str]] = mapped_column(String(7))   # #RRGGBB
    color_family: Mapped[Optional[str]] = mapped_column(String(50))

    bottle_size_ml: Mapped[Optional[float]] = mapped_column(Float)
    purchase_price: Mapped[Optional[float]] = mapped_column(Float)
    purchase_currency: Mapped[Optional[str]] = mapped_column(String(3))
    purchase_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    remaining_ml: Mapped[Optional[float]] = mapped_column(Float)
    reorder_threshold_ml: Mapped[Optional[float]] = mapped_column(Float)
    reorder_url: Mapped[Optional[str]] = mapped_column(String(1000))
    reorder_note: Mapped[Optional[str]] = mapped_column(Text)
    is_empty: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    # Erweiterte Tinten-Charakteristik für Rotation/Regeln
    color_type: Mapped[Optional[str]] = mapped_column(String(100))
    sheen_level: Mapped[int] = mapped_column(Integer, default=0)
    sheen_color: Mapped[Optional[str]] = mapped_column(String(50))
    feathering_level: Mapped[int] = mapped_column(Integer, default=2)
    shading_level: Mapped[int] = mapped_column(Integer, default=3)
    flow_level: Mapped[int] = mapped_column(Integer, default=3)
    saturation_level: Mapped[int] = mapped_column(Integer, default=3)
    character_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Eigenschaften
    has_shading: Mapped[bool] = mapped_column(Boolean, default=False)
    has_sheen: Mapped[bool] = mapped_column(Boolean, default=False)
    has_shimmer: Mapped[bool] = mapped_column(Boolean, default=False)
    is_pigment: Mapped[bool] = mapped_column(Boolean, default=False)
    is_waterproof: Mapped[bool] = mapped_column(Boolean, default=False)

    wetness_level: Mapped[int] = mapped_column(Integer, default=3)    # 1=trocken … 5=sehr nass
    cleaning_effort: Mapped[int] = mapped_column(Integer, default=3)  # 1=einfach … 5=sehr aufwändig

    max_days_in_pen: Mapped[Optional[int]] = mapped_column(Integer)   # Safety Timer

    # Kommagetrennte Einsatz-/Themen-Tags für Rotationslogik
    # z.B. edc,business,journal,creative,fine_nib,cheap_paper,sheen_showcase
    usage_tags: Mapped[Optional[str]] = mapped_column(Text)

    notes: Mapped[Optional[str]] = mapped_column(Text)
    image_path: Mapped[Optional[str]] = mapped_column(String(500))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    ink_loads: Mapped[List["InkLoad"]] = relationship("InkLoad", back_populates="ink")
    writing_samples: Mapped[List["WritingSample"]] = relationship(
        "WritingSample", back_populates="ink", cascade="all, delete-orphan"
    )
    cleaning_logs: Mapped[List["CleaningLog"]] = relationship(
        "CleaningLog", back_populates="ink", cascade="all, delete-orphan"
    )
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="ink", cascade="all, delete-orphan"
    )

    @property
    def usage_tags_list(self) -> List[str]:
        if not self.usage_tags:
            return []
        return [t.strip() for t in self.usage_tags.split(",") if t.strip()]

    def __repr__(self):
        return f"<Ink {self.brand} {self.name}>"


# ---------------------------------------------------------------------------
# Tintenfüllung (Protokoll welcher Füller welche Tinte enthält)
# ---------------------------------------------------------------------------
class InkLoad(Base):
    __tablename__ = "ink_loads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pen_id: Mapped[int] = mapped_column(Integer, ForeignKey("pens.id"))
    ink_id: Mapped[int] = mapped_column(Integer, ForeignKey("inks.id"))

    loaded_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    cleaned_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    notes: Mapped[Optional[str]] = mapped_column(Text)
    override_reasons: Mapped[Optional[str]] = mapped_column(Text)
    volume_ml: Mapped[Optional[float]] = mapped_column(Float)
    is_fixed_pairing: Mapped[bool] = mapped_column(Boolean, default=False)

    pen: Mapped["Pen"] = relationship("Pen", back_populates="ink_loads")
    ink: Mapped["Ink"] = relationship("Ink", back_populates="ink_loads")

    @property
    def days_loaded(self) -> int:
        """Volle Kalendertage seit Befüllung/Reinigung.

        Bewusst auf ganze Tage gerundet: Der Safety-Timer springt erst nach
        Ablauf von 24 Stunden weiter und nicht stundenweise.
        """
        end = self.cleaned_date or datetime.now()
        return max(0, (end - self.loaded_date).days)

    @property
    def is_active(self) -> bool:
        return self.cleaned_date is None


# ---------------------------------------------------------------------------
# Schreibprobe / Testseite
# ---------------------------------------------------------------------------
class WritingSample(Base):
    """Scrivener-artige Schreibprobe: Text, Bild und Messwerte einer realen Kombination.

    Eine Probe kann an Füller, Tinte, Papier und optional Feder hängen. Damit wird
    nicht nur Inventar verwaltet, sondern echte Alltagserfahrung nachvollziehbar.
    """
    __tablename__ = "writing_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    sample_type: Mapped[str] = mapped_column(String(40), default="regular")

    pen_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("pens.id"))
    ink_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("inks.id"))
    paper_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("papers.id"))
    nib_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("nibs.id"))

    written_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    sample_text: Mapped[Optional[str]] = mapped_column(Text)
    image_path: Mapped[Optional[str]] = mapped_column(String(1000))

    line_width_mm: Mapped[Optional[float]] = mapped_column(Float)
    dry_time_seconds: Mapped[Optional[float]] = mapped_column(Float)
    feathering_level: Mapped[int] = mapped_column(Integer, default=1)
    bleedthrough_level: Mapped[int] = mapped_column(Integer, default=1)
    shading_level: Mapped[int] = mapped_column(Integer, default=3)
    sheen_level: Mapped[int] = mapped_column(Integer, default=0)
    flow_level: Mapped[int] = mapped_column(Integer, default=3)
    feedback_level: Mapped[int] = mapped_column(Integer, default=3)
    overall_rating: Mapped[int] = mapped_column(Integer, default=3)

    tags: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    pen: Mapped[Optional["Pen"]] = relationship("Pen", back_populates="writing_samples")
    ink: Mapped[Optional["Ink"]] = relationship("Ink", back_populates="writing_samples")
    paper: Mapped[Optional["Paper"]] = relationship("Paper", back_populates="writing_samples")
    nib: Mapped[Optional["Nib"]] = relationship("Nib")

    @property
    def tags_list(self) -> List[str]:
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    def __repr__(self):
        return f"<WritingSample {self.title}>"


# ---------------------------------------------------------------------------
# Reinigungsprotokoll
# ---------------------------------------------------------------------------
class CleaningLog(Base):
    """Optionales Reinigungsprotokoll für Enthusiasten.

    InkLoad.cleaned_date bleibt als einfacher Status erhalten. Dieses Protokoll
    ergänzt Details wie Aufwand, Spülgänge und Reiniger, ohne die normale
    Nutzung zu erzwingen.
    """
    __tablename__ = "cleaning_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pen_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("pens.id"))
    ink_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("inks.id"))
    cleaned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    duration_minutes: Mapped[Optional[float]] = mapped_column(Float)
    difficulty_level: Mapped[int] = mapped_column(Integer, default=3)
    flush_cycles: Mapped[Optional[int]] = mapped_column(Integer)
    cleaner_used: Mapped[Optional[str]] = mapped_column(String(120))
    result: Mapped[Optional[str]] = mapped_column(String(50))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    pen: Mapped[Optional["Pen"]] = relationship("Pen", back_populates="cleaning_logs")
    ink: Mapped[Optional["Ink"]] = relationship("Ink", back_populates="cleaning_logs")

    def __repr__(self):
        return f"<CleaningLog pen={self.pen_id} ink={self.ink_id}>"


# ---------------------------------------------------------------------------
# Papier
# ---------------------------------------------------------------------------
class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    brand: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))
    paper_type: Mapped[str] = mapped_column(String(50), default="notebook")

    weight_gsm: Mapped[Optional[int]] = mapped_column(Integer)
    surface: Mapped[Optional[str]] = mapped_column(String(50))

    shading_suitable: Mapped[bool] = mapped_column(Boolean, default=True)
    sheen_suitable: Mapped[bool] = mapped_column(Boolean, default=False)
    feathering_level: Mapped[int] = mapped_column(Integer, default=2)     # 1–5
    bleedthrough_level: Mapped[int] = mapped_column(Integer, default=2)   # 1–5

    is_edc: Mapped[bool] = mapped_column(Boolean, default=False)

    purchase_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    purchase_price: Mapped[Optional[float]] = mapped_column(Float)
    purchase_currency: Mapped[Optional[str]] = mapped_column(String(3))
    pages_total: Mapped[Optional[int]] = mapped_column(Integer)
    pages_used: Mapped[int] = mapped_column(Integer, default=0)

    notes: Mapped[Optional[str]] = mapped_column(Text)
    image_path: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    writing_samples: Mapped[List["WritingSample"]] = relationship(
        "WritingSample", back_populates="paper", cascade="all, delete-orphan"
    )
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="paper", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Paper {self.brand} {self.name}>"


# ---------------------------------------------------------------------------
# Ausgaben
# ---------------------------------------------------------------------------
class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_type: Mapped[str] = mapped_column(String(20))  # pen / ink / nib / paper / accessory / service / other

    pen_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("pens.id"))
    ink_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("inks.id"))
    nib_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("nibs.id"))
    paper_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("papers.id"))

    amount: Mapped[float] = mapped_column(Float)
    shipping: Mapped[float] = mapped_column(Float, default=0.0)
    customs: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="CHF")

    purchase_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    description: Mapped[Optional[str]] = mapped_column(String(200))
    vendor: Mapped[Optional[str]] = mapped_column(String(150))
    order_number: Mapped[Optional[str]] = mapped_column(String(100))
    payment_method: Mapped[Optional[str]] = mapped_column(String(80))
    warranty_until: Mapped[Optional[datetime]] = mapped_column(DateTime)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    pen: Mapped[Optional["Pen"]] = relationship("Pen", back_populates="expenses")
    ink: Mapped[Optional["Ink"]] = relationship("Ink", back_populates="expenses")
    nib: Mapped[Optional["Nib"]] = relationship("Nib", back_populates="expenses")
    paper: Mapped[Optional["Paper"]] = relationship("Paper", back_populates="expenses")

    @property
    def total(self) -> float:
        return (self.amount or 0.0) + (self.shipping or 0.0) + (self.customs or 0.0)

    @property
    def linked_label(self) -> str:
        if self.pen:
            return f"{self.pen.brand} {self.pen.model}"
        if self.ink:
            return f"{self.ink.brand} {self.ink.name}"
        if self.nib:
            return f"{self.nib.manufacturer or ''} {self.nib.size or ''}".strip()
        if self.paper:
            return f"{self.paper.brand} {self.paper.name}"
        return ""


# ---------------------------------------------------------------------------
# Regeln (Regel-Engine)
# ---------------------------------------------------------------------------
class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)

    rule_type: Mapped[str] = mapped_column(String(20), default="soft")    # hard / soft / preference / context
    warn_level: Mapped[str] = mapped_column(String(20), default="warning") # info / warning / critical / blocked
    rule_group: Mapped[str] = mapped_column(String(50), default="rotation") # safety / maintenance / rotation / pen / ink / nib / paper / collector
    score_delta: Mapped[Optional[int]] = mapped_column(Integer)
    auto_action: Mapped[str] = mapped_column(String(30), default="warn") # allow / warn / reject / require_override

    condition_type: Mapped[str] = mapped_column(String(50))
    condition_data: Mapped[Optional[str]] = mapped_column(Text)  # JSON

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    overrides: Mapped[List["OverrideLog"]] = relationship("OverrideLog", back_populates="rule")


# ---------------------------------------------------------------------------
# Override-Log
# ---------------------------------------------------------------------------
class OverrideLog(Base):
    __tablename__ = "override_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[int] = mapped_column(Integer, ForeignKey("rules.id"))
    pen_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("pens.id"))
    ink_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("inks.id"))

    override_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    decision_mode: Mapped[str] = mapped_column(String(30), default="manual")  # manual / full_auto
    action: Mapped[Optional[str]] = mapped_column(String(50))
    score_snapshot: Mapped[Optional[int]] = mapped_column(Integer)
    explanation: Mapped[Optional[str]] = mapped_column(Text)

    rule: Mapped["Rule"] = relationship("Rule", back_populates="overrides")



# ---------------------------------------------------------------------------
# Wishlist / generische Artikelkarte
# ---------------------------------------------------------------------------
class WishlistItem(Base):
    __tablename__ = "wishlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_type: Mapped[str] = mapped_column(String(30), default="pen")  # pen / ink / nib / paper / accessory / service
    title: Mapped[str] = mapped_column(String(200))
    brand: Mapped[Optional[str]] = mapped_column(String(100))
    model: Mapped[Optional[str]] = mapped_column(String(150))
    variant: Mapped[Optional[str]] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(30), default="wish")  # wish / watching / ordered / bought / rejected
    priority: Mapped[int] = mapped_column(Integer, default=3)

    desired_price: Mapped[Optional[float]] = mapped_column(Float)
    expected_price: Mapped[Optional[float]] = mapped_column(Float)
    actual_price: Mapped[Optional[float]] = mapped_column(Float)
    currency: Mapped[Optional[str]] = mapped_column(String(3))
    shipping: Mapped[Optional[float]] = mapped_column(Float)
    customs: Mapped[Optional[float]] = mapped_column(Float)

    shop: Mapped[Optional[str]] = mapped_column(String(150))
    url: Mapped[Optional[str]] = mapped_column(String(1000))
    reason: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    article_card_path: Mapped[Optional[str]] = mapped_column(String(1000))
    bought_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_object_type: Mapped[Optional[str]] = mapped_column(String(30))
    created_object_id: Mapped[Optional[int]] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<WishlistItem {self.item_type} {self.title}>"


# ---------------------------------------------------------------------------
# App-Einstellungen (Key-Value)
# ---------------------------------------------------------------------------
class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[Optional[str]] = mapped_column(Text)

    @classmethod
    def get(cls, session, key: str, default: str = None) -> Optional[str]:
        row = session.query(cls).filter_by(key=key).first()
        return row.value if row else default

    @classmethod
    def set(cls, session, key: str, value: str):
        row = session.query(cls).filter_by(key=key).first()
        if row:
            row.value = value
        else:
            session.add(cls(key=key, value=value))
        session.commit()
