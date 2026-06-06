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
                                   [BWAPI: commandcenter.train(SCV)]
                                       ↓
                                   [게임 화면에 SCV 등장]
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

`{"cmd":"produce_scv"}` → `Broodwar->self()->getUnits()`에서 완성된 Terran Command Center 중 `getTrainingQueue().size()`가 가장 작은 것을 선택, `< 5`이면 `train(UnitTypes::Terran_SCV)` 호출. 매 호출 후 `Broodwar->getLastError()` 로깅 ([ADR-006](decisions.md#adr-006)).


## 음성 측 (Python)

MVP-B의 `voice/` 서비스. 영어 전용 음성 인식(접근성 확장은 나중).

-   **동시성**: 단일 프로세스 2-스레드 ([ADR-015](decisions.md#adr-015)). 메인 스레드 = asyncio TCP 서버(:5000) + whisper 모델 상주, 워커 스레드 = PTT + 마이크 + STT + NLU. 워커→메인은 `loop.call_soon_threadsafe`로 JSON 라인 전달.
-   **트리거 (PTT)**: F12, 누른 동안만 녹음, `pynput` X11 전역 핫키 ([ADR-016](decisions.md#adr-016)). F12 down → 마이크 시작, F12 up → 정지 후 전사.
-   **마이크 캡처**: `sounddevice`(PortAudio), 시스템 기본 입력 장치, mono 16 kHz, 콜백 청크를 `numpy` `float32` 배열로 연결 → whisper에 직접. 디스크 없음 ([ADR-016](decisions.md#adr-016)).
-   **STT**: faster-whisper `base.en`, `device="cpu"`, `compute_type="int8"`, `language="en"`. 시작 시 1회 로드(콜드 스타트 없음) ([ADR-017](decisions.md#adr-017)).
-   **NLU**: `(동사 집합, 명사 집합, 명령)` 규칙 리스트 ([ADR-018](decisions.md#adr-018)). 정규화(소문자·구두점 제거·공백 압축) 후 부분일치. MVP-B는 production 동사(produce/make/build/train) **그리고** "scv"가 모두 있어야 `produce_scv` 발화. 무매칭 → 무명령 + 로그.
-   **라이브러리 셋**: `pynput` + `sounddevice` + `numpy` + `faster-whisper` (+ stdlib `asyncio`/`socket`).
-   **설정**: 상수 하드코딩(PTT 키·모델·포트·규칙). config 파일·CLI 인자 없음 ([ADR-009](decisions.md#adr-009) 단순성).
-   **피드백**: Python 콘솔 로그 스트림이 유일한 피드백(GUI·오디오 큐 없음). 단계별 로그 — `ptt: recording...` / `stt: "..."` / `nlu: matched ...` / `tcp: sent ...`, 실패 경로 `stt: (empty)` / `nlu: no rule matched` / `tcp: no bot connected, dropped`.

빈/공백 전사는 NLU 이전 조기 종료 (`stt: (empty)`).


## IPC

-   **전송**: TCP, `localhost:5000`.
-   **인코딩**: JSON lines (`\n` delimited). 예: `{"cmd":"produce_scv"}\n`.
-   **역할**:
    -   Python = **서버**, 여러 매치 동안 살아남음.
    -   C++ 봇 = **클라이언트**, 매치 시작 시마다 새로 연결.
    -   이유: Python을 서버로 두면 매치 사이에 STT 모델이 메모리에 유지된다. 봇은 매치마다 BWAPI(게임)에 재연결하는데, 봇이 Python 서버이기도 하면 그 listener가 매 매치 죽어 Python의 재연결이 복잡해진다 ([ADR-004](decisions.md#adr-004)).
-   **봇 측 I/O**: 비차단 소켓을 메인 루프(매 `BWAPIClient.update()` 직후)에서 폴링, 영구 라인 버퍼에 누적, `\n` 만날 때마다 한 명령 파싱·실행 ([ADR-005](decisions.md#adr-005)).
-   **연결 복구**: 봇은 첫 진입 시점부터 재연결 로직 포함 (N 프레임마다 재시도) ([ADR-004](decisions.md#adr-004)).
-   **서버 측 생애주기 (MVP-B)**: Python asyncio 서버가 봇 1개 연결을 보유, accept/disconnect/reconnect 시 writer 교체. 봇 미연결 중 생성된 명령은 **드롭 + 로그**(미래 연결에 큐잉하지 않음) ([ADR-019](decisions.md#adr-019)).

### MVP-A에서의 임시 서버 (은퇴)

MVP-A에서는 Python 서비스가 존재하기 전이라 `nc -l -k 5000`이 서버 역할을 대신했다 (운영자가 nc stdin에 JSON 한 줄 입력 → 봇 수신·실행, `-k`로 매치 재시작에도 세션 유지). **MVP-B에서 Python 서버가 :5000을 차지하며 `nc`는 은퇴한다** — 디버그 폴백으로도 두지 않는다 ([ADR-019](decisions.md#adr-019)).


## 테스트 맵

-   **별도 맵 제작 없음.** 스톡 melee 맵의 테란 시작 상태(Command Center 1기 + SCV 4기 + 시작 미네랄 + 서플라이 여유)를 그대로 harness로 쓴다 ([ADR-007](decisions.md#adr-007)).
-   `produce_scv`의 생산 건물은 melee 시작 시 봇 슬롯이 이미 소유한 Command Center다. 사전 배치·소유자 설정이 필요 없어 "배럭 소유자 불일치로 `getUnits()`가 빈다"는 실패 모드가 사라진다.


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
└── voice/                # Python 음성 서비스 (MVP-B)
    └── voice_craft/      # PTT·마이크·STT·NLU·asyncio TCP 서버
```

최상위 컴포넌트 디렉터리 + 컴포넌트 내부의 자체 `src/` ([ADR-009](decisions.md#adr-009)).
