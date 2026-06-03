# 아키텍처 스냅샷

현재 시점의 voice-craft 구조. 결정의 *이유*는 인라인 ADR 링크를 따라간다 → [decisions.md](decisions.md).

## 전체 흐름

```
[키 누름 (PTT)]
  ↓
[마이크 녹음]
  ↓
[faster-whisper STT]
  ↓
[키워드 딕셔너리 NLU]
  ↓
[JSON 한 줄] → TCP localhost:5000 → [C++ BWAPI 봇]
                                       ↓
                                   [BWAPI: barracks.train(Marine)]
                                       ↓
                                   [게임 화면에 마린 등장]
```

두 개 프로세스 + IPC 구조.


## 실행 환경

-   호스트: Arch Linux 단일 머신 ([ADR-001](decisions.md#adr-001)).
-   게임: BW 1.16.1 + Classic BWAPI, Wine 위에서 실행 ([ADR-001](decisions.md#adr-001)).
-   봇 주입: Chaoslauncher의 BWAPI Injector 플러그인 ([ADR-002](decisions.md#adr-002)).


## 게임 측 (C++ 봇)

-   **형태**: BWAPI `AIModule`을 상속한 32-bit Windows DLL. `bwapi-data/AI/`에 배치.
-   **역할**: TCP로 받은 JSON 명령을 BWAPI 호출로 변환하는 얇은 레이어. 자체 의사결정 없음.
-   **빌드**: MinGW-w64 크로스컴파일, CMake + 직접 작성한 toolchain 파일, `-std=c++17` ([ADR-003](decisions.md#adr-003)).
-   **JSON 파싱**: nlohmann/json single-header, `bot/third_party/`에 vendoring ([ADR-008](decisions.md#adr-008)).

### 명령 실행 시맨틱스

`{"cmd":"produce_marine"}` → `Broodwar->self()->getUnits()`에서 완성된 Terran Barracks 중 `getTrainingQueue().size()`가 가장 작은 것을 선택, `< 5`이면 `train(UnitTypes::Terran_Marine)` 호출. 매 호출 후 `Broodwar->getLastError()` 로깅 ([ADR-006](decisions.md#adr-006)).


## 음성 측 (Python)

MVP-B에서 본격적으로 정의. 현재 확정된 항목:

-   **트리거**: 푸시-투-토크.
-   **STT**: faster-whisper (로컬).
-   **NLU**: 키워드 딕셔너리 + 부분일치 스캔.

세부 (모델 크기, PTT 키, 마이크 캡처 라이브러리 등)는 MVP-A 완료 후 grilling으로 확정.


## IPC

-   **전송**: TCP, `localhost:5000`.
-   **인코딩**: JSON lines (`\n` delimited). 예: `{"cmd":"produce_marine"}\n`.
-   **역할**:
    -   Python = **서버**, 여러 매치 동안 살아남음.
    -   C++ 봇 = **클라이언트**, 매치 시작 시마다 새로 연결.
    -   이유: BWAPI는 매치 종료 시 `AIModule`을 폐기하므로 봇이 서버일 경우 listener가 매번 죽는다 ([ADR-004](decisions.md#adr-004)).
-   **봇 측 I/O**: 비차단 소켓을 `onFrame`에서 폴링, 영구 라인 버퍼에 누적, `\n` 만날 때마다 한 명령 파싱·실행 ([ADR-005](decisions.md#adr-005)).
-   **연결 복구**: 봇은 첫 진입 시점부터 재연결 로직 포함 (N 프레임마다 재시도) ([ADR-004](decisions.md#adr-004)).

### MVP-A에서의 임시 서버

Python 서비스가 존재하기 전에는 `nc -l -k 5000`이 서버 역할을 대신한다. 운영자가 nc stdin에 JSON 한 줄을 입력 → 봇이 수신·실행. `-k`로 매치 재시작에도 nc 세션이 유지된다.


## 테스트 맵

-   ScmDraft 2로 직접 제작 ([ADR-007](decisions.md#adr-007)).
-   내용: Player 1 테란 시작 위치, Player 1 소유 Terran Barracks 1기 사전 배치, 시작 미네랄 1000+, 서플라이 여유, 트리거 없음.
-   배치되는 배럭의 **소유자가 봇이 점유하는 슬롯(Player 1)**과 일치해야 한다. 불일치 시 `getUnits()` 결과가 비어 `produce_marine`이 조용히 실패한다.


## 저장소 구조

```
voice-craft/
├── AGENTS.md
├── docs/
│   ├── architecture.md   (이 파일)
│   ├── decisions.md
│   └── runbook.md
├── bot/                  # C++ BWAPI 봇
│   ├── CMakeLists.txt
│   ├── cmake/mingw-w64-toolchain.cmake
│   ├── src/
│   ├── include/
│   └── third_party/nlohmann/json.hpp
└── voice/                # Python 음성 서비스 (MVP-B에서 채움)
```

최상위 컴포넌트 디렉터리 + 컴포넌트 내부의 자체 `src/` ([ADR-009](decisions.md#adr-009)).
