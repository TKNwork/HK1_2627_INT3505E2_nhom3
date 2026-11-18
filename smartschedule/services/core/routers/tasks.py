from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Query, Request, Response
from ..schemas.base import Envelope
from ..schemas.tasks import CreateTask, ExpectedVersion, PatchTask, TaskData, TaskListData
from ..services.fixtures import stub_task
from ..utils.auth import get_current_user
from ..utils.response import success
from ..database import get_async_db
from ..clients.scheduling_client import SchedulingClient
from ..services.task_creation import create_manual_task
from ..utils.auth import CurrentUser
from ..utils.request_id import get_request_id
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix='/api/v1/tasks', tags=['Tasks'], dependencies=[Depends(get_current_user)])


@router.post(
    "",
    status_code=201,
    response_model=Envelope[TaskData],
    operation_id="API-03",
)
async def create_task(
    body: CreateTask,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_db)],
) -> dict:

    scheduling_client = SchedulingClient(
        request.app.state.settings
    )

    task = await create_manual_task(
        body=body,
        user_id=user.id,
        session=session,
        scheduling_client=scheduling_client,
        request_id=get_request_id(request),
    )

    return success(request, TaskData(task=task))

@router.get('', response_model=Envelope[TaskListData], operation_id='API-04')
def list_tasks(request: Request, status: Literal['pending', 'completed'] | None = None,
               scheduled: bool | None = None, limit: Annotated[int, Query(ge=1, le=100)] = 20,
               cursor: str | None = None) -> dict:
    """UC-04: danh sách cá nhân với cursor (stub)."""
    # TODO: logic thật theo UC-04: ownership, bộ lọc và cursor ổn định.
    return success(request, TaskListData(items=[stub_task()], next_cursor=None))


@router.get('/{id}', response_model=Envelope[TaskData], operation_id='API-05')
def get_task(id: str, request: Request) -> dict:
    """UC-05: chi tiết công việc (stub)."""
    # TODO: logic thật theo UC-05: không tồn tại/không thuộc user trả TASK_NOT_FOUND.
    return success(request, TaskData(task=stub_task(id)))


@router.patch('/{id}', response_model=Envelope[TaskData], operation_id='API-06')
def patch_task(id: str, body: PatchTask, request: Request) -> dict:
    """UC-06, UC-17: sửa task (stub)."""
    # TODO: logic thật theo UC-06/17: version, pending, kiểm lịch, task+outbox atomic.
    return success(request, TaskData(task=stub_task(id, version=2)))


@router.delete('/{id}', status_code=204, response_class=Response, operation_id='API-07')
def delete_task(id: str, expected_version: Annotated[int, Query(alias='expectedVersion', ge=1)]) -> Response:
    """UC-07: xóa (stub); 204 không body theo ngoại lệ đã duyệt."""
    # TODO: logic thật theo UC-07: quyền/version, xóa và outbox cancel cùng transaction.
    return Response(status_code=204)


@router.post('/{id}/complete', response_model=Envelope[TaskData], operation_id='API-08')
def complete_task(id: str, body: ExpectedVersion, request: Request) -> dict:
    """UC-08: hoàn thành (stub)."""
    # TODO: logic thật theo UC-08: TASK_ALREADY_COMPLETED, version và cancel job.
    return success(request, TaskData(task=stub_task(id, version=2, completed=True)))