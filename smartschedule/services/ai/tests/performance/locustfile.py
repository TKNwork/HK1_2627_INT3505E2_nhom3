import random
from locust import HttpUser, between, task

SAMPLE_PROMPTS = [
    "Ngay mai 9h hop nhom SOA trong 90 phut",
    "Thu sau 14h nop bao cao tuan 8, xong truoc 17h",
    "Toi nay on tap kien truc huong dich vu 2 tieng",
    "Sang thu hai 8h30 trao doi tien do do an",
]


class AIServiceUser(HttpUser):
    host = "http://127.0.0.1:8001"
    wait_time = between(0.5, 1.5)

    def on_start(self):
        self.headers = {
            "Content-Type": "application/json",
            "X-Internal-Api-Key": "local_dev_internal_api_key_1234567890",
        }

    @task(4)
    def extract_vietnamese_task(self):
        payload = {
            "source_text": random.choice(SAMPLE_PROMPTS),
            "timezone": "Asia/Ho_Chi_Minh",
            "now": "2026-11-17T08:00:00+07:00",
        }
        self.client.post(
            "/internal/v1/extractions",
            json=payload,
            headers=self.headers,
            name="POST /internal/v1/extractions",
        )

    @task(1)
    def health_check(self):
        self.client.get("/health", name="GET /health")
