"""The application's own state.

Columns mirror the pipeline's fields, not the mockups' display strings (spec
5.1a seam 4). Evidence text, benchmark rates, confidence bands and
needs_human_review are stored even where no screen shows them, nullable, so a
real pipeline run populates them without a migration.

Money is stored as integer rupees. No column ever holds a formatted string.
"""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Contractor(Base):
    __tablename__ = "contractors"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    sites: Mapped[int] = mapped_column(Integer, default=0)
    flags_per_boq: Mapped[float | None] = mapped_column(Float, nullable=True)
    underspecified_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    overrun_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    sites_gone_quiet: Mapped[int] = mapped_column(Integer, default=0)
    tier: Mapped[str] = mapped_column(String(16), default="RELIABLE")

    loans: Mapped[list["Loan"]] = relationship(back_populates="contractor")


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    borrower_name: Mapped[str] = mapped_column(String(120))
    locality: Mapped[str] = mapped_column(String(80))
    plot_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    built_up_sqft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sanctioned: Mapped[int] = mapped_column(Integer)
    disbursed: Mapped[int] = mapped_column(Integer, default=0)
    contractor_id: Mapped[str | None] = mapped_column(ForeignKey("contractors.id"), nullable=True)

    # Denormalised risk snapshot — the portfolio table's columns. Sourced from
    # the mockups in this build; from risk_assessment when the pipeline lands.
    paid_up_to: Mapped[str | None] = mapped_column(String(40), nullable=True)
    seen_on_site: Mapped[str | None] = mapped_column(String(40), nullable=True)
    behind_schedule: Mapped[bool] = mapped_column(Boolean, default=False)
    exposure_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    exposure_undefined: Mapped[bool] = mapped_column(Boolean, default=False)
    cost_to_complete_gap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Preserves the design's exposure-descending order without recomputing it.
    hotlist_rank: Mapped[int] = mapped_column(Integer, default=0)

    contractor: Mapped[Contractor | None] = relationship(back_populates="loans")
    revisions: Mapped[list["BoqRevision"]] = relationship(
        back_populates="loan", cascade="all, delete-orphan", order_by="BoqRevision.rev"
    )
    tranches: Mapped[list["Tranche"]] = relationship(
        back_populates="loan", cascade="all, delete-orphan", order_by="Tranche.number"
    )
    questions: Mapped[list["Question"]] = relationship(
        back_populates="loan", cascade="all, delete-orphan", order_by="Question.number"
    )
    change_orders: Mapped[list["ChangeOrder"]] = relationship(
        back_populates="loan", cascade="all, delete-orphan"
    )


class BoqRevision(Base):
    __tablename__ = "boq_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"))
    rev: Mapped[int] = mapped_column(Integer, default=1)
    received_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_filename: Mapped[str | None] = mapped_column(String(200), nullable=True)
    boq_total: Mapped[int] = mapped_column(Integer)
    payment_pct_before_slab: Mapped[float] = mapped_column(Float)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    # Pipeline provenance, unused by any screen. Stored so a live run has a home.
    pipeline_mode: Mapped[str] = mapped_column(String(16), default="fixture")
    raw_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_artifact: Mapped[str | None] = mapped_column(Text, nullable=True)

    loan: Mapped[Loan] = relationship(back_populates="revisions")
    line_items: Mapped[list["LineItem"]] = relationship(
        back_populates="revision", cascade="all, delete-orphan"
    )
    flags: Mapped[list["Flag"]] = relationship(
        back_populates="revision", cascade="all, delete-orphan"
    )
    questions: Mapped[list["Question"]] = relationship(back_populates="revision")


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey("boq_revisions.id"))
    item_id: Mapped[str] = mapped_column(String(16))
    section: Mapped[str | None] = mapped_column(String(80), nullable=True)
    desc: Mapped[str] = mapped_column(Text)
    qty: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(16))
    rate: Mapped[float] = mapped_column(Float)
    amount: Mapped[float] = mapped_column(Float)

    revision: Mapped[BoqRevision] = relationship(back_populates="line_items")


