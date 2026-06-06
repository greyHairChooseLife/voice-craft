# 실행 절차 (Runbook)

"지금 한 번 돌려보고 싶다"를 위한 단계별 명령.


## 사전 준비 (1회성)

### Wine + BW 1.16.1

작업은 루트 `mise.toml`의 task로 정의되어 있다. 게임 확보 근거는 [ADR-011](decisions.md#adr-011). `WINEPREFIX`(`~/.wine-bw`)·`WINEARCH`(`win64`)·`BW_DIR`(`~/sc-bw-1161`)는 `mise.toml`의 전역 `[env]`에서 모든 task에 자동 주입되므로 수동 export가 필요 없다. Wine 11+는 wow64 단일 빌드라 `win64` prefix에서 32-bit BW를 실행한다 ([ADR-001](decisions.md#adr-001) Note 참조).

순서:

```bash
# 1. BW 1.16.1 + BWAPI 4.4.0 패키지 다운로드·압축 해제 (~97 MB, 멱등)
mise run bw-download

# 2. Wine 등 시스템 패키지 설치 — sudo 필요, '!' 접두로 실행
#    ([multilib] 저장소가 켜져 있어야 32-bit wine이 깔린다)
! mise run system-setup

# 3. 전용 WINEPREFIX 초기화 (win64/wow64, 멱등)
mise run wine-init

# 4. 게임 실행 → 메인 메뉴 확인 (bw-download·wine-vdesktop 자동 선행)
mise run bw-run
```

-   `bw-run`은 `wine-vdesktop`에 `depends` → BW가 640x480 가상 데스크톱 창(윈도우 모드)으로 뜬다. i3-wm이 이 창을 일반 타일/플로팅 창으로 배치한다.
-   **BW 1.16.1은 내부 렌더가 640x480 고정**이라 가상 데스크톱 크기(`WINE_VDESKTOP`)를 키워도 게임은 커지지 않고 검은 여백만 늘어난다 → 창을 게임 크기(640x480)에 맞춰 둔다.
-   체크포인트 A1 통과 조건: **메인 메뉴 화면이 보인다.**
-   안 뜨면 → ADR-001대로 첫 의심처는 Wine 환경 (win64/wow64 prefix인지, multilib wine인지).

### A2 — injectory로 BWAPI 주입 (봇 없음)

패키지엔 Chaoslauncher가 없고 injectory CLI가 들어있다 ([ADR-012](decisions.md#adr-012)). bwapi.ini의 `ai =`를 비운 채 주입만 검증한다 ([ADR-013](decisions.md#adr-013)).

```bash
mise run bw-bwapi
```

-   injectory가 `BWAPI.dll` + `WMode.dll`을 StarCraft.exe에 주입. `--verbose` 로그로 주입 확인.
-   single-player 게임까지 진입 → BWAPI 오버레이/`bwapi-data/logs/` 정상, 크래시 없음.
-   체크포인트 A2 통과 조건: **BWAPI가 주입된 채 크래시 없이 실행된다.**

### A3 — BWAPI Client API 봇 .exe (Docker MinGW 빌드)

봇은 AIModule DLL이 아니라 독립 `.exe` ([ADR-014](decisions.md#adr-014)). 빌드는 Docker 컨테이너에서, 호스트엔 MinGW를 깔지 않는다. 봇 소스 라이브러리(vendored BWAPI Client)는 `bot/third_party/bwapi/`에 있다.

**빌드** (이미지 1회 빌드 후 재사용):

```bash
mise run bot-build      # bot-image(이미지) 의존 → 컨테이너에서 cmake 빌드
# 산출물: bot/build/voice-craft-bot.exe (PE32, i386)
```

**실행** — 게임과 봇은 **같은 Wine prefix**(`~/.wine-bw`)에서 도는 별도 프로세스. shared memory로 연결된다 (bwapi.ini의 `shared_memory = ON` 필수).

```bash
# 터미널 1 — 게임 + BWAPI 주입
mise run bw-bwapi
#   → single-player 로 아무 맵이나 로드해 매치에 진입 (A3는 채팅 출력만 확인)

# 터미널 2 — 봇 .exe (게임이 매치에 진입한 뒤)
mise run bot-run
```

-   봇 콘솔: `connecting to BWAPI...` → `Connected` → `waiting to enter match` → 매치 진입 시 `in match: sent hello`.
-   게임 채팅창에 `hello voice-craft ...` 표시.
-   메뉴 상태에선 콘솔이 `waiting to enter match`만 반복 (정상 — `isInGame()`이 false).
-   체크포인트 A3 통과 조건: **봇 .exe가 shared memory로 연결되고 채팅에 메시지가 뜬다.**

### A4 — 봇 비차단 TCP 클라이언트 (라인 echo)

봇이 명령 서버(`127.0.0.1:5000`)에 비차단 TCP로 붙어, 들어온 라인을 콘솔에 echo ([ADR-004](decisions.md#adr-004)/[ADR-005](decisions.md#adr-005)). JSON 파싱·`train()` 호출은 아직 없다 (A5). 모듈: `bot/src/voice_client.{h,cpp}` (`VoiceClient`).

```bash
# 터미널 1 — 명령 서버 대기
nc -l -k 5000

# 터미널 2 — 게임 + BWAPI 주입
mise run bw-bwapi   # → single-player 테란 매치 진입

# 터미널 3 — 봇 .exe
mise run bot-run
```

-   봇 콘솔: 매치 루프 진입 후 `voice: connected to 127.0.0.1:5000`.
-   `nc`에 라인 입력 → 봇 콘솔 `voice recv: <라인>`. 멀티라인·부분 라인은 영구 버퍼가 `\n`로 분할.
-   `nc` 죽이고 재실행 → `voice: server closed` 후 재연결.
-   봇이 매치 진입 시 `Broodwar->enableFlag(Flag::UserInput)`를 켜서 **테스트용**으로 사람도 유닛 조종 가능 (기본은 봇만 명령 가능 → A4 봇은 train 호출이 없어 유닛이 안 움직이는 게 정상).
-   체크포인트 A4 통과 조건: **봇이 서버에 connect 하고, 입력 라인을 콘솔에 echo 하며, 프레임 루프가 끊김 없이 돈다.**

### 테스트 맵 — 별도 제작 없음

-   맵을 만들지 않는다 ([ADR-007](decisions.md#adr-007)). 스톡 melee 맵을 single-player + 테란으로 로드하면 봇 슬롯이 Command Center 1기 + SCV 4기 + 시작 미네랄(50) + 서플라이 여유를 이미 갖는다.
-   `produce_scv`는 이 기본 Command Center에서 SCV를 뽑으므로 사전 배치·소유자 설정이 필요 없다.


## MVP-A 실행 절차 (반복) — A5

A4(TCP echo)까지 통과한 뒤, 여기서 `on_line` 콜백에 JSON 파싱 + `produce_scv` 디스패치가 들어가면 A5 = MVP-A 완료. 아래는 A5 구현 후의 일상 실행 흐름.

1.  터미널에서 `nc -l -k 5000` 실행 (서버 대기).
2.  게임 + BWAPI 주입: `mise run bw-bwapi`.
3.  BW에서 single-player → 스톡 melee 맵 → **테란**으로 게임 시작.
4.  봇 .exe 실행: `mise run bot-run`. 봇 로그에서 "connected to 127.0.0.1:5000" 확인.
5.  `nc` 터미널에 한 줄 입력:

    ```
    {"cmd":"produce_scv"}
    ```

6.  게임 화면에서 Command Center가 SCV 1기를 생산하는지 확인 (훈련 progress bar / 서플라이 카운트 증가).
7.  반복: 같은 줄을 다시 입력 → 또 한 기 생산.

**체크포인트 A5 통과 조건 = MVP-A 완료**: 위 6단계가 처음 시도에서 SCV를 띄우고, 7단계가 두 번째 SCV를 띄운다. BWAPI 에러 로그 없음.


## 디버깅 빠른 확인

증상별 첫 번째 의심처:

-   **봇 로그에 "connected" 메시지가 안 뜬다** → `nc -l -k 5000`이 정말 listen 중인지 (`ss -tlnp | grep 5000`), Wine 안의 봇이 host의 localhost에 닿는지.
-   **`{"cmd":"produce_scv"}` 입력 후 아무 반응이 없다** → 봇 로그에 라인이 도착했는지 (A4 echo 동작이 살아있는지), JSON 파싱 에러가 났는지, `Broodwar->self()->getUnits()`가 비었는지.
-   **`getUnits()`가 비어 있다** → 매치를 **테란**으로 시작했는지, single-player melee로 실제 게임에 진입했는지 (메뉴 상태면 빈다).
-   **SCV가 안 나오고 `getLastError()`가 `Insufficient_Minerals`** → 시작 미네랄(50)을 이미 다른 데 썼는지 / 매치가 melee 시작 상태인지.
-   **두 번째 매치부터 봇이 명령에 반응하지 않는다** → 봇의 재연결 루프가 누락 (ADR-004).


## MVP-B 실행 절차 (음성 경로)

MVP-A의 `nc` 단계를 Python 음성 서비스가 대체한다 ([ADR-019](decisions.md#adr-019)). 영어 전용. 동시성·STT·NLU 설계는 [ADR-015](decisions.md#adr-015)~[ADR-018](decisions.md#adr-018).

아래 "사전 준비 / 반복 실행"은 음성 경로 전체(B5)가 결선된 뒤의 최종 흐름이다. 체크포인트별 중간 검증은 그 앞에 둔다.

### B1 — asyncio TCP 서버 (stdin 입력, `nc` 대체 검증)

음성 경로 결선 전, 서버가 봇 1개 연결을 보유하고 명령을 전달하는지만 검증한다 ([ADR-019](decisions.md#adr-019)). 음성 입력 자리에 **stdin** 을 둬 MVP-A의 `nc` 흐름을 그대로 재현한다. PTT·STT·NLU 의존성은 아직 깔지 않는다 (B1 은 stdlib `asyncio` 만).

```bash
# 1회성 — uv + voice/.venv 생성 (B1 은 의존성 없음, 패키지만 설치)
mise run voice-setup

# 터미널 1 — 음성 서버 (stdin 으로 JSON 입력)
mise run voice
#   → "tcp: listening on 127.0.0.1:5000"

# 터미널 2 — 게임 + BWAPI 주입
mise run bw-bwapi   # → single-player 테란 매치 진입

# 터미널 3 — 봇 .exe
mise run bot-run
```

-   봇 연결 시 서버 콘솔: `tcp: bot connected 127.0.0.1:...`, 봇 콘솔: `voice: connected to 127.0.0.1:5000`.
-   서버 터미널(터미널 1)의 stdin 에 한 줄 입력 → 봇에 전달:

    ```
    {"cmd":"produce_scv"}
    ```

    서버 콘솔 `tcp: sent ...`, 봇이 SCV 1기 생산 (A5 디스패치 재사용).
-   봇 미연결 중 입력하면 `tcp: no bot connected, dropped: ...` (큐잉 안 함, [ADR-019](decisions.md#adr-019)).
-   봇 재연결 시 writer 교체 (`tcp: replacing bot ...`) — 두 번째 봇이 붙으면 옛 연결을 닫는다 (단일 봇 불변식).
-   **B1 통과 조건**: 서버가 `:5000` 에 listen, 봇이 connect, stdin 한 줄이 봇까지 도달해 SCV 생산. `nc` 없이 동작.

### B2 — PTT 캡처 (`,` 토글 + 마이크 → numpy 버퍼)

음성 입력단만 검증한다 ([ADR-016](decisions.md#adr-016)). `,` 토글로 마이크를 녹음해 numpy 버퍼를 만들고 길이를 로그한다 — STT(B3)·봇 송신(B5) 전이라 버퍼는 봇에 가지 않는다. B1 의 stdin 펌프는 그대로 남아 동시 동작한다.

```bash
# 1회성 — 음성 의존성 설치 (pynput·sounddevice·numpy)
mise run voice-setup

# 음성 서버 + PTT 캡처
mise run voice
#   → "tcp: listening on 127.0.0.1:5000"
#   → "ptt: ready (, to start/stop)"
```

-   **`,` 눌러 시작**, 잠깐 말하고, **다시 `,` 눌러 정지**:

    ```
    ptt: recording...
    ptt: captured 1.4s
    ```

    캡처 길이가 발화 길이에 비례하면 통과.
-   바로 정지하면 `ptt: captured 0.0s (empty)` (B3 에서 STT 조기 종료로 이어질 자리).
-   녹음 중에도 서버는 listen — 봇이 connect 하면 `tcp: bot connected ...`(워커 스레드 분리 확인).
-   **B2 통과 조건**: `,`→`recording...`, 다시 `,`→`captured <N>s`, 반복 동작. :5000 서버가 녹음에 안 막힘. X11 세션 필요(전역 핫키, Wayland 미지원).
-   **`,` 눌러도 `recording...` 안 뜸** → X11 세션인지, 다른 앱이 `,` 를 가로채는지. `stt:` 가 엉뚱 → 마이크가 기본 입력 장치인지(`mise run voice` 시작 시 sounddevice 기본 장치 확인).

### 사전 준비 (1회성)

```bash
# Python 의존성 설치 (voice/ 패키지)
#   pynput + sounddevice + numpy + faster-whisper
#   sounddevice는 PortAudio 시스템 패키지 필요할 수 있음 (Arch: portaudio)
mise run voice-setup
```

-   `base.en` 모델은 첫 실행 시 자동 다운로드되어 캐시된다 (이후 재사용).
-   X11 세션이어야 한다 (전역 핫키 — Wayland 미지원, [ADR-016](decisions.md#adr-016)).

### 반복 실행

1.  **음성 서비스 기동** (`nc` 대체):

    ```bash
    mise run voice
    ```

    -   `base.en` 모델 로드 → `:5000` 서버 listen → `,` 핫키 등록까지 끝나면 콘솔에 준비 로그.

2.  **게임 + BWAPI 주입**: `mise run bw-bwapi`.
3.  BW에서 single-player → 스톡 melee 맵 → **테란**으로 게임 시작 (MVP-A와 동일 harness, [ADR-007](decisions.md#adr-007) — 새 맵 없음).
4.  **봇 .exe 실행**: `mise run bot-run`. 음성 콘솔에 봇 connect 로그 확인.
5.  **`,` 눌러 시작** "produce SCV" (또는 build/make/train + scv) 말하고 **다시 `,` 눌러 정지**.
6.  Command Center가 SCV 1기를 생산하는지 확인 (훈련 progress bar / 서플라이 카운트 증가).
7.  반복: 다시 `,` 누르고 말하고 `,` 정지 → 또 한 기 생산.

**체크포인트 통과 조건 = MVP-B 완료**: 5~6단계가 키보드 JSON 없이 음성만으로 SCV를 띄우고, 7단계가 반복된다. 인식 안 된 발화는 명령을 보내지 않고 콘솔에 이유를 남긴다. BWAPI 에러 로그 없음.

### 콘솔 로그로 읽는 단계 (피드백)

운영자는 게임을 보지만 진단은 음성 콘솔 로그로 한다 ([ADR-015](decisions.md#adr-015)):

```
ptt: recording...
ptt: captured 1.4s
stt: "produce an scv"
nlu: matched produce_scv
tcp: sent produce_scv
```

실패 경로:

-   `stt: (empty)` — `,` 로 녹음했지만 음성이 안 잡힘 / 무음.
-   `nlu: no rule matched: "..."` — 동사+scv 조건 불충족.
-   `tcp: no bot connected, dropped: produce_scv` — 봇이 매치에 없을 때 발화 (드롭, 큐잉 안 함).

### 디버깅 빠른 확인 (MVP-B)

-   **`,` 를 눌러도 `ptt: recording...`이 안 뜬다** → X11 세션인지, `pynput`이 핫키를 잡았는지 (다른 앱이 `,` 를 가로채는지).
-   **`stt:`가 매번 엉뚱한 텍스트** → 마이크가 기본 입력 장치로 잡혔는지, 너무 짧게 말했는지. `tiny.en`/`small.en`로 모델 조정 ([ADR-017](decisions.md#adr-017)).
-   **`tcp: no bot connected`** → 봇이 매치에 진입했는지 (메뉴 상태면 봇이 :5000에 연결 안 됨). 봇 로그에서 "connected to 127.0.0.1:5000" 먼저 확인하고 말한다.
-   **봇은 connect 했는데 SCV가 안 나온다** → MVP-A 디버깅 절차로 (getUnits 비었는지 / getLastError). 음성 경로는 `tcp: sent`까지 떴으면 정상.
