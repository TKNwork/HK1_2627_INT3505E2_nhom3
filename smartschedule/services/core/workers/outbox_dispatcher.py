"""UC-19: worker frame only. Never started by the FastAPI application."""


async def run() -> None:
    # TODO: logic thật theo UC-19: claim/lease, retry, crash recovery và ghi kết quả.
    raise NotImplementedError('Worker execution is intentionally disabled in skeleton.')