class Flag(Base):
    __tablename__ = "flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey("boq_revisions.id"))
    item: Mapped[str] = mapped_column(String(16))
    type: Mapped[str] = mapped_column(String(32))
    label: Mapped[str] = mapped_column(String(40))
    tone: Mapped[str] = mapped_column(String(16), default="danger")
    group_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    evidence: Mapped[str] = mapped_column(Text)
    question: Mapped[str] = mapped_column(Text)
    benchmark_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    deviation_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_qty: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    expected_amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    revision: Mapped[BoqRevision] = relationship(back_populates="flags")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"))
    revision_id: Mapped[int | None] = mapped_column(ForeignKey("boq_revisions.id"), nullable=True)
    number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft|sent|replied
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reply: Mapped[str | None] = mapped_column(Text, nullable=True)

    loan: Mapped[Loan] = relationship(back_populates="questions")
    revision: Mapped[BoqRevision | None] = relationship(back_populates="questions")


class Tranche(Base):
    __tablename__ = "tranches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"))
    number: Mapped[int] = mapped_column(Integer)
    milestone: Mapped[str] = mapped_column(String(32))
    planned_cum_pct: Mapped[float] = mapped_column(Float)
    disbursed_cum: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="upcoming")  # paid|on_hold|upcoming
    inspection_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    observed_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    claimed_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    assessment_revision_id: Mapped[int | None] = mapped_column(ForeignKey("boq_revisions.id"), nullable=True)

    # Pipeline fields. Not all are shown; all are stored.
    verified_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exposure_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    exposure_undefined: Mapped[bool] = mapped_column(Boolean, default=False)
    cost_to_complete: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_to_complete_gap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(16), nullable=True)
    needs_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    recommendation: Mapped[str | None] = mapped_column(String(16), nullable=True)
    owner_view: Mapped[str | None] = mapped_column(Text, nullable=True)
    officer_view: Mapped[str | None] = mapped_column(Text, nullable=True)

    loan: Mapped[Loan] = relationship(back_populates="tranches")
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="tranche", cascade="all, delete-orphan"
    )
    decision: Mapped["Decision | None"] = relationship(
        back_populates="tranche", cascade="all, delete-orphan", uselist=False
    )


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tranche_id: Mapped[int] = mapped_column(ForeignKey("tranches.id"))
    slot_key: Mapped[str] = mapped_column(String(40))
    caption: Mapped[str | None] = mapped_column(String(200), nullable=True)
    stored_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    geotag_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    timestamp_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    same_angle: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    taken_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    tranche: Mapped[Tranche] = relationship(back_populates="photos")


class ChangeOrder(Base):
    __tablename__ = "change_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loan_id: Mapped[str] = mapped_column(ForeignKey("loans.id"))
    title: Mapped[str] = mapped_column(String(200))
    signed_desc: Mapped[str] = mapped_column(Text)
    signed_amount: Mapped[int] = mapped_column(Integer)
    proposed_desc: Mapped[str] = mapped_column(Text)
    proposed_amount: Mapped[int] = mapped_column(Integer)
    neevs_read: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    tone: Mapped[str] = mapped_column(String(16), default="warn")

    loan: Mapped[Loan] = relationship(back_populates="change_orders")


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tranche_id: Mapped[int] = mapped_column(ForeignKey("tranches.id"), unique=True)
    action: Mapped[str] = mapped_column(String(16))  # RELEASE|HOLD|ESCALATE
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[str] = mapped_column(String(80), default="credit officer")
    decided_at: Mapped[datetime] = mapped_column(DateTime)
    # The full evidence trail the designs promise gets written to the loan file.
    evidence_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    tranche: Mapped[Tranche] = relationship(back_populates="decision")


class DecisionEvent(Base):
    """Append-only audit trail. Decision remains the latest-state projection."""
    __tablename__ = "decision_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tranche_id: Mapped[int] = mapped_column(ForeignKey("tranches.id"))
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True)
    action: Mapped[str] = mapped_column(String(16))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[str] = mapped_column(String(120))
    decided_at: Mapped[datetime] = mapped_column(DateTime)
    evidence_snapshot: Mapped[str] = mapped_column(Text)
