# 테스트 케이스 명세서 (Test Case Specification)

> 대상 시스템: **GitHub REST API** (`https://api.github.com`)
> API 버전: `2022-11-28` / `Accept: application/vnd.github+json`
> 테스트 프레임워크: `pytest` + `requests` + `allure`
> 작성 기준: `tests/` 디렉터리의 자동화 테스트 코드

---

## 1. 개요

| 항목 | 내용 |
|------|------|
| 테스트 목적 | GitHub REST API의 기능 동작, 응답 스키마, 상태 코드, 권한/검증 동작 검증 |
| 테스트 범위 | User API, Repository API, Issues API(읽기), Issues/Labels API(쓰기 CRUD) |
| 테스트 유형 | 기능(Functional), 계약/스키마(Contract), 경계/부정(Negative) |
| 인증 방식 | PAT(Personal Access Token) — `Authorization: Bearer <token>` (`.env` 관리) |
| 테스트 데이터 | 공개 유저/레포(읽기), 전용 샌드박스 레포 `qa-sandbox`(쓰기) |
| 환경 변수 | `GITHUB_TOKEN`, `GITHUB_USERNAME`, `GITHUB_WRITE_REPO` |

### 마커(Marker) 분류
| 마커 | 의미 |
|------|------|
| `smoke` | 핵심 정상 경로 — 회귀 시 우선 실행 |
| `user` / `repos` / `issues` | 기능 영역별 분류 |
| `write` | 실데이터 변경(CRUD) — 토큰/권한 없으면 자동 skip |

### 심각도(Severity) 분류
| 등급 | 의미 |
|------|------|
| BLOCKER | 실패 시 해당 API 사용 불가 — 최우선 |
| CRITICAL | 핵심 기능 결함 |
| NORMAL | 일반 기능 |

---

## 2. 전제 조건 (Preconditions)

1. 네트워크에서 `api.github.com` 접근 가능
2. (읽기) 대상 계정에 최소 1개 이상의 공개 레포가 존재
3. (쓰기) `repo` 스코프를 가진 PAT가 `GITHUB_TOKEN`에 설정됨
4. (쓰기) 샌드박스 레포가 없으면 픽스처가 `private/auto_init` 레포를 1회 생성
5. 토큰/권한 미충족 시 쓰기 테스트는 **실패가 아닌 skip** 처리

---

## 3. User API 테스트 케이스

**Feature:** User API | **파일:** `tests/test_user.py`

### 3.1 공개 유저 프로필 (TestPublicUser)

| TC ID | 시나리오 | 사전조건 | 입력 | 기대 결과 | 심각도 | 마커 |
|-------|----------|----------|------|-----------|--------|------|
| USR-001 | 공개 유저 조회 성공 | 존재하는 username | `GET /users/{username}` | `200` | BLOCKER | smoke |
| USR-002 | 응답 스키마 검증 | - | `GET /users/{username}` | `login, id, type, public_repos, followers, following` 필드 존재 | NORMAL | - |
| USR-003 | login 값 일치 | - | `GET /users/{username}` | 응답 `login`(소문자) == 요청 username | NORMAL | - |
| USR-004 | 계정 타입 확인 | - | `GET /users/{username}` | `type == "User"` | NORMAL | - |
| USR-005 | 존재하지 않는 유저 | - | `GET /users/this-user-...-xyzxyz999` | `404` | NORMAL | - |
| USR-006 | 응답 Content-Type | - | `GET /users/{username}` | `Content-Type`에 `application/json` 포함 | NORMAL | - |

### 3.2 인증 유저 (TestAuthenticatedUser)

| TC ID | 시나리오 | 사전조건 | 입력 | 기대 결과 | 심각도 | 마커 |
|-------|----------|----------|------|-----------|--------|------|
| USR-007 | 인증 유저 조회 | - | `GET /user` | `200`(인증) 또는 `401`(토큰 없음) | CRITICAL | smoke |
| USR-008 | 인증 시 스키마 검증 | 유효 토큰 | `GET /user` | `login`, `email` 필드 존재 / `email`은 `str` 또는 `null` (401이면 skip) | NORMAL | - |
| USR-009 | 공개 이메일 목록 권한 | - | `GET /user/emails` | `200/401/403/404` 중 하나 (스코프에 따라) | NORMAL | - |

### 3.3 팔로워/팔로잉 (TestUserFollowers)

| TC ID | 시나리오 | 입력 | 기대 결과 | 심각도 |
|-------|----------|------|-----------|--------|
| USR-010 | 팔로워 목록 조회 | `GET /users/{username}/followers` | `200` | NORMAL |
| USR-011 | 팔로워 응답 타입 | `GET /users/{username}/followers` | 응답이 `list` 타입 | NORMAL |
| USR-012 | 팔로잉 목록 조회 | `GET /users/{username}/following` | `200` | NORMAL |

