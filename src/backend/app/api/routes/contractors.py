"""Contractor Scorecard — a credit signal on builders rather than borrowers."""

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DbSession
from app.db import models
from app.mappers.contractor import to_contractor_scorecard
from app.schemas.views import ContractorScorecardView

router = APIRouter(prefix="/api", tags=["contractors"])


@router.get("/contractors", response_model=ContractorScorecardView)
def contractors(db: DbSession) -> ContractorScorecardView:
    return to_contractor_scorecard(list(db.scalars(select(models.Contractor))))
