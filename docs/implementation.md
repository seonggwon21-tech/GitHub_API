# 주요 구현

> GitHub REST API QA 자동화의 설계 의도와 코드 레벨 상세입니다.
> 메인 개요는 [README](../README.md) 참고.

---

## 1. GitHubAPIClient — HTTP 호출 추상화 + Allure 자동 기록

테스트 코드는 `client.get("/users/{username}")`만 호출하면 되고, **URL · Status Code · Response Body가 리포트에 자동 첨부**됩니다. `requests.Session`을 재사용하므로 인증 헤더는 한 번만 세팅하면 이후 모든 요청에 자동 포함됩니다.

```python
def get(self, endpoint: str, params: dict = None) -> requests.Response:
    url = f"{self.base_url}{endpoint}"
    with allure.step(f"GET {url}"):
        response = self.session.get(url, params=params)
        self._attach(response)   # Status Code + Response Body 자동 첨부
    return response
```

> `_attach()`는 응답 `Content-Type`을 보고 JSON일 때만 JSON으로, 에러 HTML·rate-limit 페이지·빈 응답은 텍스트로 첨부해 Allure가 파싱에 실패하지 않게 했습니다.

---

## 2. session-scope fixture — 연결 재사용 + 실계정 레포 자동 탐지

`public_repo` fixture가 테스트 계정의 공개 레포를 **API로 직접 조회**해 오므로 레포명을 하드코딩하지 않아도 어떤 계정에서든 동작합니다. 단순히 첫 레포를 고르면 그 레포의 Issues가 비활성/fork일 때 `GET .../issues`가 `410`을 내 false-fail이 날 수 있어, **`has_issues=true`인 레포를 우선 선택**합니다(없으면 첫 레포로 폴백). `client`·`username`·`public_repo` 세 fixture 모두 `session` scope라 HTTP 세션은 전체 실행에서 **1개만** 생성됩니다.

```python
@pytest.fixture(scope="session")
def public_repo(client, username) -> str:
    response = client.get(f"/users/{username}/repos", params={"type": "owner", "per_page": 100})
    if response.status_code != 200:
        pytest.skip(f"Could not fetch repos ({response.status_code}): {response.json().get('message')}")
    repos = response.json()
    if not repos:
        pytest.skip("No public repositories found for this account.")
    with_issues = next((r for r in repos if r.get("has_issues")), None)
    return (with_issues or repos[0])["name"]
```

---

## 3. negative 케이스 — 404 · 422 · 인증 스코프

정상 동작만큼 **비정상 입력의 응답이 올바른지**가 API 품질의 일부입니다. 특히 `/user/emails`는 PAT에 `user:email` 스코프가 없으면 `401`도 `403`도 아닌 **`404`** 를 반환한다는 것을 직접 마주쳐, 허용 코드에 추가하고 *이유를 주석으로* 남겼습니다.

```python
def test_list_public_emails_requires_auth(self, client):
    response = client.get("/user/emails")
    # 200: authed with user:email scope, 401/403: no token, 404: token lacks user:email scope
    assert response.status_code in (200, 401, 403, 404)
```

---

## 4. GitHub Actions CI + Allure Pages 자동 배포

`main` push·PR마다 `test` job이 테스트를 실행하고, `report` job이 Allure 리포트를 생성해 **GitHub Pages에 배포**합니다. `gh-pages`의 history를 복사해 trend가 누적되므로 빌드마다 과거 결과와 비교됩니다. **테스트가 실패해도 리포트는 배포**합니다 — 실패했을 때야말로 리포트가 가장 필요하기 때문입니다.

```
push to main
 ├── test   : pytest → allure-results → upload artifact
 └── report : download → allure generate (+ history 누적) → deploy to gh-pages
```

> PAT는 `GH_API_TOKEN`으로 GitHub Secrets에 등록해 주입합니다. 워크플로 내장 `GITHUB_TOKEN`과의 이름 충돌을 피하기 위해 별도 이름을 사용합니다.

---

## 5. write-path CRUD — 샌드박스 격리 + teardown 정리

read-only 검증만으로는 "API가 쓰기까지 올바르게 동작한다"를 말할 수 없어, 이슈·라벨을 **실제로 생성·수정·삭제**하는 write-path 테스트를 추가했습니다. 핵심은 **실데이터를 건드리되 흔적을 남기지 않는 것**입니다.

- **전용 샌드박스 레포 격리** — 모든 쓰기는 `write_repo` fixture가 보장하는 전용 sandbox 레포에서만 일어납니다. 레포가 없으면 setup에서 **자동 생성**(private), 포트폴리오 레포는 손대지 않습니다.
- **`yield` setup/teardown으로 정리** — fixture가 setup에서 자원을 만들고 `yield` 뒤에서 정리합니다. GitHub은 **이슈를 REST로 hard-delete 할 수 없어** 생성한 이슈는 `state:closed`로 닫고, 라벨·코멘트는 `DELETE`(204)로 실제 삭제합니다.
- **토큰 없으면 전체 skip** — `repo` 스코프 PAT가 없거나 push 권한이 없으면 fixture가 `pytest.skip()`으로 write 스위트 전체를 건너뛰어, 토큰 없는 환경(CI 포함)에서도 read-only 테스트는 그대로 통과합니다.

```python
@pytest.fixture
def new_issue(client, username, write_repo):
    response = client.post(f"/repos/{username}/{write_repo}/issues",
                           payload={"title": ..., "body": ...})
    yield response                                  # ← 테스트 실행
    # 이슈는 REST hard-delete가 없으므로 close로 정리 (idempotent)
    if response.status_code == 201:
        number = response.json()["number"]
        client.patch(f"/repos/{username}/{write_repo}/issues/{number}",
                     payload={"state": "closed"})
```

> 라벨을 full-CRUD 자원으로 고른 이유: 이슈와 달리 **생성→수정→삭제(204)** 가 모두 REST로 가능해 "정리까지 깔끔한" CRUD 사이클을 그대로 시연할 수 있기 때문입니다.