---

## 4. Repository API 테스트 케이스

**Feature:** Repository API | **파일:** `tests/test_repos.py`

### 4.1 레포 목록 (TestListRepositories)

| TC ID | 시나리오 | 입력 | 기대 결과 | 심각도 | 마커 |
|-------|----------|------|-----------|--------|------|
| REP-001 | 공개 레포 목록 성공 | `GET /users/{username}/repos` | `200` | BLOCKER | smoke |
| REP-002 | 응답 타입 검증 | `GET /users/{username}/repos` | 응답이 `list` 타입 | NORMAL | - |
| REP-003 | 레포 스키마 검증 | `?per_page=1` | `id, name, full_name, private, owner, html_url, fork` 필드 존재 (없으면 skip) | NORMAL | - |
| REP-004 | 비공개 레포 미노출 보장 | `?type=owner&per_page=10` | 모든 레포 `private == false` | NORMAL | - |
| REP-005 | 페이지네이션 | `?per_page=1&page=1` | `200` + `list` | NORMAL | - |
| REP-006 | 정렬(updated/desc) | `?sort=updated&direction=desc&per_page=5` | `200` | NORMAL | - |
| REP-007 | 잘못된 정렬 값 | `?sort=nonexistent_sort_value` | `200` 또는 `422` | NORMAL | - |
| REP-008 | 존재하지 않는 유저 레포 | `GET /users/...-xyzxyz999/repos` | `404` | NORMAL | - |

### 4.2 단일 레포 (TestGetRepository)

| TC ID | 시나리오 | 입력 | 기대 결과 | 심각도 | 마커 |
|-------|----------|------|-----------|--------|------|
| REP-009 | 단일 레포 조회 성공 | `GET /repos/{owner}/{repo}` | `200` | CRITICAL | smoke |
| REP-010 | 레포명 일치 | `GET /repos/{owner}/{repo}` | 응답 `name` == repo | NORMAL | - |
| REP-011 | 소유자 일치 | `GET /repos/{owner}/{repo}` | `owner.login`(소문자) == username | NORMAL | - |
| REP-012 | 상세 스키마 검증 | `GET /repos/{owner}/{repo}` | `id, name, full_name, owner, private, html_url, description, fork, created_at, updated_at, stargazers_count, watchers_count, forks_count, default_branch` 필드 존재 | NORMAL | - |
| REP-013 | 존재하지 않는 레포 | `GET /repos/{owner}/repo-...-xyz9999` | `404` | NORMAL | - |
| REP-014 | 언어 목록 조회 | `GET /repos/{owner}/{repo}/languages` | `200` + `dict` | NORMAL | - |
| REP-015 | 토픽 조회 | `GET /repos/{owner}/{repo}/topics` | `200` + `names` 키 존재 | NORMAL | - |
| REP-016 | 기여자 조회 | `GET /repos/{owner}/{repo}/contributors` | `200` 또는 `204`(빈 기여자) | NORMAL | - |

---

## 5. Issues API 테스트 케이스 (읽기)

**Feature:** Issues API | **파일:** `tests/test_issues.py`

### 5.1 이슈 목록 (TestListIssues)

| TC ID | 시나리오 | 입력 | 기대 결과 | 심각도 | 마커 |
|-------|----------|------|-----------|--------|------|
| ISS-001 | 이슈 목록 조회 성공 | `GET /repos/{owner}/{repo}/issues` | `200` | CRITICAL | smoke |
| ISS-002 | 응답 타입 검증 | `GET .../issues` | 응답이 `list` 타입 | NORMAL | - |
| ISS-003 | open 상태 필터 | `?state=open&per_page=5` | 모든 이슈 `state == "open"` | NORMAL | - |
| ISS-004 | closed 상태 필터 | `?state=closed&per_page=5` | 모든 이슈 `state == "closed"` | NORMAL | - |
| ISS-005 | 이슈 스키마 검증 | `?per_page=1` | `id, number, title, state, user, created_at, updated_at, html_url` 필드 존재 (없으면 skip) | NORMAL | - |
| ISS-006 | 페이지네이션 | `?state=all&per_page=1&page=1` vs `page=2` | page1[0].id ≠ page2[0].id (둘 다 존재 시) | NORMAL | - |
| ISS-007 | 잘못된 state 값 | `?state=invalid_state` | `422` | NORMAL | - |
| ISS-008 | 존재하지 않는 레포 이슈 | `GET /repos/{owner}/repo-...-xyz9999/issues` | `404` | NORMAL | - |

