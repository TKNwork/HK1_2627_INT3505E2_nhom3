"""Gửi HTTP nội bộ và chuẩn hóa lỗi giao tiếp giữa các service."""
from typing import Any
import httpx
from ..utils.errors import AppError


class InternalClient:
    """Client dùng chung cho các service nội bộ, có timeout và transport thay thế khi test."""
    def __init__(self, base_url: str, api_key: str, timeout: float,
                 unavailable_code: str, timeout_code: str | None = None,
                 invalid_code: str | None = None, transport: httpx.AsyncBaseTransport | None = None,
                 error_statuses: dict[int, str] | None = None) -> None:
        """Lưu cấu hình kết nối, mã lỗi và ánh xạ HTTP riêng mà client con truyền vào."""
        self.base_url, self.api_key, self.timeout = base_url, api_key, timeout
        self.unavailable_code = unavailable_code
        self.timeout_code = timeout_code or unavailable_code
        self.invalid_code = invalid_code or unavailable_code
        self.transport = transport
        self.error_statuses = error_statuses or {}

    async def request(self, method: str, path: str, request_id: str,
                      payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Gửi method/path với payload JSON và trả phần data của envelope.

        request_id được chuyển qua X-Request-Id; khóa nội bộ đi qua X-Internal-Api-Key.
        Lỗi được ánh xạ thành AppError theo cấu hình: response không hợp lệ là 502,
        service không khả dụng thường là 503; timeout AI là 504. Không tự retry.
        Hàm chỉ kiểm envelope, không kiểm schema nghiệp vụ bên trong data."""
        headers = {'X-Internal-Api-Key': self.api_key, 'X-Request-Id': request_id}
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout,
                                             headers=headers, transport=self.transport, trust_env=False) as client:
                response = await client.request(method, path, json=payload)
                if response.status_code in self.error_statuses:
                    raise AppError(self.error_statuses[response.status_code], response.status_code,
                                   'Dịch vụ phụ thuộc không xử lý được yêu cầu.')
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict) or 'requestId' not in data or not isinstance(data.get('data'), dict):
                    raise AppError(self.invalid_code, 502, 'Response service không đúng envelope.')
                return data['data']
        except httpx.TimeoutException as exc:
            raise AppError(self.timeout_code, 504 if self.timeout_code != self.unavailable_code else 503,
                           'Service quá thời gian phản hồi.') from exc
        except httpx.HTTPError as exc:
            raise AppError(self.unavailable_code, 503, 'Service không khả dụng.') from exc
        except (ValueError, TypeError) as exc:
            raise AppError(self.invalid_code, 502, 'Service trả JSON không hợp lệ.') from exc
