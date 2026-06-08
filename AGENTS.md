# 프로젝트 개요

스타크래프트: 브루드워를 **음성 명령만으로** 플레이할 수 있게 하는 도구.

지금까지의 진행과 앞으로의 계획은 [docs/roadmap.md](docs/roadmap.md), 실제 작업 기록(source of truth)은 [CHANGELOG.md](CHANGELOG.md), 한 번 돌려보려면 [docs/runbook.md](docs/runbook.md).


## 문서 구조

-   [`docs/roadmap.md`](docs/roadmap.md) — **장기 계획**. "어디로 가는가?" 마일스톤 단위. 완료·진행·예정 상태와 잠정 체크리스트.
-   [`CHANGELOG.md`](CHANGELOG.md) — **나간 것 기록**. "최근 뭐가 바뀌었나?" 워크트리 단위, 최신이 위.
-   [`docs/architecture.md`](docs/architecture.md) — **현재 구조 스냅샷**. "지금 어떻게 생겼나?" 각 결정 옆에 `[ADR-NNN](decisions.md#adr-nnn)` 인라인 링크.
-   [`docs/decisions.md`](docs/decisions.md) — **ADR 로그**. "왜 이렇게 했나?" architecture.md에서 링크됨. 각 ADR에 Status 필드 (Accepted / Superseded by ADR-NNN / Rejected).
-   [`docs/runbook.md`](docs/runbook.md) — **실행 절차**. "지금 한 번 돌려보고 싶다" 할 때. 환경 설정, 빌드, 실행, 디버깅 명령어.
-   [`docs/plans/active/`](docs/plans/active/) — **현재 워크트리의 상세 플랜**. 완료 시 [`docs/plans/done/`](docs/plans/done/)로 이동.


### 문서 유지 규칙

#### Anytime at

1.  **새 결정**: `decisions.md`에 ADR 추가 → `architecture.md`의 해당 부분 갱신 + ADR 링크 추가.
2.  **기존 결정 변경**: 옛 ADR을 `Status: Superseded by ADR-NNN`으로 표기 → 새 ADR 추가 (삭제하지 않음) → `architecture.md` 갱신.
3.  **새 실행 절차 / 단축키 / 설정 변경**: `runbook.md` 즉시 갱신.

#### On checkpoint(git worktree) completed

1.  `docs/plans/active/<worktree>.md` → `docs/plans/done/`로 이동.
2.  `roadmap.md` — 해당 하위 단계 `[x]` (취소·대체된 단계는 `[c]` + 이유). 마일스톤이 끝났으면 배지 갱신.
3.  `CHANGELOG.md` — 워크트리 단위 항목 추가 (최신이 위, 브랜치명 + ADR).
4.  구조·결정이 바뀌었으면 위 "작업 중" 규칙대로 `architecture.md`/`decisions.md` 갱신.

새 정보를 어디에 적을지 모를 때는: **사실/스냅샷 → architecture.md**, **이유 → decisions.md**, **명령어/조작 → runbook.md**, **계획 → roadmap.md**, **구현된 것 → CHANGELOG.md**.


## 에이전트 실행 규칙

-   **Docker 명령 (`docker`, `docker compose` 등)과 mise 태스크 (`mise run ...`)는 에이전트가 직접 실행하지 않는다.**
-   해당 명령이 필요하면 실행하지 말고, 사용자에게 실행할 명령을 알려주고 직접 돌려달라고 요청한다.
-   사용자가 결과를 붙여넣어 주면 그걸 바탕으로 작업을 이어간다.
