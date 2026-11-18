from fastapi import APIRouter, Depends, Request

from ..schemas.base import Envelope
from ..schemas.scheduling import ConflictRequest, ConflictData
from ..services.conflict_service import find_conflicts
from ..utils.internal_auth import require_internal_key
from ..utils.response import success


router = APIRouter(
    prefix="/internal/v1",
    tags=["Scheduling"],
    dependencies=[Depends(require_internal_key)],
)


@router.post(
    "/conflicts",
    response_model=Envelope[ConflictData],
    operation_id="INT-02",
)
def conflicts(body: ConflictRequest, request: Request) -> dict:
    """INT-02: kiểm tra xung đột lịch cho UC-03."""

    result = find_conflicts(
        candidate=body.candidate,
        busy_slots=body.busy,
    )

    data = ConflictData(
        has_conflict=len(result) > 0,
        conflicts=result,
    )

    return success(request, data)