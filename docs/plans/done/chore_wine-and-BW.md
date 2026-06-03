# MVP-A 환경 셋업 (A1·A2) — 완료 기록

worktree `chore_wine-and-BW`에서 수행. 코드 없는 환경 셋업 단계(A1·A2)를 완료하고 머지한다. A3부터는 실제 MVP 코드라 새 worktree에서 진행한다.

결정의 *이유*는 ADR에, 반복 실행 *절차*는 runbook에 있다. 이 문서는 "무엇을 어떻게 했고 무엇이 비자명했나"의 진행 기록이다.


## A1. Wine + BW 1.16.1 실행 (메인 메뉴 도달) — 완료

### 한 일

-   BW 1.16.1을 STARTcraft 재호스팅 패키지로 확보 ([ADR-011](../../decisions.md#adr-011)).
    -   `https://davechurchill.ca/starcraft/files/startcraft/scbw_bwapi440.zip` (~97 MB, BW 1.16.1 + BWAPI 4.4.0 합본).
-   Wine 설치 (`wine wine-mono winetricks`), 전용 prefix `~/.wine-bw` 생성.
-   `mise run bw-run` → 메인 메뉴 도달 확인.

### 비자명했던 것

-   **무료 리마스터 배포판은 못 씀**: BWAPI Classic은 1.16.1 바이너리 오프셋에 의존. 리마스터(1.18+) 비호환.
-   **구 다운로드 미러 다 죽음**: `cs.mun.ca` 경로는 404. 살아있는 건 `davechurchill.ca` 최신 경로뿐 (검증: HTTP 200, `application/zip`, ZIP 매직바이트).
-   **Wine 11은 wow64 단일 빌드** ([ADR-001](../../decisions.md#adr-001) Note): `WINEARCH=win32` prefix 생성 불가 (`not supported in wow64 mode`). → `win64` prefix에서 32-bit BW를 wow64가 실행.
-   **BW 내부 렌더는 640x480 고정**: virtual desktop을 키워도 게임은 안 커지고 검은 여백만 늘어남 → vdesktop을 640x480로 맞춤. i3-wm이 이 창을 다룸.


## A2. injectory + BWAPI 인젝션 검증 — 완료

### 한 일

-   주입을 Chaoslauncher 대신 **injectory CLI**로 ([ADR-012](../../decisions.md#adr-012), ADR-002 대체).
-   A2를 **봇 없이 BWAPI 인젝션만** 검증하도록 축소 ([ADR-013](../../decisions.md#adr-013)).
-   `bwapi-data/bwapi.ini`의 `ai =`를 비우고 `mise run bw-bwapi` 실행.
-   injectory `--verbose` 출력에서 `BWAPI.dll`·`WMode.dll` 주입 확인, 매치 진입 시 BWAPI 오버레이 확인, 크래시 없음.

### 비자명했던 것

-   **받은 패키지엔 Chaoslauncher가 없음**: STARTcraft는 `injectory_x86.exe` + 주입 bat을 제공. → ADR-002(Chaoslauncher)를 ADR-012(injectory)로 대체. CLI라 `mise run` 워크플로에 그대로 들어가고 GUI 클릭이 사라짐.
-   **빌드된 스톡 봇이 없음**: BWAPI 4.4.0 공식 배포(BWAPI.7z)는 ExampleAIModule의 *소스만* 줌 (MSVC 빌드 전제). → "스톡 봇 동작" 검증을 포기하고 "BWAPI 주입 자체"만 격리 검증 (ADR-013). 실제 봇 동작은 A3(자체 hello DLL)로 이관.
-   **BWAPI 오버레이는 메뉴가 아니라 매치 진입 후에 나타남**: 메뉴 화면만 보고는 주입 성공을 알 수 없어 `--verbose` 모듈 출력으로 객관 확인.


## 산출물

-   `mise.toml`: task `bw-download` / `system-setup` / `wine-init` / `wine-vdesktop` / `bw-run` / `bw-bwapi` + 전역 env(`WINEPREFIX`/`WINEARCH`/`BW_DIR`/`WINE_VDESKTOP`).
-   ADR-011·ADR-012·ADR-013 추가, ADR-001 wow64 Note, ADR-002 Superseded.
-   runbook A1·A2 절차 갱신.


## 다음 (새 worktree)

-   A3. MinGW-w64 툴체인 + 자체 DLL 로딩 ("hello" 채팅 출력). 여기서부터 실제 코드.
-   bwapi.ini의 `ai =`를 우리 봇 DLL로 가리키게 됨 (A2에서 비워둔 상태).
