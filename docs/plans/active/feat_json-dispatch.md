# A5 — JSON 디스패치 → SCV 생산 (MVP-A 완료)

worktree `feat_json-dispatch`. A4(비차단 TCP 라인 echo)에 이어, 봇이 들어온 라인을 JSON으로 파싱해 `produce_scv` 명령을 BWAPI `train()` 호출로 디스패치한다. 이 단계로 "JSON 한 줄 → BWAPI 생산 호출" 경로가 닫히고 **MVP-A가 완료**된다.

## 범위

-   **포함**:
    -   nlohmann/json single-header vendoring ([ADR-008](../../decisions.md#adr-008)).
    -   A4의 `on_line` echo 콜백 자리에 JSON 파싱 + 명령 디스패치를 끼워 넣음. 모듈 인터페이스(`VoiceClient::poll`) 변경 없음.
    -   `produce_scv` 핸들러: 가장 한가한 idle Command Center에서 `train(Terran_SCV)` ([ADR-006](../../decisions.md#adr-006)).
    -   파싱 실패·미지 명령은 로깅 후 라인 드롭, 봇 크래시 금지.
-   **불포함 (이후)**: 음성 경로(MVP-B), 추가 명령어, 실제 통제 맵. 스톡 melee CC를 그대로 harness로 씀 ([ADR-007](../../decisions.md#adr-007)).

근거 ADR: [ADR-008](../../decisions.md#adr-008) (nlohmann vendoring), [ADR-006](../../decisions.md#adr-006) (`produce_scv` = least-loaded idle CC + train + getLastError 로깅), [ADR-007](../../decisions.md#adr-007) (스톡 melee 맵, 별도 제작 없음).

## 프로토콜

-   인코딩: JSON lines, `\n` delimited ([architecture.md IPC](../../architecture.md)).
-   A5 명령: `{"cmd":"produce_scv"}\n`.
-   `cmd` 필드로 디스패치. 다른 값·필드 누락·파싱 에러 → 경고 로그 후 드롭.

## A5 통과 조건

1.  `nc -l -k 5000` listen 중, 봇 connect (A4 유지).
2.  `nc`에 `{"cmd":"produce_scv"}` 입력 → 봇이 파싱, idle CC에서 `train(Terran_SCV)` 호출, `getLastError()` 로그 출력.
3.  게임에서 SCV 훈련 시작 확인 (CC progress bar / 서플라이 카운트 증가).
4.  잘못된 JSON(`{not json`) 입력 → 봇이 죽지 않고 경고 로그 후 다음 라인 정상 처리.
5.  미지 명령(`{"cmd":"foo"}`) → 봇이 죽지 않고 "unknown cmd" 로그.
6.  미네랄·서플라이·큐 부족 시 `train()` 조용히 실패 → `getLastError()` 로그로 이유 노출 ([ADR-006] consequences).

## 설계 결정

### `on_line` 콜백에 파싱·디스패치 삽입

A4가 의도적으로 비워 둔 자리. `VoiceClient`는 라인 전달만 담당하고 (소켓·버퍼 책임), JSON·BWAPI 지식은 main 쪽 콜백에 둔다 — 소켓 모듈이 게임 API에 의존하지 않게 분리 유지.

-   `on_line = [](const std::string& line){ dispatch(line); }`.
-   `dispatch()`는 BWAPI(`Broodwar`)를 캡처하거나 main.cpp 안 free function.

### 디스패치 위치: main.cpp vs 별도 모듈

A5 명령은 `produce_scv` 하나뿐. 단일 명령에 별도 모듈/추상화는 [CLAUDE.md "Simplicity First"]에 어긋남 → main.cpp 안 함수로 시작. 명령이 둘 이상 생기는 시점(MVP-B 등)에 분리 검토. (A4가 TCP를 분리한 것과 대비: TCP는 소켓 수명·재연결로 main과 책임이 명확히 달랐다.)

### `produce_scv` 로직 ([ADR-006])

-   `Broodwar->self()->getUnits()`에서 완성된 Terran Command Center 필터.
-   `getTrainingQueue().size()` 최소인 것 선택, `< 5`이면 `train(UnitTypes::Terran_SCV)`.
-   호출 직후 `Broodwar->getLastError()` 로깅 (실패 원인 노출).
-   MVP(CC 1기)에선 least-loaded tiebreaker가 no-op이지만 건물 수가 늘어도 코드 변경 없이 동작.

### 에러 처리 ([ADR-008] consequences)

-   `nlohmann::json::parse`를 try/catch. 파싱 실패 → 경고 로그 + 라인 드롭.
-   `cmd` 미존재 / 미지 값 → "unknown cmd" 로그 + 드롭.
-   어떤 경우에도 throw가 프레임 루프 밖으로 나가지 않게 (봇 크래시 금지).

### vendoring ([ADR-008])

-   `bot/third_party/nlohmann/json.hpp` 단일 파일. 패키지 매니저·링크 없음.
-   `-std=c++17` (이미 MinGW-w64 설정), include path에 `bot/third_party` 추가.

## 빌드 / 검증

-   `bot/third_party/nlohmann/json.hpp` 추가, `bot/CMakeLists.txt` include 디렉터리 반영 (소스 파일은 main.cpp 그대로 — header-only).
-   `mise run bot-build` → `bot/build/voice-craft-bot.exe`.
-   검증 (runbook MVP-A 절차):
    1.  `nc -l -k 5000`.
    2.  `mise run bw-bwapi` → single-player 테란 melee 매치.
    3.  `mise run bot-run` → connect 로그.
    4.  `nc`에 `{"cmd":"produce_scv"}` → SCV 훈련 시작 + getLastError 로그.
    5.  잘못된 JSON / 미지 명령 → 크래시 없이 로그.

## 미결 / 이후

-   `enableFlag(UserInput)`은 A4 테스트 편의 — MVP-A 완료 시점(=이 단계)에 제거 검토.
-   MVP-A 완료 후 별도 grilling 세션으로 MVP-B(음성 경로) 확정 ([AGENTS.md](../../../AGENTS.md)).

## 결과 (완료 기록)

-   (완료 후 기입: 실제 구현 결정, 빌드 이슈, 통과 조건 검증 결과)
