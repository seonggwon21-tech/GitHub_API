import allure
import requests

from config.settings import BASE_URL, HEADERS

# (connect, read) timeout in seconds. Without this, a stalled connection to
# api.github.com would hang the whole suite (and CI) indefinitely.
DEFAULT_TIMEOUT = (5, 30)


class GitHubAPIClient:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    @staticmethod
    def _attach(response: requests.Response) -> None:
        allure.attach(
            str(response.status_code),
            name="Status Code",
            attachment_type=allure.attachment_type.TEXT,
        )
        if not response.content:
            return
        # Only render as JSON when the server actually sent JSON; otherwise
        # (error HTML, rate-limit pages, empty bodies) attach as plain text so
        # Allure does not choke trying to parse it.
        content_type = response.headers.get("Content-Type", "")
        attachment_type = allure.attachment_type.JSON if "json" in content_type.lower() else allure.attachment_type.TEXT
        allure.attach(response.text, name="Response Body", attachment_type=attachment_type)

    def get(self, endpoint: str, params: dict = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        with allure.step(f"GET {url}"):
            response = self.session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            self._attach(response)
        return response

    def post(self, endpoint: str, payload: dict = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        with allure.step(f"POST {url}"):
            response = self.session.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
            self._attach(response)
        return response

    def patch(self, endpoint: str, payload: dict = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        with allure.step(f"PATCH {url}"):
            response = self.session.patch(url, json=payload, timeout=DEFAULT_TIMEOUT)
            self._attach(response)
        return response

    def put(self, endpoint: str, payload: dict = None) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        with allure.step(f"PUT {url}"):
            response = self.session.put(url, json=payload, timeout=DEFAULT_TIMEOUT)
            self._attach(response)
        return response

    def delete(self, endpoint: str) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        with allure.step(f"DELETE {url}"):
            response = self.session.delete(url, timeout=DEFAULT_TIMEOUT)
            self._attach(response)
        return response
