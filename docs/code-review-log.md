# 코드 리뷰 로그

> 테스트 코드 전반을 주기적으로 점검하고, 발견한 문제와 그 처리 판단을 기록합니다.
> 정상 케이스를 늘리는 것만큼 **이미 작성한 코드가 견고한지** 되짚는 것도 QA의 일이라 보고 남깁니다.

---

## 1회차 — 2026-06-14 · 전체 소스 점검

대상: `conftest.py` · `utils/api_client.py` · `tests/*` 전체
관점: 상태 의존성, 외부 I/O 견고성, teardown 정합성, negative 케이스

| # | 발견 | 심각도 | 조치 | 근거 커밋 |
|:---:|---|:---:|---|:---:|
| 1 | `GitHubAPIClient`의 모든 HTTP 호출에 timeout이 없어, 연결이 멈추면 스위트·CI가 무한 대기 | High | `(5, 30)` connect/read timeout 적용 | `01b4e48` |
| 2 | `public_repo` fixture가 정렬상 첫 레포를 그대로 선택 → 그 레포의 Issues가 비활성/fork면 `GET .../issues`가 `410`을 반환해 issue 테스트가 false-fail | Medium | 보류 → **3회차 해결** | — |
| 3 | `test_comment_create_then_delete`의 코멘트가 fixture가 아닌 본문에서 생성돼, 중간 단언 실패 시 샌드박스에 코멘트가 남음 | Low | 보류 → **3회차 해결** | — |

### 처리 판단

- **#1 (수정)** — 외부 API(`api.github.com`)에 의존하는 스위트에서 timeout 누락은 가장 실질적인 리스크였다. 연결 단절·프록시 hang 시 GitHub Actions 잡이 잡 타임아웃까지 매달린다. 세션 공통 상수로 빼 네 메서드에 일괄 적용했다.
- **#2 (보류)** — 계정·정렬 상태에 따라 갈리는 환경 의존 취약성이다. 현재 테스트 계정에서는 재현되지 않으며, 근본 해결은 `has_issues=true` 필터나 대상 레포 명시가 필요하다. 재현되거나 대상 계정이 바뀔 때 다루기로 했다.
- **#3 (보류)** — 영향이 private 샌드박스로 한정되고, 같은 이슈가 `new_issue` teardown에서 닫히므로 누수 비용이 작다. 클린업 일관성 차원에서 코멘트도 fixture로 빼는 개선 여지는 인지하고 남겨 둔다.

> 점검 기준선: 50 TC / 47 passed · 3 skipped · 0 failed (read-only 환경).

---

## 2회차 — 2026-06-14 · 죽은 코드·중복 점검

대상: `pytest.ini` · `requirements.txt` · `.gitignore` · `tests/*`
관점: 미사용 설정/의존성, 중복 리포터, 하드코딩 중복

| # | 발견 | 심각도 | 조치 | 근거 커밋 |
|:---:|---|:---:|---|:---:|
| 1 | `regression` 마커가 등록만 되고 사용처가 0 — 죽은 설정 | Low | 삭제 | `9904569` |
| 2 | pytest-html(`report.html`)이 Allure와 중복되는 2차 리포터 — 커밋·CI·문서 어디에도 안 쓰이는데 매 실행 생성 | Low | addopts·의존성·gitignore·산출물 일괄 제거 | `9904569` |
| 3 | 존재하지 않는 user 리터럴이 `test_user`·`test_repos`에 중복 하드코딩 | Low | `nonexistent_username` 공용 fixture로 통합 | `9904569` |

### 처리 판단

- **#1·#2 (수정)** — 셋 다 기능 영향은 없지만, 이 프로젝트의 리포팅 컨셉은 **Allure 하나**다. 보여주지도 않는 pytest-html이 매 실행 돌고 의존성까지 차지하는 건 "일관된 리포팅"이라는 의도와 어긋나 걷어냈다. 미사용 마커도 같은 맥락에서 정리했다.
- **#3 (수정)** — 같은 매직 리터럴이 두 파일에 흩어져 있어, 값이 바뀌면 한쪽만 고칠 위험이 있었다. session fixture로 단일화해 negative 케이스 전체가 한 곳을 참조하게 했다.

> 기준선 유지: 50 TC / 47 passed · 3 skipped · 0 failed. 1회차 보류 항목(#2 `public_repo` 410, #3 코멘트 fixture화)은 이번 점검 범위 밖으로, 여전히 열려 있다.

---

## 3회차 — 2026-06-15 · 보류 항목 해소 + 도구/CI 강화

대상: `conftest.py` · `tests/test_issues_crud.py` · `.github/workflows/ci.yml` · 신규 `ruff.toml` · `.pre-commit-config.yaml` · `requirements-dev.txt`
관점: 1·2회차 보류 항목 종결, 정적 분석·CI 호환성 기반 마련

| # | 항목 | 심각도 | 조치 |
|:---:|---|:---:|---|
| 1 | 1회차 #2 — `public_repo`가 첫 레포를 그대로 선택해 Issues 비활성/fork 레포에서 410 false-fail 가능 | Medium | `per_page=100`으로 받아 `has_issues=true`인 첫 레포를 선택, 없으면 첫 레포로 폴백 |
| 2 | 1회차 #3 — 코멘트가 본문에서 생성돼 중간 실패 시 샌드박스에 잔존 | Low | `new_comment` fixture로 분리, teardown에서 idempotent 삭제 |
| 3 | 정적 분석 부재 — 스타일/임포트 정렬이 사람 손에 의존 | Low | `ruff`(check+format) 도입, `.pre-commit-config.yaml`로 커밋 훅화. 전체 소스 1회 정렬·포맷 |
| 4 | CI가 단일 Python(3.12)만 검증 | Low | `3.12`·`3.13` 매트릭스로 호환성 증명, `setup-python` pip 캐싱 추가 |
| 5 | 런타임/개발 의존성 혼재 | Low | `requirements-dev.txt`(ruff·pre-commit)로 분리 |

### 처리 판단

- **#1 (수정)** — 환경 의존 취약성을 fixture 선택 로직에서 근본 차단했다. `has_issues` 필터로 Issues 스위트가 항상 사용 가능한 레포를 받게 하되, read-only 레포 테스트만 도는 계정을 위해 첫 레포 폴백을 남겼다.
- **#2 (수정)** — 코멘트 생명주기를 fixture로 옮겨, 본문 단언이 중간에 깨져도 teardown이 샌드박스를 정리한다. `new_issue`·`created_label`과 teardown 패턴이 일관된다.
- **#3 (수정)** — 이 레포는 `pyproject.toml`을 두지 않는 방침이라 `ruff.toml` 단독 설정으로 갔다. line-length는 서술형 테스트 시그니처를 한 줄로 유지하도록 120으로 잡았다.
- **#4·#5 (수정)** — 개선 백로그의 quick win 항목. 매트릭스는 동일 스위트를 두 버전에서 돌리되, Allure 리포트 중복을 막으려 결과 업로드는 3.12에서만 한다.

> 기준선 유지: 50 TC / 47 passed · 3 skipped · 0 failed. `ruff check`·`ruff format --check` 클린.
