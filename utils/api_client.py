import requests
import allure
from config.settings import BASE_URL, HEADERS


class GitHubAPIClient:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def get(self, endpoint: str, params: dict = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        with allure.step(f"GET {url}"):
            response = self.session.get(url, params=params)
            allure.attach(
                str(response.status_code),
                name="Status Code",
                attachment_type=allure.attachment_type.TEXT,
            )
            allure.attach(
                response.text,
                name="Response Body",
                attachment_type=allure.attachment_type.JSON,
            )
        return response

    def post(self, endpoint: str, payload: dict = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        with allure.step(f"POST {url}"):
            response = self.session.post(url, json=payload)
            allure.attach(
                str(response.status_code),
                name="Status Code",
                attachment_type=allure.attachment_type.TEXT,
            )
            allure.attach(
                response.text,
                name="Response Body",
                attachment_type=allure.attachment_type.JSON,
            )
        return response

    def patch(self, endpoint: str, payload: dict = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        with allure.step(f"PATCH {url}"):
            response = self.session.patch(url, json=payload)
            allure.attach(
                str(response.status_code),
                name="Status Code",
                attachment_type=allure.attachment_type.TEXT,
            )
            allure.attach(
                response.text,
                name="Response Body",
                attachment_type=allure.attachment_type.JSON,
            )
        return response

    def delete(self, endpoint: str) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        with allure.step(f"DELETE {url}"):
            response = self.session.delete(url)
            allure.attach(
                str(response.status_code),
                name="Status Code",
                attachment_type=allure.attachment_type.TEXT,
            )
        return response
