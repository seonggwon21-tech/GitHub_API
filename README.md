# GitHub REST API QA Automation

> GitHub REST API(api.github.com) — User · Repository · Issues **총 39 TC**, pytest + requests + Allure 기반 REST API 테스트 자동화 포트폴리오

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-8.x-0A9EDC?logo=pytest&logoColor=white)
![requests](https://img.shields.io/badge/requests-2.x-FF6B35?logo=python&logoColor=white)
![Allure](https://img.shields.io/badge/Allure-Report-FF6B6B?logo=qameta&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI-2088FF?logo=githubactions&logoColor=white)
[![CI](https://github.com/seonggwon21-tech/GitHub_API/actions/workflows/ci.yml/badge.svg)](https://github.com/seonggwon21-tech/GitHub_API/actions/workflows/ci.yml)

> **Claude AI를 적극 활용해** 설계·구현 전 과정을 진행했습니다.
>
> UI 자동화와 달리 REST API 테스트는 응답 자체가 계약(contract)입니다. 상태 코드가 200인지 확인하는 것에 그치지 않고, 스키마 필드의 존재 여부, 데이터 타입, 페이지네이션 동작, 음성(negative) 케이스까지 검증해야 "API가 올바르게 동작한다"고 말할 수 있다고 생각했습니다.
>
> `public_repo` fixture 하나가 session scope로 동작하면서 Repository·Issues 테스트 전체에 공유되는 구조가 대표적인 설계 결정입니다. 실제 계정의 공개 레포를 자동으로 탐지해 오는 방식으로, 하드코딩 없이 어떤 계정에서도 동작합니다.
>
> PAT 스코프에 따라 동일 엔드포인트가 다른 상태 코드를 반환한다는 것도 직접 마주쳤습니다. `/user/emails`가 PAT에 `user:email` 스코프가 없으면 200도 401도 아닌 404를 반환합니다. 단순히 허용 코드에 404를 추가하는 게 아니라, 주석으로 이유를 명시해 다음 사람이 왜 이런 코드가 있는지 이해할 수 있게 했습니다.

---

## 프로젝트 개요

**REST API 계약 검증 · 39 TC · 36 passed · 3 skipped · GitHub Actions CI + Allure Pages 자동 배포**

GitHub REST API의 공개 엔드포인트를 대상으로 상태 코드, 응답 스키마, 데이터 정합성, 음성 케이스, 페이지네이션을 자동으로 검증합니다. `session` scope fixture로 HTTP 세션을 재사용해 테스트 전체에서 연결 오버헤드를 최소화하고, 각 API 호출은 Allure step으로 자동 기록되어 어느 요청에서 무엇이 반환됐는지 리포트에서 추적할 수 있습니다.

---

## 기술 스택

| 분류 | 사용 기술 | 선택 이유 |
|---|---|---|
| 언어 | Python 3.12 | requests · pytest · allure 생태계 표준 |
| HTTP 클라이언트 | requests | `Session` 객체로 헤더·연결 풀 재사용, 인증 헤더 일괄 관리 |
| 테스트 프레임워크 | pytest 8.x | fixture scope(`session`/`function`) 분리, marker 기반 슬라이스(`smoke`/`user`/`repos`/`issues`) |
| 리포팅 | allure-pytest | epic/feature/story/step 4계층 + HTTP 요청별 Status Code·Response Body 자동 첨부 |
| CI/CD | GitHub Actions | push·PR마다 자동 테스트 실행, Allure Report → GitHub Pages 자동 배포 |
| 환경 관리 | python-dotenv | `.env`로 PAT·사용자명을 코드와 분리, `.gitignore` 처리 |

---

## 프로젝트 구조

```
GitHub_API/
├── config/
│   └── settings.py            # BASE_URL, 인증 헤더, 환경변수 로드
├── utils/
│   └── api_client.py          # GitHubAPIClient — get/post/patch/delete + allure step 자동 기록
├── tests/
│   ├── test_user.py           # User API — 공개 프로필, 인증 유저, followers/following (12 TC)
│   ├── test_repos.py          # Repository API — 목록, 단건, languages/topics/contributors (16 TC)
│   └── test_issues.py         # Issues API — 목록, 단건, comments, 페이지네이션 (11 TC)
├── conftest.py                # client / username / public_repo session-scope fixtures
├── pytest.ini                 # allure 결과 경로, marker 정의, html 리포트
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions — 테스트 실행 → Allure Report → GitHub Pages 배포
├── .env.example               # 환경 변수 템플릿
└── requirements.txt
```

---

## 테스트 구성

| 파일 | 클래스 | TC | 검증 내용 |
|---|---|---|---|
| `test_user.py` | `TestPublicUser` | 6 | 공개 프로필 200, 스키마, login/type 정합성, 404, Content-Type |
| | `TestAuthenticatedUser` | 3 | 인증 유저 200/401, 스키마, `/user/emails` 스코프별 응답 |
| | `TestUserFollowers` | 3 | followers/following 200, list 타입 |
| `test_repos.py` | `TestListRepositories` | 8 | 200, list 타입, 스키마, public 여부, 페이지네이션, 정렬, 404 |
| | `TestGetRepository` | 8 | 200, name/owner 정합성, 스키마, 404, languages/topics/contributors |
| `test_issues.py` | `TestListIssues` | 8 | 200, list 타입, state 필터(open/closed), 스키마, 페이지네이션, 422, 404 |
| | `TestGetIssue` | 3 | 단건 200, 404, comments 200 |
| **합계** | | **39** | **36 passed · 3 skipped** |

> SKIPPED 3개는 대상 레포에 Issue가 없어 자동으로 건너뛴 것으로 정상 동작입니다.  
> `pytest -m smoke`로 핵심 엔드포인트 5개만 빠르게 검증할 수 있습니다.

---

## 주요 구현 내용

### 1. GitHubAPIClient — Allure step 자동 기록

**모든 HTTP 호출을 `allure.step`으로 감싸 어느 요청에서 무엇이 반환됐는지 리포트에서 추적할 수 있습니다.** 테스트 코드는 `client.get("/users/{username}")`만 호출하면 되고, 리포트에는 URL · Status Code · Response Body가 자동 첨부됩니다.

```python
def get(self, endpoint: str, params: dict = None) -> requests.Response:
    url = f"{self.base_url}{endpoint}"
    with allure.step(f"GET {url}"):
        response = self.session.get(url, params=params)
        allure.attach(str(response.status_code), name="Status Code", ...)
        allure.attach(response.text, name="Response Body", ...)
    return response
```

`requests.Session`을 재사용하므로 인증 헤더는 `session.headers`에 한 번만 세팅하면 이후 모든 요청에 자동으로 포함됩니다.

### 2. session scope fixture — 연결 재사용 + 실계정 레포 자동 탐지

**`public_repo` fixture는 테스트 계정의 공개 레포를 API로 자동으로 탐지해 오기 때문에, 레포 이름을 하드코딩하지 않아도 어떤 계정에서도 동작합니다.**

```python
@pytest.fixture(scope="session")
def public_repo(client, username) -> str:
    response = client.get(f"/users/{username}/repos", params={"type": "public", "per_page": 1})
    if response.status_code != 200:
        pytest.skip(f"Could not fetch repos ({response.status_code}): {response.json().get('message')}")
    repos = response.json()
    if not repos:
        pytest.skip("No public repositories found for this account.")
    return repos[0]["name"]
```

`client`, `username`, `public_repo` 세 fixture가 모두 `scope="session"`이므로 HTTP 세션은 테스트 전체에서 1개만 생성됩니다.

### 3. 음성(negative) 케이스 — 404, 422, 인증 스코프 검증

**정상 동작 검증만큼 비정상 입력에 대한 응답이 올바른지 확인하는 것도 API 품질의 일부입니다.** 존재하지 않는 사용자·레포·이슈에 대한 404, 잘못된 파라미터(`state=invalid_state`)에 대한 422를 명시적으로 검증합니다.

```python
def test_list_issues_invalid_state_returns_422(self, ...):
    response = client.get(f"/repos/{username}/{public_repo}/issues",
                          params={"state": "invalid_state"})
    assert response.status_code == 422
```

`/user/emails`는 PAT에 `user:email` 스코프가 없으면 GitHub이 404를 반환하는 것을 직접 확인하고 허용 코드에 추가했습니다.

```python
def test_list_public_emails_requires_auth(self, client):
    response = client.get("/user/emails")
    # 200: authed with user:email scope, 401/403: no token, 404: token lacks user:email scope
    assert response.status_code in (200, 401, 403, 404)
```

### 4. GitHub Actions CI + Allure Pages 자동 배포

**`main` 브랜치에 push할 때마다 테스트가 자동 실행되고, 결과가 GitHub Pages에 배포됩니다.** Trend 히스토리는 `gh-pages` 브랜치에서 복사해 누적되므로, 매 빌드마다 과거 결과와 비교할 수 있습니다.

```
push to main
  └── test job
        ├── pytest tests/ → allure-results/
        └── upload artifact
  └── report job (main only)
        ├── download artifact
        ├── copy gh-pages/history → allure-results/history  (trend 누적)
        ├── allure generate
        └── deploy to gh-pages
```

PAT는 `GH_API_TOKEN` 이름으로 GitHub Secrets에 등록해 CI에 주입합니다. 워크플로 내장 `GITHUB_TOKEN`과 이름 충돌을 피하기 위해 별도 이름을 사용합니다.

---

## 로컬 실행 방법

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env.example`을 복사해 `.env`를 생성하고 PAT를 입력합니다.

```bash
cp .env.example .env
```

```env
GITHUB_TOKEN=ghp_your_personal_access_token_here
GITHUB_USERNAME=your_github_username
```

> PAT는 `repo`, `read:user` 스코프면 충분합니다. `user:email` 스코프 없이도 테스트는 통과합니다.

### 3. 테스트 실행

```bash
# 전체 실행
pytest tests/

# smoke 테스트만 (5개, 빠른 검증)
pytest tests/ -m smoke

# API 영역별 실행
pytest tests/ -m user
pytest tests/ -m repos
pytest tests/ -m issues

# 특정 파일
pytest tests/test_user.py -v
```

### 4. Allure 리포트 확인

```bash
allure serve allure-results
```

> Allure CLI가 없다면 `scoop install allure` (Windows) 또는 [공식 다운로드](https://allurereport.org/docs/install/)에서 설치합니다.

---

## 테스트 결과

| 구분 | TC 수 | 결과 |
|---|---|---|
| User API | 12 | **12 passed** |
| Repository API | 16 | **16 passed** |
| Issues API | 11 | **8 passed · 3 skipped** |
| **총계** | **39** | **36 passed · 3 skipped · 0 failed** |

> SKIPPED는 대상 레포에 Issue가 없어 `pytest.skip()`으로 건너뛴 케이스입니다. Issue가 생기면 자동으로 통과합니다.
