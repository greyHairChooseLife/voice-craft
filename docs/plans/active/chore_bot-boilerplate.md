# A3 — MinGW 툴체인 + 자체 DLL 로딩 (채팅 "hello")

worktree `chore_bot-boilerplate`에서 수행. A1·A2(환경 셋업)에 이어 **여기서부터 실제 봇 코드**가 들어온다.

## 목표

자체 작성한 최소 `AIModule` DLL을 MinGW-w64로 크로스컴파일해서, injectory로 주입된 BW에 로딩 → 게임 채팅에 "hello voice-craft" 출력.

- **A3 통과 조건**: 매치 진입 시 게임 채팅창에 "hello voice-craft"가 뜨고, `bwapi-data/logs/`에 에러 없음, 크래시 없음.

이 단계는 코드 자체보다 **빌드 파이프라인(헤더·링크·툴체인·주입 경로)이 끝까지 뚫리는가**를 검증한다. 봇 로직은 한 줄(`sendText`)이면 충분하다.


## 비자명한 핵심 — BWAPI SDK 확보

받은 STARTcraft 패키지는 실행용 `bwapi-data/BWAPI.dll`만 있고, 컴파일에 필요한 **헤더**와 **MinGW용 import 라이브러리**가 그대로는 없다.

-   헤더 + MSVC용 `.lib` + ExampleAIModule 소스는 패키지 안 `BWAPI.7z`(공식 SDK 배포본)에 들어있다.
-   MSVC 형식 `.lib`은 MinGW로 직접 링크 불가 ([ADR-003](../../decisions.md#adr-003)이 예고한 함정).

**해결**:

1.  `BWAPI.7z`에서 **헤더만** 꺼내 `bot/third_party/bwapi/include/`에 둔다.
2.  import 라이브러리는 MSVC용을 버리고, 런타임 `BWAPI.dll`에서 **MinGW용 `.a`를 직접 생성**한다 (`gendef` → `.def`, `dlltool` → `libBWAPI.a`). 둘 다 mingw-w64 패키지에 포함.

→ MSVC 의존성이 사라지고 MinGW만으로 빌드된다. 이 결정은 새 ADR로 기록한다.


## 비자명한 핵심 2 — 빌드 전체 컨테이너화 (Docker)

MinGW·cmake·gendef·dlltool을 **호스트에 설치하지 않는다**. import lib 생성 + 봇 컴파일 전부 Docker 컨테이너 안에서 한다. 호스트엔 Docker만.

-   **이미지**: `mingw-w64-gcc` + `cmake` + `binutils`(gendef/dlltool) 포함. 최초 1회 빌드(2~5분), 이후 재사용.
-   **빌드**: `docker run`에 `bot/`을 bind mount → 컨테이너 안에서 cmake 빌드 → 산출 DLL이 mount 통해 호스트 `bot/build/`에 떨어짐. 컨테이너당 오버헤드 ~1초 미만, 증분 캐시는 `build/` mount로 유지.
-   **역할 분리**: 컨테이너는 BW·Wine을 전혀 모른다. 순수 크로스컴파일러. 산출물은 그냥 32-bit PE 파일.

```
[Docker 컨테이너]                          [호스트 Wine]
mingw-w64 + cmake 빌드                      injectory로 주입
  ↓ 출력 (bind mount)                        ↑ 입력 (파일 복사)
bot/build/voice-craft-bot.dll  ──>  $BW_DIR/bwapi-data/AI/voice-craft-bot.dll
```

-   **주의 (Docker 권한)**: rootless가 아니면 컨테이너가 만든 파일이 root 소유로 생김. `docker run --user "$(id -u):$(id -g)"`로 호스트 UID 매핑해 회피.


## 단계

1.  **Dockerfile 작성** → `bot/Dockerfile`: 베이스 + `mingw-w64-gcc cmake binutils` 설치 → verify: `docker build`로 이미지 생성, 컨테이너 안에서 `i686-w64-mingw32-g++ --version`·`gendef`·`dlltool` 동작.
2.  **BWAPI 헤더 추출** → `BWAPI.7z`에서 include 트리를 `bot/third_party/bwapi/include/`로 복사 (호스트에서 `7z` 또는 컨테이너 안에서) → verify: `BWAPI.h`·`BWAPI/AIModule.h` 존재.
3.  **MinGW import lib 생성 (컨테이너 안, 일회성)** → `BWAPI.dll`에서 `gendef` + `dlltool`로 `bot/third_party/bwapi/lib/libBWAPI.a` 생성 → verify: 파일 생성, `i686` 아키텍처.
4.  **toolchain 파일 작성** → `bot/cmake/mingw-w64-toolchain.cmake` (i686 타깃, `CMAKE_SYSTEM_NAME=Windows`).
5.  **CMakeLists 작성** → `bot/CMakeLists.txt`: `-std=c++17`, BWAPI include 경로, `libBWAPI.a` 링크, 출력은 32-bit `.dll` (`SHARED`, 접두사 없음 → `voice-craft-bot.dll`).
6.  **최소 AIModule 작성** → `bot/src/VoiceCraftBot.cpp` + BWAPI가 요구하는 `gameInit`/`newAIModule` export. `onStart` 또는 첫 `onFrame`에서 `Broodwar->sendText("hello voice-craft")`.
7.  **컨테이너 빌드** → `docker run --user ... -v bot:/work <image>` 안에서 `cmake -B build -DCMAKE_TOOLCHAIN_FILE=...` → `cmake --build build` → verify: 호스트 `bot/build/voice-craft-bot.dll` 생성, `file`로 PE32(i386) 확인.
8.  **배치 + bwapi.ini 설정** → DLL을 `$BW_DIR/bwapi-data/AI/`에 복사, `bwapi.ini`의 `ai =`를 우리 DLL로 지정 (A2에서 비워둔 상태) → verify: ini 줄 확인.
9.  **실행 + 검증** → `mise run` 태스크로 injectory 주입 실행 (호스트 Wine), single-player 맵 진입 → verify: **채팅에 "hello voice-craft", 로그 에러 없음, 크래시 없음**.


## 산출물 (예상)

-   `bot/` 디렉터리 신설: `Dockerfile`, `cmake/mingw-w64-toolchain.cmake`, `CMakeLists.txt`, `src/VoiceCraftBot.cpp`, `third_party/bwapi/{include,lib}/`.
-   `bot/build/`는 gitignore. `third_party/bwapi/` 커밋 여부는 라이선스 확인 후 결정 (미커밋이면 생성 절차를 mise 태스크로).
-   `mise.toml`: A3 태스크 — 이미지 빌드(`bot-image`, 멱등), 컨테이너 빌드(`bot-build` → `docker run`), 배치(`bot-deploy`), 실행(`bw-bot`). `bwapi.ini` ai= 자동 설정 포함.
-   새 ADR 2건: (1) "BWAPI import lib을 dll에서 dlltool로 생성 (MSVC .lib 미사용)", (2) "봇 빌드는 Docker 컨테이너에서 (MinGW 호스트 미설치)". `architecture.md` 빌드 섹션 갱신, `runbook.md` A3 절차 실제값으로 갱신 (현재 Chaoslauncher 기준 → injectory + Docker 빌드 기준).
-   `bwapi.ini`의 `ai =`가 우리 봇을 가리키게 됨 (A2 빈 값에서 전환).


## 미확정 / 진행 중 결정

-   **export 시그니처**: BWAPI 4.4.0이 요구하는 모듈 진입점 정확한 형태 (`extern "C" __declspec(dllexport)` `newAIModule` vs `gameInit`)는 `BWAPI.7z`의 ExampleAIModule 소스로 확인.
-   **sendText 타이밍**: `onStart` 한 번 vs 첫 프레임. 채팅 가시성 확인 쉬운 쪽으로. (단발 메시지면 onStart로 충분.)
-   **third_party 커밋 여부**: BWAPI 라이선스(LGPL 계열) 확인 후. 미커밋이면 추출·생성 절차를 멱등 mise 태스크로 두고 README/runbook에 명시.


## 다음

-   A4. 테스트 맵 (ScmDraft 2, 배럭 Player 1 소유 확인) — 자체 DLL이 도는 게 확인되면 진행.