### 5.2 단일 이슈/댓글 (TestGetIssue)

| TC ID | 시나리오 | 입력 | 기대 결과 | 심각도 |
|-------|----------|------|-----------|--------|
| ISS-009 | 첫 이슈 단건 조회 | 목록 첫 이슈 number로 `GET .../issues/{number}` | `200` (이슈 없으면 skip) | NORMAL |
| ISS-010 | 존재하지 않는 이슈 | `GET .../issues/9999999` | `404` | NORMAL |
| ISS-011 | 이슈 댓글 목록 | `GET .../issues/{number}/comments` | `200` + `list` (이슈 없으면 skip) | NORMAL |

---

## 6. Issues / Labels API 테스트 케이스 (쓰기 CRUD)

**Feature:** Issues/Labels API (write) | **파일:** `tests/test_issues_crud.py`
**공통 사전조건:** `repo` 스코프 PAT 필요 / 샌드박스 레포(`qa-sandbox`)에서만 실행 / 미충족 시 모듈 전체 skip
**클린업:** 이슈는 REST 하드 삭제 불가 → teardown에서 `closed` 처리 / 댓글·라벨은 DELETE(204)

### 6.1 이슈 라이프사이클 (TestIssueLifecycle)

| TC ID | 시나리오 | 입력 | 기대 결과 | 심각도 |
|-------|----------|------|-----------|--------|
| CRUD-001 | 이슈 생성 | `POST .../issues {title, body}` | `201` + `number`(int) + `state=="open"` + title 접두사 일치 | CRITICAL |
| CRUD-002 | 생성 이슈 재조회 | `GET .../issues/{number}` | `200` + title/body가 POST한 값과 round-trip 일치 | NORMAL |
| CRUD-003 | 이슈 제목 수정 | `PATCH .../issues/{number} {title}` | `200` + 응답 title 변경 + 재조회 시 영속 확인 | CRITICAL |
| CRUD-004 | 이슈 닫기 | `PATCH .../issues/{number} {state:"closed"}` | `200` + `state=="closed"` | NORMAL |

### 6.2 이슈 댓글 (TestIssueComment)

| TC ID | 시나리오 | 입력 | 기대 결과 | 심각도 |
|-------|----------|------|-----------|--------|
| CRUD-005 | 댓글 생성→삭제→검증 | `POST .../comments` → `DELETE .../comments/{id}` → `GET` | 생성 `201` → 삭제 `204` → 재조회 `404` | NORMAL |

### 6.3 라벨 CRUD (TestLabelCrud)

| TC ID | 시나리오 | 입력 | 기대 결과 | 심각도 |
|-------|----------|------|-----------|--------|
| CRUD-006 | 라벨 생성 | `POST .../labels {name, color, description}` | `201` + name 일치 + `color=="ededed"` | NORMAL |
| CRUD-007 | 라벨 수정 | `PATCH .../labels/{name} {color, description}` | `200` + `color=="0e8a16"` + description 갱신 | NORMAL |
| CRUD-008 | 라벨 삭제 | `DELETE .../labels/{name}` | `204` + 재조회 `404` | CRITICAL |

### 6.4 부정 케이스 (TestWriteNegativeCases)

| TC ID | 시나리오 | 입력 | 기대 결과 | 심각도 |
|-------|----------|------|-----------|--------|
| CRUD-009 | 존재하지 않는 이슈 수정 | `PATCH .../issues/9999999 {title}` | `404` | NORMAL |
| CRUD-010 | title 없는 이슈 생성 | `POST .../issues {body}` (title 누락) | `422` (필수값 검증) | NORMAL |
| CRUD-011 | 중복 라벨 생성 | 기존 name으로 `POST .../labels` | `422` (already_exists) | NORMAL |

---

## 7. 요약 통계

| 영역 | 케이스 수 | smoke | 비고 |
|------|-----------|-------|------|
| User API | 12 | 2 | 읽기 |
| Repository API | 16 | 2 | 읽기 |
| Issues API (읽기) | 11 | 1 | 읽기 |
| Issues/Labels (쓰기 CRUD) | 11 | - | 토큰 필요, 미충족 시 skip |
| **합계** | **50** | **5** | |

---

## 8. 실행 방법

```bash
# 전체 실행
pytest

# 스모크만 실행
pytest -m smoke

# 영역별 실행
pytest -m user
pytest -m repos
pytest -m issues

# 읽기 전용(쓰기 제외)
pytest -m "not write"

# Allure 리포트 생성
pytest --alluredir=allure-results
allure serve allure-results
```
