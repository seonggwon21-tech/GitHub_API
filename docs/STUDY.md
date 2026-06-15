# 이 레포 소화하기 (Study Guide)

> "내가 끝까지 설명할 수 있는 포트폴리오"를 위한 학습 문서.
> 각 조각이 **왜 있는지**를 내 말로 정리하고, 면접에서 나올 법한 질문에 답을 미리 만들어 둔다.

---

## 1. 한 문장으로

> GitHub REST API를 대상으로, **요청을 보내고 응답이 계약(contract)대로인지** 검증하는 pytest 자동화 프로젝트.
> 상태코드만 보는 게 아니라 스키마·정합성·CRUD·실패 케이스까지 본다. CI에서 자동 실행되고 Allure 리포트가 자동 배포된다.

---

## 2. 큰 그림 (요청 한 번이 흐르는 길)

```
테스트 함수 (tests/*.py)
   │  client.get("/users/{u}/repos") 처럼 호출
   ▼
GitHubAPIClient (utils/api_client.py)
   │  requests.Session 으로 실제 HTTP 전송 + Allure에 요청/응답 자동 첨부
   ▼
api.github.com  ──►  응답(JSON)
   ▲
   │  conftest.py의 fixture가 client·username·테스트 대상 레포를 미리 준비
   │  factories.py가 POST/PATCH에 보낼 payload(dict)를 만들어 줌
   ▼
assert 로 검증  ──►  Allure 리포트 (CI가 GitHub Pages로 배포)
```

핵심: **테스트는 "무엇을 검증할지"만 쓰고, "어떻게 호출/준비하는지"는 client·fixture·factory가 담당**한다. 이 분리가 이 레포의 뼈대다.

---

## 3. 파일별 "이게 왜 있나" (내 말로)

| 파일 | 한 줄 설명 | 면접에서 이렇게 말한다 |
|---|---|---|
| `config/settings.py` | BASE_URL·인증 헤더·`.env`에서 토큰 로드 | "환경값(토큰·유저명)을 코드에서 분리해 `.env`로 관리했습니다" |
| `utils/api_client.py` | `GitHubAPIClient` — get/post/patch/put/delete를 감싸고 매 호출을 Allure step으로 기록 | "requests를 얇게 감싸 URL 조립·타임아웃·리포트 첨부를 한곳에 모았습니다" |
| `utils/factories.py` | 이슈/라벨/코멘트/마일스톤 **payload 빌더**, uuid로 유니크 이름 | "요청 본문을 테스트마다 복붙하지 않게 빌더로 모았고, 이름을 유니크하게 만들어 재실행 충돌을 막았습니다" |
| `conftest.py` | 공용 fixture: `client`·`username`·`public_repo`·`write_repo` | "fixture로 준비 단계를 공유하고, 쓰기 테스트는 토큰 게이트로 안전하게 막았습니다" |
| `tests/test_user.py` | User API (프로필·인증·팔로워) | — |
| `tests/test_repos.py` | Repository API (목록·단건·languages 등) | — |
| `tests/test_issues.py` | Issues API **읽기** (목록·단건·페이지네이션·negative) | — |
| `tests/test_issues_crud.py` | Issues·Labels·Milestones **쓰기** 라이프사이클 CRUD | "읽기를 넘어 실제 생성·수정·삭제까지 검증한 게 이 레포의 차별점입니다" |
| `pytest.ini` | Allure 결과 경로 · 마커 정의 | — |
| `ruff.toml` / `.pre-commit-config.yaml` | 린트·포맷 + 커밋 훅 | "ruff로 스타일을 자동화하고 pre-commit으로 커밋마다 강제했습니다" |
| `.github/workflows/ci.yml` | push/PR마다 테스트(3.12·3.13) → Allure → Pages 배포 | "두 파이썬 버전에서 돌려 호환성을 확인하고 리포트를 자동 배포합니다" |

---

## 4. 꼭 이해할 핵심 개념 5개

### ① fixture와 scope
- **fixture** = 테스트 전에 준비물을 만들어 주입하는 함수(`conftest.py`).
- `client`·`username`·`public_repo`·`write_repo`는 `scope="session"` → **전체 실행에서 1번만** 생성(HTTP 세션 재사용).
- `new_issue`·`created_label` 같은 건 scope 없음(기본 `function`) → **테스트마다 새로** 만들고 끝나면 정리.
- 💬 *"왜 session scope?"* → "매 테스트마다 HTTP 세션을 새로 열 필요가 없어서, 연결을 재사용하려고요."

