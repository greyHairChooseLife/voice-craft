# 프로젝트 개요

스타크래프트: 브루드워를 **음성 명령만으로** 플레이할 수 있게 하는 도구.


## MVP

단일 명령 "마린 생산" → 사전 배치된 배럭에서 마린 1기 생산.

두 단계로 나눠 진행한다. 자세한 정의는 [docs/architecture.md](docs/architecture.md), 실행 절차는 [docs/runbook.md](docs/runbook.md).

-   **MVP-A**: C++ 봇 + `nc`로 JSON 수동 주입 → 마린 등장.
-   **MVP-B**: 전체 음성 경로 (PTT → STT → NLU → JSON → 봇) → 마린 등장.


## 문서 구조

-   [`docs/architecture.md`](docs/architecture.md) — **현재 구조 스냅샷**. "지금 어떻게 생겼나?" 알고 싶을 때. 각 결정 옆에 `[ADR-NNN](decisions.md#adr-nnn)` 인라인 링크.
-   [`docs/decisions.md`](docs/decisions.md) — **ADR 로그**. "왜 이렇게 했나?" 알고 싶을 때. architecture.md에서 링크됨. 각 ADR에 Status 필드 (Accepted / Superseded by ADR-NNN / Rejected).
-   [`docs/runbook.md`](docs/runbook.md) — **실행 절차**. "지금 한 번 돌려보고 싶다" 할 때. 환경 설정, 빌드, 실행, 디버깅 명령어.


## 문서 유지 규칙

작업 시 아래 순서를 따른다.

1.  **새 결정**: `decisions.md`에 ADR 추가 → `architecture.md`의 해당 부분 갱신 + ADR 링크 추가.
2.  **기존 결정 변경**: 옛 ADR을 `Status: Superseded by ADR-NNN`으로 표기 → 새 ADR 추가 (삭제하지 않음) → `architecture.md` 갱신.
3.  **새 실행 절차 / 단축키 / 설정 변경**: `runbook.md` 즉시 갱신.
4.  **체크포인트 완료**: 이 파일의 체크박스 갱신.

새 정보를 어디에 적을지 모를 때는: **사실/스냅샷 → architecture.md**, **이유 → decisions.md**, **명령어/조작 → runbook.md**.


## 에이전트 실행 규칙

-   **Docker 명령 (`docker`, `docker compose` 등)과 mise 태스크 (`mise run ...`)는 에이전트가 직접 실행하지 않는다.**
-   해당 명령이 필요하면 실행하지 말고, 사용자에게 실행할 명령을 알려주고 직접 돌려달라고 요청한다.
-   사용자가 결과를 붙여넣어 주면 그걸 바탕으로 작업을 이어간다.


## 개발 일정

### MVP-A — 봇 + nc

-   [x] A1. Wine + BW 실행 확인 (메인 메뉴 도달) - `chore_wine-and-BW`
-   [x] A2. injectory로 BWAPI 인젝션 검증 (봇 없이 주입·실행, ADR-013) - `chore_wine-and-BW`
-   [x] A3. MinGW(Docker) + BWAPI Client API 봇 .exe (게임 채팅에 "hello" 출력, ADR-014) - `chore_bot-boilerplate`
-   [ ] A4. 테스트 맵 (ScmDraft 2, 배럭 소유자 확인)
-   [ ] A5. 비차단 TCP 클라이언트 + 라인 버퍼 (nc 입력이 봇 화면에 에코)
-   [ ] A6. JSON 디스패치 → 마린 생산 (**MVP-A 완료**)

### MVP-B — 음성 경로

MVP-A 완료 후 별도 grilling 세션으로 확정한다. PTT 방식, faster-whisper 모델 크기, NLU 키워드 구조, 마이크 캡처 라이브러리 등을 그때 정한다.
