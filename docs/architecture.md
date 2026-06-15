# 아키텍처 & 테스트 구성

> 프로젝트 구조와 테스트 스위트 구성입니다. 메인 개요는 [README](../README.md) 참고.

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

> 전체 TC의 시나리오·입력·기대결과·심각도는 **[테스트 케이스 명세서](TEST_CASES.md)** 참고.

### 마커(marker) 슬라이스

| 마커 | 의미 |
|---|---|
| `smoke` | 핵심 엔드포인트 5개 — 회귀 시 우선 실행 |
| `user` / `repos` / `issues` | 기능 영역별 분류 |
| `write` | 실데이터 변경(CRUD) — `repo` 스코프 PAT 없으면 자동 skip |

> SKIPPED 3건은 대상 레포에 Issue가 없어 `pytest.skip()`으로 자동 건너뛴 정상 동작입니다. Issue가 생기면 자동 통과합니다.
> write-path(`test_issues_crud.py`, 11 TC)는 `repo` 스코프 PAT가 없으면 `write_repo` fixture가 **전체를 자동 skip**합니다.

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
├── docs/
│   ├── TEST_CASES.md          # 테스트 케이스 명세서 — 50 TC 시나리오·입력·기대결과·심각도
│   ├── architecture.md        # 이 문서 — 프로젝트 구조 · 테스트 구성
│   └── implementation.md      # 주요 구현 5선 — 설계·코드 상세
├── postman/                   # Postman 컬렉션 (수동 탐색·재현용)
├── .github/workflows/ci.yml   # 테스트 실행 → Allure Report → GitHub Pages 배포
├── pytest.ini                 # allure 결과 경로 · marker 정의
├── ruff.toml                  # 린트/포맷 설정 (standalone — pyproject 미사용 방침)
├── .pre-commit-config.yaml    # 커밋 훅 — ruff check + format
├── .env.example               # 환경 변수 템플릿
├── requirements.txt           # 런타임 의존성
└── requirements-dev.txt       # 개발 도구 (ruff · pre-commit)
```

---

## Allure 리포팅 구성

`GitHubAPIClient`가 매 HTTP 요청을 `allure.step`으로 감싸 **URL · Status Code · Response Body**를 자동 첨부하고, 테스트는 `epic → feature → story → step` 4계층으로 분류됩니다.

| 계층 | 값 |
|---|---|
| epic | `GitHub REST API` |
| feature | `User API` / `Repository API` / `Issues API` / `Issues API (write)` / `Labels API (write)` |
| story | `Get public user profile`, `Create an issue`, `Delete a label` 등 |
| step | 매 HTTP 호출 (`GET /users/...`) — Status·Body 첨부 |

> 📊 **Live Allure Report** → https://seonggwon21-tech.github.io/GitHub_API/ *(매 `main` push마다 trend 누적 갱신)*
