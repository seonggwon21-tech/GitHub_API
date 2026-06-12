# GitHub REST API QA Automation

> GitHub REST API(api.github.com)의 User · Repository · Issues · Labels 엔드포인트를 **pytest + requests**로 검증한 REST API 계약(contract) 검증 포트폴리오
> — 총 **50 TC** · READ + **write-path(CRUD) 검증** · setup/teardown 정리 · negative 케이스 포함 · GitHub Actions CI + Allure Pages 자동 배포

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-8.x-0A9EDC?logo=pytest&logoColor=white)
![requests](https://img.shields.io/badge/requests-2.x-FF6B35?logo=python&logoColor=white)
![Allure](https://img.shields.io/badge/Allure-Report-FF6B6B?logo=qameta&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI-2088FF?logo=githubactions&logoColor=white)
[![CI](https://github.com/seonggwon21-tech/GitHub_API/actions/workflows/ci.yml/badge.svg)](https://github.com/seonggwon21-tech/GitHub_API/actions/workflows/ci.yml)

---

## 핵심 성과

| 테스트 | 결과 | 검증 범위 | CI | 리포트 |
|:---:|:---:|:---:|:---:|:---:|
| **50 TC** (User 12·Repos 16·Issues 11·CRUD 11) | **47 passed · 3 skip · 0 fail** | 상태코드·스키마·정합성·**CRUD write-path**·negative | **GitHub Actions** | **Allure Pages** |

**핵심 기능**

- **READ를 넘어선 write-path(CRUD) 검증** — 이슈·라벨을 실제로 **생성(201)·수정(200)·삭제(204)** 하고 응답·read-back으로 정합성을 확인. 전용 **샌드박스 레포**에서만 동작하고, fixture `yield` teardown으로 **생성물을 전부 정리**(이슈 close · 라벨/코멘트 delete)해 데이터를 남기지 않음
- **상태 코드를 넘어선 계약 검증** — `200`만 확인하는 데 그치지 않고 응답 **스키마 필드 존재·데이터 타입·정합성**(`login`/`owner` 일치, repo `private:false` 보장)까지 검증해 "API가 올바르게 동작한다"를 증명
- **negative 케이스로 거부 동작까지** — 존재하지 않는 user/repo/issue의 `404`, 잘못된 파라미터(`state=invalid_state`)의 `422`, **필수값 누락·중복 라벨 생성의 `422`** 까지 명시적으로 검증. 정상 응답만큼 비정상 입력의 응답도 품질의 일부
- **실계정 공개 레포 자동 탐지** — `public_repo` fixture가 테스트 계정의 공개 레포를 API로 동적 조회 → **레포명 하드코딩 0**, 어떤 계정에서도 그대로 동작
- **모든 HTTP 호출 Allure step 자동 기록** — `GitHubAPIClient`가 매 요청을 `allure.step`으로 감싸 URL·Status Code·Response Body를 리포트에 자동 첨부 → 어느 요청에서 무엇이 반환됐는지 추적 가능

> 📊 **Live Allure Report** → https://seonggwon21-tech.github.io/GitHub_API/ *(매 `main` push마다 trend 누적 갱신)*

---

## 기술 스택

| 분류 | 사용 기술 |
|---|---|
| 언어 · 프레임워크 | Python 3.12 · pytest 8 (fixture scope, `yield` setup/teardown, marker 슬라이스 `smoke`/`user`/`repos`/`issues`/`write`) |
| HTTP 클라이언트 | requests (`Session` 재사용 — 헤더·연결 풀 일괄 관리, 인증 헤더 1회 세팅) |
| API 검증 | 상태 코드 · 스키마 필드/타입 · 데이터 정합성 · 페이지네이션 · **CRUD write-path(생성/수정/삭제 + read-back)** · negative(404·422·인증 스코프) |
| 리포팅 | Allure (epic/feature/story/step 4계층 + HTTP 요청별 Status·Body 자동 첨부) |
| CI/CD | GitHub Actions — push·PR마다 테스트 실행 → Allure Report → **GitHub Pages 자동 배포**(trend 누적) |
| 환경 관리 | python-dotenv (`.env`로 PAT·사용자명 분리, `.gitignore` 처리) |
| 보조 도구 | Postman 컬렉션 (`postman/`) — 동일 엔드포인트 수동 탐색·재현용 |

---

## 테스트 구성

| 파일 | 클래스 | TC | 검증 내용 |
|---|---|:---:|---|
| `test_user.py` | `TestPublicUser` | 6 | 공개 프로필 200 · 스키마 · login/type 정합성 · 404 · Content-Type |
| | `TestAuthenticatedUser` | 3 | 인증 유저 200/401 · 스키마 · `/user/emails` 스코프별 응답 |
| | `TestUserFollowers` | 3 | followers/following 200 · list 타입 |
| `test_repos.py` | `TestListRepositories` | 8 | 200 · list · 스키마 · public 보장 · 페이지네이션 · 정렬 · 404 |
| | `TestGetRepository` | 8 | 200 · name/owner 정합성 · 스키마 · 404 · languages/topics/contributors |
| `test_issues.py` | `TestListIssues` | 8 | 200 · list · state 필터(open/closed) · 스키마 · 페이지네이션 · 422 · 404 |
| | `TestGetIssue` | 3 | 단건 200 · 404 · comments 200 |
| `test_issues_crud.py` | `TestIssueLifecycle` | 4 | 이슈 생성 201 · read-back 정합성 · title 수정 200 · close 200 |
| | `TestIssueComment` | 1 | 코멘트 생성 201 → 삭제 204 → 404 |
| | `TestLabelCrud` | 3 | 라벨 생성 201 · 수정 200 · **삭제 204** (full CRUD) |
| | `TestWriteNegativeCases` | 3 | 없는 이슈 PATCH 404 · title 누락 422 · 중복 라벨 422 |
| **합계** | | **50** | **47 passed · 3 skipped · 0 failed** |

> SKIPPED 3건은 대상 레포에 Issue가 없어 `pytest.skip()`으로 자동 건너뛴 정상 동작입니다. Issue가 생기면 자동 통과합니다.
> write-path(`test_issues_crud.py`, 11 TC)는 `repo` 스코프 PAT가 없으면 `write_repo` fixture가 **전체를 자동 skip**합니다 — 토큰 없이도 read-only 테스트는 그대로 동작합니다.
> `pytest -m smoke`로 핵심 엔드포인트 **5개**만, `pytest -m write`로 CRUD 11개만 슬라이스 실행할 수 있습니다.

---

## 주요 구현

### 1. GitHubAPIClient — HTTP 호출 추상화 + Allure 자동 기록

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

### 2. session-scope fixture — 연결 재사용 + 실계정 레포 자동 탐지

`public_repo` fixture가 테스트 계정의 공개 레포를 **API로 직접 조회**해 오므로 레포명을 하드코딩하지 않아도 어떤 계정에서든 동작합니다. `client`·`username`·`public_repo` 세 fixture 모두 `session` scope라 HTTP 세션은 전체 실행에서 **1개만** 생성됩니다.

```python
@pytest.fixture(scope="session")
def public_repo(client, username) -> str:
    response = client.get(f"/users/{username}/repos", params={"type": "owner", "per_page": 1})
    if response.status_code != 200:
        pytest.skip(f"Could not fetch repos ({response.status_code}): {response.json().get('message')}")
    repos = response.json()
    if not repos:
        pytest.skip("No public repositories found for this account.")
    return repos[0]["name"]
```

### 3. negative 케이스 — 404 · 422 · 인증 스코프

정상 동작만큼 **비정상 입력의 응답이 올바른지**가 API 품질의 일부입니다. 특히 `/user/emails`는 PAT에 `user:email` 스코프가 없으면 `401`도 `403`도 아닌 **`404`** 를 반환한다는 것을 직접 마주쳐, 허용 코드에 추가하고 *이유를 주석으로* 남겼습니다.

```python
def test_list_public_emails_requires_auth(self, client):
    response = client.get("/user/emails")
    # 200: authed with user:email scope, 401/403: no token, 404: token lacks user:email scope
    assert response.status_code in (200, 401, 403, 404)
```

### 4. GitHub Actions CI + Allure Pages 자동 배포

`main` push·PR마다 `test` job이 테스트를 실행하고, `report` job이 Allure 리포트를 생성해 **GitHub Pages에 배포**합니다. `gh-pages`의 history를 복사해 trend가 누적되므로 빌드마다 과거 결과와 비교됩니다. **테스트가 실패해도 리포트는 배포**합니다 — 실패했을 때야말로 리포트가 가장 필요하기 때문입니다.

```
push to main
 ├── test   : pytest → allure-results → upload artifact
 └── report : download → allure generate (+ history 누적) → deploy to gh-pages
```

> PAT는 `GH_API_TOKEN`으로 GitHub Secrets에 등록해 주입합니다. 워크플로 내장 `GITHUB_TOKEN`과의 이름 충돌을 피하기 위해 별도 이름을 사용합니다.

### 5. write-path CRUD — 샌드박스 격리 + teardown 정리

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

---

## 실행 방법

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경 변수 설정 (.env.example 복사 후 실제 값 입력)
cp .env.example .env
#   GITHUB_TOKEN=ghp_...   (read-only는 read:user면 충분 / write-path 테스트는 repo 스코프 필요)
#   GITHUB_USERNAME=your_github_username
#   GITHUB_WRITE_REPO=qa-sandbox   (write-path 전용 샌드박스 레포명 — 없으면 자동 생성)

# 3. 테스트 실행
pytest tests/                # 전체 (50 TC)
pytest tests/ -m smoke       # 핵심 엔드포인트 5개만 빠르게
pytest tests/ -m write       # write-path CRUD 11개만 (repo 스코프 PAT 필요, 없으면 자동 skip)
pytest tests/ -m user        # 영역별 (user / repos / issues / write)
pytest tests/test_user.py -v # 특정 파일

# 4. Allure 리포트
allure serve allure-results
```

> Allure CLI가 없다면 `scoop install allure`(Windows) 또는 [공식 문서](https://allurereport.org/docs/install/)로 설치합니다.
> PAT 없이도 공개 엔드포인트 테스트는 동작하며, 인증 전용 테스트(`/user` 등)는 자동으로 skip됩니다.

---

## 프로젝트 구조

```
GitHub_API/
├── config/
│   └── settings.py            # BASE_URL · 인증 헤더 · 환경변수 로드 (GITHUB_WRITE_REPO 포함)
├── utils/
│   └── api_client.py          # GitHubAPIClient — get/post/patch/delete + Allure step 자동 기록
├── tests/
│   ├── test_user.py           # User API — 공개 프로필 · 인증 유저 · followers/following (12 TC)
│   ├── test_repos.py          # Repository API — 목록 · 단건 · languages/topics/contributors (16 TC)
│   ├── test_issues.py         # Issues API (read) — 목록 · 단건 · comments · 페이지네이션 (11 TC)
│   └── test_issues_crud.py    # Issues·Labels API (write) — 생성/수정/삭제 + teardown 정리 (11 TC)
├── conftest.py                # client / username / public_repo / write_repo (session-scope fixtures)
├── postman/                   # Postman 컬렉션 (수동 탐색·재현용)
├── .github/workflows/ci.yml   # 테스트 실행 → Allure Report → GitHub Pages 배포
├── pytest.ini                 # allure 결과 경로 · marker 정의
├── .env.example               # 환경 변수 템플릿
└── requirements.txt
```

---

## 프로젝트 배경 & 회고

> 본 레포는 UI 자동화 포트폴리오([helpy-chat-qa-automation](https://github.com/seonggwon21-tech/helpy-chat-qa-automation))와 별개로, **REST API 계약 검증** 역량을 따로 정리한 것입니다. 인증·다양한 응답 형태가 공개돼 있고 누구나 재현할 수 있는 GitHub REST API를 대상으로 골랐습니다.

**Claude AI를 적극 활용해** 설계·구현 전 과정을 진행했습니다. 다만 UI 자동화와 달리 REST API 테스트는 **응답 자체가 계약(contract)** 이라는 점에 집중했습니다 — 상태 코드가 `200`인지 보는 것에 그치지 않고, 스키마 필드의 존재·데이터 타입·페이지네이션·negative 케이스까지 검증해야 비로소 "API가 올바르게 동작한다"고 말할 수 있다고 봤습니다.

가장 기억에 남는 건 `/user/emails`였습니다. 인증이 필요한 엔드포인트라 당연히 `401`을 예상했는데, 실제로는 **`404`** 가 돌아왔습니다. PAT에 `user:email` 스코프가 없으면 GitHub이 "권한 없음"이 아니라 "없는 리소스"로 응답하기 때문이었습니다. 허용 코드에 `404`를 그냥 추가하는 대신, *왜 이런 코드가 나오는지*를 주석으로 남겨 다음 사람이 이해할 수 있게 했습니다. 같은 엔드포인트가 **토큰 스코프에 따라 다른 상태 코드를 반환**한다는 걸 직접 마주하니, API 테스트가 단순 호출 검증이 아니라는 게 와닿았습니다.

<details>
<summary>API 테스트를 만들며 세운 원칙</summary>

- **상태 코드는 시작일 뿐** — 스키마 필드·타입·정합성까지 봐야 계약 검증
- **거부 동작도 기능이다** — 404·422·인증 실패를 정상 케이스만큼 명시적으로 검증
- **하드코딩을 줄인다** — 공개 레포를 fixture가 동적 탐지해 어떤 계정에서도 동작
- **리포트는 실패할 때 가장 필요하다** — 테스트가 깨져도 Allure를 배포하고, 매 호출을 step으로 추적 가능하게

</details>
