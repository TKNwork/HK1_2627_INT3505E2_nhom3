import os
import random
from locust import HttpUser, between, task

SAMPLE_CASES = [
    ("Ngày mai 9h họp nhóm SOA trong 90 phút",
     {"startAt": "2026-11-18T09:00:00+07:00", "durationMinutes": 90}),
    ("Thứ sáu 14h nộp báo cáo tuần 8, xong trước 17h",
     {"startAt": "2026-11-20T14:00:00+07:00", "deadlineAt": "2026-11-20T17:00:00+07:00"}),
    ("Tối nay ôn tập kiến trúc hướng dịch vụ 2 tiếng",
     {"date": "2026-11-17", "startAt": None, "durationMinutes": 120}),
    ("Sáng thứ hai 8h30 trao đổi tiến độ đồ án",
     {"startAt": "2026-11-23T08:30:00+07:00"}),
]


class AIServiceUser(HttpUser):
    host = "http://127.0.0.1:8001"
    wait_time = between(0.5, 1.5)

    def on_start(self):
        self.headers = {
            "Content-Type": "application/json",
            "X-Internal-Api-Key": os.environ.get("INTERNAL_API_KEY") or "local_dev_internal_api_key_1234567890",
        }

    @task(4)
    def extract_vietnamese_task(self):
        source, expected = random.choice(SAMPLE_CASES)
        payload = {
            "sourceText": source,
            "timezone": "Asia/Ho_Chi_Minh",
            "now": "2026-11-17T08:00:00+07:00",
        }
        with self.client.post(
            "/internal/v1/extractions",
            json=payload,
            headers=self.headers,
            name="POST /internal/v1/extractions",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                return
            try:
                fields = response.json()["data"]["fields"]
                if any(fields[key] != value for key, value in expected.items()):
                    response.failure("Unexpected extraction fields")
            except (KeyError, TypeError, ValueError):
                response.failure("Invalid extraction envelope")

    @task(1)
    def health_check(self):
        self.client.get("/health", name="GET /health")
