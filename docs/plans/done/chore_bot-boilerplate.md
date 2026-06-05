# A3 — BWAPI Client API 봇 .exe (채팅 "hello") — 완료

worktree `chore_bot-boilerplate`. A1·A2(환경 셋업)에 이어 실제 봇 코드가 들어온다.

**완료 (2026-06-06)**: 봇 .exe가 같은 Wine prefix에서 shared memory로 BWAPI에 연결, 매치 진입 시 채팅에 hello 출력 확인. 2b(shared memory under Wine)까지 실증. 매치 재진입 시 재연결도 정상.

원래 계획은 C++ AIModule(DLL) 방식이었으나, MinGW로 링크 불가함을 확인해 **BWAPI Client API(.exe)**로 피벗했다 ([ADR-014](../../decisions.md#adr-014)). 이 문서는 피벗 후 남은 작업의 진행 기록이다.

## 목표

vendored BWAPI Client 소스로 봇 `.exe`를 MinGW(Docker)로 빌드 → 게임과 같은 Wine prefix에서 실행 → shared memory로 연결 → 게임 채팅에 "hello voice-craft" 출력.

- **A3 통과 조건**: injectory로 BWAPI 주입된 BW에 매치 진입 후 봇 .exe 실행 → 채팅창에 "hello voice-craft"가 뜨고, 봇 콘솔/로그에 에러 없음, 크래시 없음.

빌드 파이프라인 + shared memory 연결이 끝까지 뚫리는가를 검증한다. 봇 로직은 한 줄(`sendText`)이면 충분하다.


## 완료된 것 (커밋됨)

-   **2a 검증** — MinGW(Docker)으로 BWAPI Client `ExampleAIClient.exe`(PE32)가 끝까지 빌드됨을 spike로 확인. 빌드 레시피 확정.
-   **vendoring** (커밋 `1595572`) — BWAPI 4.4.0 Client 소스(`BWAPIClient/ Util/ Storm/ Shared/ BWAPILIB/`) + include + shim/stub + `bot/Dockerfile`.
-   **MinGW 패치** (커밋 `96afa7b`) — `CommandTemp.h`(`forward<BWAPIC::Command>`), `SharedMemory.h`(`decltype(Pointer<T>::offset)`).
-   **Docker 이미지** — `voice-craft-bot-build` (Debian + g++-mingw-w64-i686 + cmake + binutils + mingw-w64-tools).
-   **문서** — ADR-014 추가, ADR-003 supersede, ADR-004/005 Note, architecture.md / AGENTS.md 갱신.


## 검증된 빌드 레시피 (spike 결과)

-   컴파일러: `i686-w64-mingw32-g++`
-   필수 플래그: `-std=c++17 -DNOMINMAX=1 -D_WIN32_WINNT=0x0501`
-   필수 링크: `-lws2_32 -static -static-libgcc -static-libstdc++`
-   include: `shim`, `include`, `include/BWAPI/Client`, `BWAPIClient/Source`, `Util/Source`, `Storm`, `Shared`, 루트(`svnrev.h`용 `-I.`)
-   소스 범위: BWAPIClient + Util + Storm + Shared + **BWAPILIB**(전부 대문자 디렉터리) + 봇 자체 소스


## 남은 단계

1.  **toolchain 파일** → `bot/cmake/mingw-w64-toolchain.cmake` (i686 타깃, `CMAKE_SYSTEM_NAME=Windows`, 컴파일러 `i686-w64-mingw32-g++`).
2.  **CMakeLists** → `bot/CMakeLists.txt`: vendored Client 소스로 `BWAPIClient` static lib 빌드 + 봇 소스 링크 → `.exe` 출력. 위 레시피의 플래그/include/링크 반영. (BWAPI 동봉 `CMake/Client`는 MSVC 전제(`/DNOMINMAX`)라 참고만 하고 자체 작성.)
3.  **최소 봇 소스** → `bot/src/main.cpp`: ExampleAIClient 패턴(`reconnect()` → `while: update() / isConnected 체크`) + 연결되면 `Broodwar->sendText("hello voice-craft")`.
4.  **컨테이너 빌드** → `docker run`으로 cmake 빌드 → `bot/build/voice-craft-bot.exe` 생성 → verify: PE32(i386) 확인.
5.  **mise 태스크** → 이미지 빌드(`bot-image`, 멱등), 컨테이너 빌드(`bot-build`), 게임+봇 실행(`bw-bot`: injectory 주입 → 봇 .exe를 같은 Wine prefix에서 실행).
6.  **실행 + 검증 (2b 포함)** → injectory로 BWAPI 주입, 매치 진입, 봇 .exe 실행 → verify: shared memory 연결됨, **채팅에 "hello voice-craft"**, 에러/크래시 없음.


## 잔여 리스크

-   **2b — shared memory under Wine** (가장 불확실): 봇 .exe와 게임이 같은 Wine prefix에서 `Global\bwapi_shared_memory_*`를 공유해야 함. spike에서 컴파일·링크는 검증했지만 **런타임 연결은 미검증**. 6단계가 이걸 처음으로 실제 확인하는 지점.
-   **bwapi.ini server 설정**: Client 연결을 받으려면 BWAPI가 server 모드여야 할 수 있음 (bwapi.ini의 `auto_menu`/connection 관련). 실행 단계에서 확인.
-   **버전 일치**: 주입 BWAPI.dll(4.4.0)과 vendored Client 소스(v4.4.0 태그)가 일치 — shared memory 프로토콜 호환 확보됨.


## 미확정

-   **봇 소스 파일 구성**: 단일 `main.cpp` vs 분리. A3는 단일이면 충분, A5(TCP)·A6(JSON)에서 분리 검토.
-   **sendText 반복 여부**: 매 프레임 출력하면 채팅 도배 → onStart 1회성 플래그로 한 번만.


## 다음

-   A4. 테스트 맵 (ScmDraft 2, 배럭 Player 1 소유 확인) — 봇 .exe가 채팅 출력에 성공하면 진행.
