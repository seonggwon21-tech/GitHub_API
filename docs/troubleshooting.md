# 트러블슈팅

> 자동화를 구축·실행하며 실제로 막혔던 문제와 그 해결 과정입니다.
> 증상이 없는데 리뷰로 찾은 잠재 결함은 [코드 리뷰 로그](code-review-log.md)에 따로 정리합니다.

---

## 1. `/user/emails`가 `401`이 아니라 `404`를 반환

**증상** — 인증이 필요한 엔드포인트라 토큰 없을 때 `401`을 예상했는데 실제로는 `404`가 돌아왔다.

**원인** — PAT에 `user:email` 스코프가 없으면 GitHub은 "권한 없음(401/403)"이 아니라 **"없는 리소스(404)"** 로 응답한다. 같은 엔드포인트가 토큰 스코프에 따라 다른 상태 코드를 낸다.

**해결** — 허용 코드를 `(200, 401, 403, 404)`로 두되, *왜 404가 나오는지*를 주석으로 남겨 다음 사람이 오해하지 않게 했다.

```python
# 200: authed with user:email scope, 401/403: no token, 404: token lacks user:email scope
assert response.status_code in (200, 401, 403, 404)
```

---

## 2. 레포 목록 `type=public` 파라미터가 동작하지 않음

**증상** — 공개 레포만 받으려고 `params={"type": "public"}`을 넣었는데 의도대로 동작하지 않았다.

**원인** — `/users/{username}/repos`의 `type`은 **`all` / `owner` / `member`** 만 받는다. `public`은 유효값이 아니다. (애초에 이 엔드포인트는 private을 반환하지 않으므로 공개 여부 필터는 불필요했다.)

**해결** — `type=owner`로 교정하고, "이 엔드포인트는 private을 반환하지 않는다"는 보장을 테스트로 검증하는 방향으로 정리했다. (`809ecf2`)

---

## 3. Allure가 JSON이 아닌 응답 본문에서 파싱 실패

**증상** — 에러 HTML·rate-limit 페이지·빈 응답이 돌아온 요청에서 Allure 첨부가 깨졌다.

**원인** — 모든 응답 본문을 `attachment_type.JSON`으로 첨부하다 보니, JSON이 아닌 본문을 Allure가 파싱하려다 실패했다.

**해결** — 응답 `Content-Type`을 확인해 **JSON일 때만 JSON으로, 그 외에는 TEXT로** 첨부하도록 `_attach()`를 분기했다. (`809ecf2`)

```python
attachment_type = (
    allure.attachment_type.JSON
    if "json" in content_type.lower()
    else allure.attachment_type.TEXT
)
```

---

## 4. 응답을 곧바로 인덱싱하다 비정상 응답에서 크래시

**증상** — 일부 테스트가 `response.json()[0]` / `["field"]`를 바로 접근해, 응답이 비었거나 에러(dict)일 때 `KeyError`·`IndexError`로 죽었다.

**원인** — 상태 코드 확인 없이 본문 구조를 가정했다. rate-limit(403)이나 빈 목록이면 가정이 깨진다.

**해결** — 인덱싱 전에 `status_code`를 단언하거나, 빈 목록이면 `pytest.skip()`으로 건너뛰도록 가드를 넣었다. 더불어 무의미하게 항상 참이던 email 단언은 실제 검증(타입·존재)으로 교체했다. (`809ecf2`)

---

## 5. CI에서 토큰이 주입되지 않음 — `GITHUB_TOKEN` 이름 충돌

**증상** — Secrets에 `GITHUB_TOKEN`을 등록하려 했으나 설정되지 않았고, 워크플로에서 PAT가 비어 인증 테스트가 전부 skip됐다.

**원인** — `GITHUB_TOKEN`은 GitHub Actions가 **잡마다 자동 발급하는 예약어**라 Secrets로 직접 덮어쓸 수 없다.

**해결** — PAT는 `GH_API_TOKEN`이라는 별도 이름으로 등록하고, 워크플로에서 환경변수 `GITHUB_TOKEN`에 매핑했다. Pages 배포에는 내장 `GITHUB_TOKEN`을 그대로 쓴다.

```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GH_API_TOKEN }}   # PAT (별도 이름)
...
github_token: ${{ secrets.GITHUB_TOKEN }}     # 배포용 내장 토큰
```

---

## 6. 테스트가 실패하면 Allure 리포트가 배포되지 않음

**증상** — 테스트가 깨진 빌드에서 리포트가 올라오지 않아, 정작 원인을 봐야 할 때 리포트가 없었다.

**원인** — 기본 동작상 앞 스텝(테스트)이 실패하면 이후 잡이 실행되지 않는다.

**해결** — 결과 업로드와 report 잡에 `if: always()`를 걸어, **테스트가 실패해도 리포트는 배포**하도록 했다. 실패했을 때야말로 리포트가 가장 필요하기 때문이다.

---

## 7. 빌드 간 Allure trend가 누적되지 않음

**증상** — 매 빌드 리포트가 단발성이라 과거 결과와 비교되는 trend 그래프가 비어 있었다.

**원인** — Allure trend는 이전 실행의 `history/`가 결과 폴더에 함께 있어야 누적된다. 새 빌드는 빈 결과만 생성한다.

**해결** — `gh-pages`의 `history/`를 내려받아 새 결과에 복사한 뒤 리포트를 생성하도록 했다. 첫 실행처럼 `gh-pages`가 아직 없을 때는 `continue-on-error`로 무시하고 진행한다.

```yaml
- name: Copy history for trend graph
  continue-on-error: true
  run: cp -r gh-pages/history allure-results/history
```

---

## 8. write-path 테스트가 토큰 없는 환경에서 실패

**증상** — `repo` 스코프 PAT가 없는 환경(로컬·CI)에서 CRUD 테스트가 인증 실패로 깨졌다.

**원인** — 쓰기 테스트는 실데이터를 변경하므로 권한이 필요한데, read-only 환경에서도 무조건 실행됐다.

**해결** — `write_repo` fixture가 토큰·push 권한을 사전 점검해, 없으면 `pytest.skip()`으로 **write 스위트 전체를 건너뛴다.** 토큰 없는 환경에서도 read-only 테스트는 그대로 통과한다.
