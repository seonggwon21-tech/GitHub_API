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
| 2 | `public_repo` fixture가 정렬상 첫 레포를 그대로 선택 → 그 레포의 Issues가 비활성/fork면 `GET .../issues`가 `410`을 반환해 issue 테스트가 false-fail | Medium | 보류 | — |
| 3 | `test_comment_create_then_delete`의 코멘트가 fixture가 아닌 본문에서 생성돼, 중간 단언 실패 시 샌드박스에 코멘트가 남음 | Low | 보류 | — |

### 처리 판단

- **#1 (수정)** — 외부 API(`api.github.com`)에 의존하는 스위트에서 timeout 누락은 가장 실질적인 리스크였다. 연결 단절·프록시 hang 시 GitHub Actions 잡이 잡 타임아웃까지 매달린다. 세션 공통 상수로 빼 네 메서드에 일괄 적용했다.
- **#2 (보류)** — 계정·정렬 상태에 따라 갈리는 환경 의존 취약성이다. 현재 테스트 계정에서는 재현되지 않으며, 근본 해결은 `has_issues=true` 필터나 대상 레포 명시가 필요하다. 재현되거나 대상 계정이 바뀔 때 다루기로 했다.
- **#3 (보류)** — 영향이 private 샌드박스로 한정되고, 같은 이슈가 `new_issue` teardown에서 닫히므로 누수 비용이 작다. 클린업 일관성 차원에서 코멘트도 fixture로 빼는 개선 여지는 인지하고 남겨 둔다.

> 점검 기준선: 50 TC / 47 passed · 3 skipped · 0 failed (read-only 환경).
