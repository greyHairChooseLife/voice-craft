# 프로젝트 개요

스타크래프트: 브루드워를 **음성 명령만으로** 플레이할 수 있게 하는 도구.


## MVP

단일 명령 "SCV 생산" → 스톡 melee 시작 Command Center에서 SCV 1기 생산.

두 단계로 나눠 진행한다. 자세한 정의는 [docs/architecture.md](docs/architecture.md), 실행 절차는 [docs/runbook.md](docs/runbook.md).

-   **MVP-A**: C++ 봇 + `nc`로 JSON 수동 주입 → SCV 등장.
-   **MVP-B**: 전체 음성 경로 (PTT → STT → NLU → JSON → 봇) → SCV 등장.


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

- [x]   A1. Wine + BW 실행 확인 (메인 메뉴 도달) - `chore_wine-and-BW`
- [x]   A2. injectory로 BWAPI 인젝션 검증 (봇 없이 주입·실행, ADR-013) - `chore_wine-and-BW`
- [x]   A3. MinGW(Docker) + BWAPI Client API 봇 .exe (게임 채팅에 "hello" 출력, ADR-014) - `chore_bot-boilerplate`
- [x]   A4. 비차단 TCP 클라이언트 + 라인 버퍼 (nc 입력이 봇 화면에 에코) - `feat_non-block-tcp-client-reading-receive-buffer`
- [x]   A5. JSON 디스패치 → SCV 생산 (스톡 melee CC에서 train, ADR-006/007/008) - `feat_json-dispatch` (**MVP-A 완료**)

#### clone 후 MVP-A 검증

clone 직후 MVP-A를 처음 돌려보는 흐름. 상세 명령·통과 조건·디버깅은 [runbook](docs/runbook.md)에 있다 (여긴 포인터만).

1.  **1회성 환경 구축**: runbook [사전 준비](docs/runbook.md#사전-준비-1회성)의 A1~A4 — BW 다운로드, Wine/시스템 셋업, 봇 .exe 빌드까지.
2.  **반복 실행**: runbook [MVP-A 실행 절차 — A5](docs/runbook.md#mvp-a-실행-절차-반복--a5).
    -   `nc -l -k 5000` (명령 서버 대기) → `mise run bw-bwapi` (게임+주입, 테란 melee 진입) → `mise run bot-run` (봇).
    -   `nc`에 `{"cmd":"produce_scv"}` 입력 → CC가 SCV 1기 생산.
-   MVP-A엔 음성·미디어 캡처가 없다 — JSON은 `nc` stdin으로 수동 주입. 음성 경로는 MVP-B.

### MVP-B — 음성 경로

영어 전용. Python 음성 서비스가 :5000 서버가 되어 `nc`를 은퇴시킨다 ([ADR-015](docs/decisions.md#adr-015)~[ADR-019](docs/decisions.md#adr-019)). 설계 확정은 grilling 세션 (architecture.md 음성 측 / runbook MVP-B 절차 참조).

- [ ]   B1. `voice/` 패키지 스캐폴드 + asyncio TCP 서버 (:5000, 봇 connect/echo 검증, `nc` 대체, ADR-019)
- [ ]   B2. PTT 캡처 — F12 전역 핫키 + 마이크 녹음 (누른 동안 녹음 → numpy 버퍼, ADR-016)
- [ ]   B3. faster-whisper STT — `base.en` cpu/int8, 버퍼 → 텍스트 콘솔 출력 (ADR-017)
- [ ]   B4. 키워드 NLU — 동사+scv → `produce_scv` JSON, 무매칭 드롭 (ADR-018)
- [ ]   B5. 전체 경로 결선 — 워커 스레드→asyncio 브리지, 음성만으로 SCV 생산 (**MVP-B 완료**, ADR-015)

#### MVP-B 검증

음성만으로 SCV 등장. 상세 명령·통과 조건·디버깅은 [runbook MVP-B 절차](docs/runbook.md#mvp-b-실행-절차-음성-경로)에 있다 (여긴 포인터만).

1.  **1회성**: `mise run voice-setup` (Python 의존성 — pynput/sounddevice/numpy/faster-whisper). X11 세션 필요.
2.  **반복 실행**: `mise run voice` (서버+모델+PTT) → `mise run bw-bwapi` (테란 melee) → `mise run bot-run` (봇).
    -   **F12 누른 채** "produce SCV" 말하고 놓기 → CC가 SCV 1기 생산.
-   키보드 JSON 입력 없음 — 전부 음성. 진단은 음성 콘솔 로그 스트림으로 한다.
