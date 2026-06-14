# GitHub REST API QA Automation

> GitHub REST API(api.github.com)의 User · Repository · Issues · Labels 엔드포인트를 **pytest + requests**로 검증한 REST API 계약(contract) 검증 포트폴리오
> — 총 **50 TC** · READ + **write-path(CRUD)** · GitHub Actions CI + Allure Pages 자동 배포

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
| **50 TC** (User 12·Repos 16·Issues 11·CRUD 11) | **47 passed · 3 skip · 0 fail** | 상태코드·스키마·정합성·**CRUD**·negative | **GitHub Actions** | **Allure Pages** |

**핵심 기능**

- **READ를 넘어선 write-path(CRUD) 검증** — 이슈·라벨을 실제로 **생성(201)·수정(200)·삭제(204)** 하고 read-back으로 정합성을 확인. 전용 **샌드박스 레포**에서만 동작하고 `yield` teardown으로 생성물을 전부 정리(이슈 close·라벨/코멘트 delete)
- **상태 코드를 넘어선 계약 검증** — `200`만 보는 데 그치지 않고 응답 **스키마 필드·데이터 타입·정합성**(`login`/`owner` 일치, repo `private:false` 보장)까지 검증
- **negative 케이스로 거부 동작까지** — 없는 user/repo/issue의 `404`, 잘못된 파라미터의 `422`, **필수값 누락·중복 라벨의 `422`** 까지 명시적으로 검증
- **실계정 공개 레포 자동 탐지** — `public_repo` fixture가 공개 레포를 API로 동적 조회 → 레포명 하드코딩 0
- **모든 HTTP 호출 Allure 자동 기록** — `GitHubAPIClient`가 매 요청을 `allure.step`으로 감싸 URL·Status·Body를 리포트에 자동 첨부

> 설계 의도·코드 레벨 상세는 **[주요 구현 5선 →](docs/implementation.md)**
> 📊 **Live Allure Report** → https://seonggwon21-tech.github.io/GitHub_API/ *(매 `main` push마다 trend 누적 갱신)*

---

## 기술 스택

| 분류 | 사용 기술 |
|---|---|
| 언어 · 프레임워크 | Python 3.12 · pytest 8 (fixture scope, `yield` teardown, marker 슬라이스) |
| HTTP 클라이언트 | requests (`Session` 재사용 — 헤더·연결 풀 일괄 관리) |
| API 검증 | 상태 코드 · 스키마 필드/타입 · 정합성 · 페이지네이션 · **CRUD write-path** · negative(404·422·인증 스코프) |
| 리포팅 | Allure (epic/feature/story/step 4계층 + HTTP 요청별 Status·Body 자동 첨부) |
| CI/CD | GitHub Actions — push·PR마다 테스트 → Allure Report → **GitHub Pages 자동 배포** |
| 환경 관리 | python-dotenv (`.env`로 PAT·사용자명 분리) · Postman 컬렉션(`postman/`) |

> 프로젝트 구조와 테스트 스위트 구성은 **[아키텍처 & 테스트 구성 →](docs/architecture.md)**

---

## 실행 방법

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경 변수 설정 (.env.example 복사 후 실제 값 입력)
cp .env.example .env
#   GITHUB_TOKEN=ghp_...   (read-only는 read:user / write-path는 repo 스코프 필요)
#   GITHUB_USERNAME=your_github_username
#   GITHUB_WRITE_REPO=qa-sandbox   (write-path 전용 샌드박스 — 없으면 자동 생성)

# 3. 테스트 실행
pytest                  # 전체 (50 TC)
pytest -m smoke         # 핵심 엔드포인트 5개만 빠르게
pytest -m write         # write-path CRUD 11개만 (repo 스코프 PAT 필요, 없으면 자동 skip)
pytest -m "not write"   # read-only만

# 4. Allure 리포트
allure serve allure-results
```

> PAT 없이도 공개 엔드포인트 테스트는 동작하며, 인증 전용 테스트(`/user` 등)와 write-path는 자동으로 skip됩니다.

---

## 상세 문서

| 문서 | 내용 |
|---|---|
| [아키텍처 & 테스트 구성](docs/architecture.md) | 프로젝트 구조, 테스트 스위트 구성, marker 슬라이스, Allure 4계층 구성 |
| [주요 구현 5선](docs/implementation.md) | API 클라이언트 추상화, 실계정 레포 자동 탐지, negative 케이스, CI 배포, write-path CRUD |
| [테스트 케이스 명세서](docs/TEST_CASES.md) | 50개 TC 전체 — 시나리오·입력·기대결과·심각도 |

---

## 프로젝트 배경 & 회고

> 본 레포는 UI 자동화 포트폴리오([helpy-chat-qa-automation](https://github.com/seonggwon21-tech/helpy-chat-qa-automation))와 별개로, **REST API 계약 검증** 역량을 따로 정리한 것입니다. 인증·다양한 응답 형태가 공개돼 있고 누구나 재현할 수 있는 GitHub REST API를 대상으로 골랐습니다.

**Claude AI를 적극 활용해** 설계·구현 전 과정을 진행했습니다. 다만 REST API 테스트는 **응답 자체가 계약(contract)** 이라는 점에 집중했습니다 — 상태 코드가 `200`인지 보는 것에 그치지 않고, 스키마 필드의 존재·데이터 타입·페이지네이션·negative 케이스까지 검증해야 비로소 "API가 올바르게 동작한다"고 말할 수 있다고 봤습니다.

가장 기억에 남는 건 `/user/emails`였습니다. 인증이 필요한 엔드포인트라 당연히 `401`을 예상했는데, 실제로는 **`404`** 가 돌아왔습니다. PAT에 `user:email` 스코프가 없으면 GitHub이 "권한 없음"이 아니라 "없는 리소스"로 응답하기 때문이었습니다. 허용 코드에 `404`를 그냥 추가하는 대신, *왜 이런 코드가 나오는지*를 주석으로 남겨 다음 사람이 이해할 수 있게 했습니다.

<details>
<summary>API 테스트를 만들며 세운 원칙</summary>

- **상태 코드는 시작일 뿐** — 스키마 필드·타입·정합성까지 봐야 계약 검증
- **거부 동작도 기능이다** — 404·422·인증 실패를 정상 케이스만큼 명시적으로 검증
- **하드코딩을 줄인다** — 공개 레포를 fixture가 동적 탐지해 어떤 계정에서도 동작
- **리포트는 실패할 때 가장 필요하다** — 테스트가 깨져도 Allure를 배포하고, 매 호출을 step으로 추적 가능하게

</details>