### ② 마커(marker)로 테스트 슬라이스
- `@pytest.mark.write` → 실데이터를 바꾸는 테스트. `pytest -m "not write"`로 빼면 **토큰 없이 read-only만** 돈다.
- `smoke` → 핵심만 빠르게.
- 💬 *"토큰 없는 CI는 어떻게?"* → "`write_repo` fixture가 토큰을 검사해서 없으면 write 스위트 전체를 `pytest.skip`합니다. 그래서 read-only CI도 초록입니다."

### ③ `yield` teardown (생성물 정리)
- 쓰기 테스트는 실제 데이터를 만든다 → 끝나면 치워야 한다.
- fixture에서 `yield`로 값을 주고, 그 **뒤 코드가 teardown**(이슈 close, 라벨 delete).
- 이슈는 REST로 하드 삭제가 안 돼서 **close**로 정리, 라벨/코멘트/마일스톤은 **delete**.
- 💬 *"테스트가 중간에 실패하면 쓰레기가 남지 않나요?"* → "fixture teardown은 실패해도 실행돼서 정리됩니다."

### ④ negative 테스트 (거부 동작도 계약이다)
- 정상(200/201)뿐 아니라 **404**(없는 리소스), **422**(잘못된 입력)도 검증.
- `@pytest.mark.parametrize`로 잘못된 payload 여러 개를 한 테스트에서 표처럼 돌린다.
- 💬 *"왜 실패 케이스까지?"* → "API가 잘못된 요청을 제대로 거부하는지도 계약의 일부라서요."

### ⑤ CI + Allure
- push마다 `ci.yml`이 테스트를 돌리고, 결과를 Allure 리포트로 만들어 **gh-pages 브랜치 → GitHub Pages**로 배포.
- `if: always()`로 **테스트가 깨져도 리포트는 올린다**(실패했을 때 리포트가 가장 필요하니까).
- 💬 *"매트릭스는 왜?"* → "3.12·3.13 두 버전에서 돌려 호환성을 보장합니다."

---

## 5. 예상 질문 & 답변 (미리 연습)

**Q. 이 프로젝트 한 줄 소개?**
> GitHub REST API의 User/Repo/Issues/Labels/Milestones를 pytest로 검증한 계약 테스트 자동화입니다. 읽기뿐 아니라 쓰기 CRUD와 실패 케이스까지 보고, CI에서 Allure 리포트를 자동 배포합니다.

**Q. 가장 신경 쓴 부분은?**
> 상태코드 200만 확인하는 데 그치지 않고 **스키마 필드·타입·정합성**(요청한 값이 응답에 그대로 돌아오는지)까지 본 점, 그리고 **쓰기 테스트가 만든 데이터를 teardown으로 전부 정리**해 재실행해도 깨끗하게 만든 점입니다.

**Q. 쓰기 테스트가 실제 레포를 더럽히지 않나요?**
> 전용 **샌드박스 레포**(`qa-sandbox`)에서만 동작합니다. 토큰이 없거나 권한이 없으면 그 스위트를 통째로 skip합니다.

**Q. `/user/emails`에서 배운 것?** *(트러블슈팅 #1)*
> 인증이 필요한데도 토큰 스코프가 없으면 401이 아니라 **404**가 옵니다. 같은 엔드포인트가 스코프에 따라 다른 코드를 내서, 허용 코드에 추가하고 *이유를 주석으로* 남겼습니다.

**Q. 한계나 더 할 일은?**
> 실제 외부 API를 호출해서 rate limit·네트워크에 영향을 받습니다(그래서 타임아웃을 넣었습니다). 더 한다면 mock 기반 단위 레이어를 분리하는 방향이 있습니다.

> 더 깊은 사례는 [troubleshooting.md](troubleshooting.md)(실제 막힌 문제 9건)와 [code-review-log.md](code-review-log.md)(스스로 점검한 리뷰 라운드)에 있다 — 면접 전 한 번 훑어볼 것.

---

## 6. 직접 해보며 익히기

```bash
# 1) read-only만 (토큰 없이도 동작)
pytest -m "not write" -v

# 2) 한 파일만
pytest tests/test_repos.py -v

# 3) 쓰기까지 (.env에 repo 스코프 PAT 필요)
pytest -m write -v
```

**손에 익히는 연습 (작은 것부터):**
1. `tests/test_user.py`에 TC 하나 추가해 보기 — 예: `GET /users/{u}`의 `created_at` 필드 존재 확인. (fixture·assert 패턴 체득)
2. `tests/test_repos.py`에서 negative 하나 추가 — 없는 레포의 languages 조회가 404인지.
3. 추가한 TC를 `docs/TEST_CASES.md` 표에 한 줄 기록 → 명세와 코드가 같이 움직이는 감각 익히기.

> 목표는 "이 줄이 왜 있는지"를 막힘 없이 말할 수 있는 상태. 안 되는 부분이 있으면 그 파일만 다시 읽고, 여기 4장의 개념과 연결해 보면 된다.
