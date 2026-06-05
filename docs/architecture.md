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
[JSON 한 줄] → TCP localhost:5000 → [C++ BWAPI 봇 (.exe)]
                                       ↕ shared memory
                                   [StarCraft.exe + 주입된 BWAPI.dll]
                                       ↓
                                   [BWAPI: barracks.train(Marine)]
                                       ↓
                                   [게임 화면에 마린 등장]
```

세 개 프로세스: ① StarCraft(주입된 BWAPI.dll = 서버), ② C++ 봇 .exe (BWAPI Client + Python TCP 클라이언트), ③ Python 음성 서비스. 봇은 BWAPI와는 shared memory로, Python과는 TCP로 통신한다 ([ADR-014](decisions.md#adr-014)).


## 실행 환경

-   호스트: Arch Linux 단일 머신 ([ADR-001](decisions.md#adr-001)).
-   게임: BW 1.16.1 + Classic BWAPI, Wine 위에서 실행 ([ADR-001](decisions.md#adr-001)).
-   BWAPI 주입: injectory CLI로 BWAPI.dll + WMode.dll을 StarCraft.exe에 주입 ([ADR-012](decisions.md#adr-012)). bwapi.ini의 `ai =`는 비워둔다 — 봇은 DLL로 주입되지 않고 별도 .exe로 실행되기 때문 ([ADR-014](decisions.md#adr-014)).
-   봇 실행: 봇 .exe를 **게임과 같은 Wine prefix**에서 별도 실행 → 주입된 BWAPI.dll과 shared memory로 연결 ([ADR-014](decisions.md#adr-014)).


## 게임 측 (C++ 봇)

-   **형태**: BWAPI **Client API** 기반 32-bit Windows **실행파일(.exe)**. 주입된 BWAPI.dll과 shared memory로 통신하는 독립 프로세스 ([ADR-014](decisions.md#adr-014)). `AIModule` DLL이 아니다.
-   **역할**: TCP로 받은 JSON 명령을 BWAPI 호출로 변환하는 얇은 레이어. 자체 의사결정 없음.
-   **메인 루프**: `BWAPIClient.connect()` 후 `update()`로 프레임을 진행시키며, 매 `update()` 직후 Python 소켓을 폴링한다 (onFrame 콜백 없음, [ADR-005](decisions.md#adr-005) Note).
-   **빌드**: MinGW-w64 크로스컴파일, Docker 컨테이너(Debian + g++-mingw-w64-i686 + cmake), `-std=c++17`. 호스트에 MinGW 미설치 ([ADR-014](decisions.md#adr-014)).
-   **BWAPI Client 라이브러리**: prebuilt가 없어 BWAPI 4.4.0 소스를 `bot/third_party/bwapi/`에 vendoring해 봇과 함께 빌드. MinGW 호환 패치 + `<Windows.h>` shim + `svnrev.h` stub 포함 ([ADR-014](decisions.md#adr-014)).
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
    -   이유: Python을 서버로 두면 매치 사이에 STT 모델이 메모리에 유지된다. 봇은 매치마다 BWAPI(게임)에 재연결하는데, 봇이 Python 서버이기도 하면 그 listener가 매 매치 죽어 Python의 재연결이 복잡해진다 ([ADR-004](decisions.md#adr-004)).
-   **봇 측 I/O**: 비차단 소켓을 메인 루프(매 `BWAPIClient.update()` 직후)에서 폴링, 영구 라인 버퍼에 누적, `\n` 만날 때마다 한 명령 파싱·실행 ([ADR-005](decisions.md#adr-005)).
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
├── bot/                  # C++ BWAPI 봇 (.exe)
│   ├── Dockerfile        # MinGW 크로스컴파일 환경
│   ├── CMakeLists.txt
│   ├── cmake/mingw-w64-toolchain.cmake
│   ├── src/
│   └── third_party/
│       ├── nlohmann/json.hpp
│       └── bwapi/        # vendored BWAPI 4.4.0 Client 소스 + 패치
│           ├── include/  (헤더)
│           ├── BWAPIClient/ Util/ Storm/ Shared/ BWAPILIB/  (Client lib 소스)
│           ├── shim/Windows.h   (MinGW 소문자 헤더명 리다이렉트)
│           └── svnrev.h         (Windows cscript 생성 단계 stub)
└── voice/                # Python 음성 서비스 (MVP-B에서 채움)
```

최상위 컴포넌트 디렉터리 + 컴포넌트 내부의 자체 `src/` ([ADR-009](decisions.md#adr-009)).
