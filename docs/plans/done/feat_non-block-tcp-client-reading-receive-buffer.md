# A4 — 봇 비차단 TCP 클라이언트 (라인 echo) — 완료

worktree `feat_non-block-tcp-client-reading-receive-buffer`. A3(shared memory 연결 + hello 채팅)에 이어, 봇이 명령 서버에 TCP로 붙어 들어온 라인을 콘솔에 echo 한다.

## 범위

-   **포함**: 비차단 TCP 클라이언트 모듈. `127.0.0.1:5000` connect → 매 프레임 polling → 영구 라인 버퍼 누적 → `\n` 단위로 완성된 라인을 봇 콘솔/로그에 echo. 서버 부재·끊김 시 재연결.
-   **불포함 (다음 단계)**: JSON 파싱(nlohmann, [ADR-008](../../decisions.md#adr-008)), `produce_scv`/`train()` 디스패치([ADR-006](../../decisions.md#adr-006)).

근거 ADR: [ADR-004](../../decisions.md#adr-004) (봇=클라이언트, 재연결 필수), [ADR-005](../../decisions.md#adr-005) (비차단 소켓, 프레임마다 polling, 라인 버퍼, 단일 스레드).

## A4 통과 조건

1.  `nc -l -k 5000` listen 중 → 봇이 connect, 콘솔에 connect 로그.
2.  서버 없음 → 봇이 재시도, 프레임 루프는 끊김 없이 계속 (비차단 확인).
3.  `nc`에 라인 입력 → 봇이 그 라인을 콘솔에 출력 (runbook 디버그의 "A4 echo 동작").
4.  한 `recv()`에 여러 라인 / 부분 라인 → 영구 버퍼가 `\n`로 정확히 분할.
5.  서버 drop → 봇이 죽지 않고 재연결.

## 설계 결정

### 별도 모듈로 분리

A3 plan의 "단일 main.cpp vs 분리" 미결 항목을 여기서 분리로 확정. TCP 로직(소켓 수명, 라인 버퍼, 재연결)이 main 루프와 책임이 다르고 이후 JSON 단계에서 더 자랄 자리라, 지금 떼어 둔다.

-   `bot/src/tcp_client.h` / `bot/src/tcp_client.cpp` — `CommandClient` 클래스.
-   `bot/src/main.cpp` — 매치 루프에서 `CommandClient`를 소유, 매 프레임 `poll()` 호출.

### 소켓 API: Winsock (POSIX 아님)

봇은 Wine에서 도는 Windows .exe라 POSIX `O_NONBLOCK`이 아니라 Winsock을 쓴다. CMake가 이미 `ws2_32` 링크 중.

-   `WSAStartup` / `WSACleanup`.
-   비차단: `ioctlsocket(s, FIONBIO, &mode=1)` ([ADR-005]의 `FIONBIO` 경로).
-   `connect()` 는 비차단이라 `WSAEWOULDBLOCK` 반환 가능 → "연결 시도 중"으로 처리, 폴링에서 완료/실패 판정.
-   `recv()` 가 `WSAEWOULDBLOCK` → 데이터 없음, 즉시 반환 (블록 안 함).
-   `recv()` 가 0 → 서버가 닫음 → 재연결 상태로.

### `CommandClient` 인터페이스 (echo 단계)

```cpp
class CommandClient {
public:
  CommandClient(std::string host, uint16_t port);
  ~CommandClient();
  // 매 프레임 호출. 비차단. 완성된 각 라인마다 on_line(line) 호출.
  void poll(const std::function<void(const std::string&)>& on_line);
private:
  // 상태: Disconnected / Connecting / Connected
  // 소켓 핸들, 영구 수신 버퍼(std::string), host/port
};
```

-   echo 단계에서는 main이 `on_line = [](auto& l){ std::cout << "recv: " << l << "\n"; }` 를 넘긴다.
-   다음 JSON 단계에서 같은 `on_line` 자리에 파싱·디스패치를 끼운다 — 모듈 인터페이스 변경 없이.

### 재연결 정책

-   두 연결은 별개 ([ADR-004] note): 봇↔BWAPI(게임) vs 봇↔명령서버. `CommandClient`는 후자만 담당.
-   비차단이라 BWAPI 재연결처럼 sleep-loop로 블록하지 않는다. `poll()` 안에서 상태 머신으로 진행: Disconnected면 connect 시도, Connecting이면 완료 확인, Connected면 recv.
-   재시도 폭주 방지: connect 실패 시 매 프레임 재시도해도 localhost라 비용 작음 — MVP는 단순 매 프레임 재시도. (백오프는 불필요, 명시 안 함.)

## 빌드 / 검증

-   `bot/CMakeLists.txt`: `add_executable(voice-craft-bot src/main.cpp src/tcp_client.cpp)` 로 새 소스 추가. `ws2_32` 이미 링크됨.
-   `mise run bot-build` → `bot/build/voice-craft-bot.exe` 산출.
-   검증 (runbook MVP-A 절차 일부):
    1.  `nc -l -k 5000` 실행.
    2.  `mise run bw-bwapi` → single-player 테란 매치 진입.
    3.  `mise run bot-run` → 봇 콘솔에 connect 로그.
    4.  `nc`에 아무 라인 입력 → 봇 콘솔에 `recv: <라인>`.
    5.  여러 줄 붙여넣기 / `nc` Ctrl-C 후 재실행 → 분할·재연결 확인.

## 결과 (완료 기록)

-   모듈은 `VoiceClient` 로 명명 (`CommandClient` 에서 변경) — `bot/src/voice_client.{h,cpp}`.
-   매치 진입 시 `Broodwar->enableFlag(Flag::UserInput)` 추가 — **테스트 전용** 디버깅 편의(사람도 유닛 조종 가능). 기본 BWAPI 상태는 봇만 명령 가능이라, A4 봇이 train 호출을 안 하면 유닛이 안 움직이는 게 정상. 다음 JSON 단계에서 봇이 명령을 낸다.
-   통과 조건 1–5 전부 수동 검증 통과 (connect 로그 / 비차단 / echo / 멀티라인 / drop 후 재연결).

### 빌드 이슈와 해결

-   `inet_pton` 이 MinGW 에서 미선언 — `ws2tcpip.h` 가 `_WIN32_WINNT >= 0x0600`(Vista) 에서만 노출하는데 프로젝트는 `0x0501`(XP) 로 설정됨.
-   해결: localhost IPv4 점표기 주소엔 `inet_addr`(winsock2.h, WINNT 게이트 없음) 로 충분 → 프로젝트 전역 `_WIN32_WINNT` 는 건드리지 않음. `ws2tcpip.h` include 제거.

## 미결 / 이후

-   JSON 파싱 + `produce_scv` 디스패치 = 다음 worktree. `on_line` 콜백 자리에 들어간다.
-   runbook 번호 정리 완료 (A4=TCP echo 로 통일).
-   `enableFlag(UserInput)` 는 테스트 편의 — MVP-A 완료 시점에 제거 검토.
