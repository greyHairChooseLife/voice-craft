# 실행 절차 (Runbook)

"지금 한 번 돌려보고 싶다"를 위한 단계별 명령.


## 사전 준비 (1회성)

### Wine + BW 1.16.1

-   Arch에서 Wine 설치 (`wine`, `winetricks`).
-   별도 WINEPREFIX 권장: `export WINEPREFIX="$HOME/.wine-bw"`.
-   BW 1.16.1 설치 후 `wine StarCraft.exe`로 메인 메뉴 진입 확인.
-   체크포인트 A1 통과 조건: **메인 메뉴 화면이 보인다.**

### Chaoslauncher + BWAPI

-   BWAPI 4.x (Classic) 릴리스 zip 다운로드.
-   `bwapi-data/`를 BW 설치 디렉터리에 복사.
-   Chaoslauncher 압축 해제 후 Wine으로 실행: `wine Chaoslauncher.exe`.
-   설정에서 "BWAPI Injector" 플러그인 활성화.
-   기본으로 제공되는 `ExampleAIModule.dll`을 `bwapi-data/AI/`에 둔 채 Chaoslauncher로 BW 기동 → 임의 melee 맵에서 봇이 자동으로 움직이는지 확인.
-   체크포인트 A2 통과 조건: **스톡 봇이 자기 할 일을 하고 크래시가 없다.**

### MinGW-w64 + CMake 툴체인

```bash
sudo pacman -S mingw-w64-gcc cmake
```

-   `bot/cmake/mingw-w64-toolchain.cmake` 작성 (i686 타깃, `CMAKE_SYSTEM_NAME=Windows`).
-   `bot/CMakeLists.txt` 작성 (`-std=c++17`, BWAPI include + import lib 링크, 출력은 `.dll`).
-   첫 빌드는 "hello" 만 출력하는 최소 `AIModule` 서브클래스로:

```bash
cd bot
cmake -B build -DCMAKE_TOOLCHAIN_FILE=cmake/mingw-w64-toolchain.cmake
cmake --build build
cp build/voice-craft-bot.dll "$HOME/.wine-bw/drive_c/<BW경로>/bwapi-data/AI/"
```

-   Chaoslauncher 재기동 → 봇 선택을 `voice-craft-bot.dll`로 변경 → 게임 채팅에 "hello voice-craft" 출력 확인.
-   체크포인트 A3 통과 조건: **자체 DLL이 로딩되고 채팅에 메시지가 뜬다.**

### 테스트 맵 (ScmDraft 2)

-   ScmDraft 2를 Wine 또는 Windows 머신에서 실행.
-   새 맵 생성:
    -   Tileset 임의, 크기 64x64면 충분.
    -   Player 1 = Human, Race = Terran, Start Location 배치.
    -   Player 1 소유 Terran Barracks 1기 사전 배치 ("Place Unit" 도구).
    -   "Properties → Forces / Players → Player 1 Starting Resources = 1000 minerals".
    -   서플라이 여유를 위해 Player 1 소유 Supply Depot 2기를 추가하거나, 트리거 없이 시작 미네랄·서플라이만 조정.
    -   **트리거 비워둘 것.**
-   `.scx`로 저장, BW 맵 디렉터리에 복사.
-   BW에서 single-player melee로 로드, "Use Map Settings" 모드로 확인 → **배럭이 파란색(Player 1) 소유인지 시각적으로 확인.**
-   체크포인트 A4 통과 조건: **맵이 로드되고 Player 1 소유 배럭이 보인다.**


## MVP-A 실행 절차 (반복)

체크포인트 A1–A4가 모두 통과한 뒤의 일상 실행 흐름.

1.  터미널에서 `nc -l -k 5000` 실행 (서버 대기).
2.  `wine Chaoslauncher.exe` 실행, "BWAPI Injector" 활성, 봇 DLL = `voice-craft-bot.dll`.
3.  BW 기동 → single-player → 테스트 맵 로드 → 게임 시작.
4.  봇 로그(게임 채팅 또는 stdout)에서 "connected to 127.0.0.1:5000" 확인.
5.  `nc` 터미널에 한 줄 입력:

    ```
    {"cmd":"produce_marine"}
    ```

6.  게임 화면에서 마린 1기가 배럭에서 생산되는지 확인.
7.  반복: 같은 줄을 다시 입력 → 또 한 기 생산.

**체크포인트 A6 통과 조건 = MVP-A 완료**: 위 6단계가 처음 시도에서 마린을 띄우고, 7단계가 두 번째 마린을 띄운다. BWAPI 에러 로그 없음.


## 디버깅 빠른 확인

증상별 첫 번째 의심처:

-   **봇 로그에 "connected" 메시지가 안 뜬다** → `nc -l -k 5000`이 정말 listen 중인지 (`ss -tlnp | grep 5000`), Wine 안의 봇이 host의 localhost에 닿는지.
-   **`{"cmd":"produce_marine"}` 입력 후 아무 반응이 없다** → 봇 로그에 라인이 도착했는지 (A5 echo 동작이 살아있는지), JSON 파싱 에러가 났는지, `Broodwar->self()->getUnits()`가 비었는지.
-   **`getUnits()`가 비어 있다** → 맵의 배럭 소유자가 Player 1인지 ScmDraft에서 재확인 (ADR-007의 1순위 실패 모드).
-   **마린이 안 나오고 `getLastError()`가 `Insufficient_Minerals`** → 맵 미네랄 설정 / 매치가 정말 그 맵을 로드했는지.
-   **두 번째 매치부터 봇이 명령에 반응하지 않는다** → 봇의 재연결 루프가 누락 (ADR-004).


## MVP-B 실행 절차

MVP-B 설계가 확정된 뒤 이 섹션에 추가한다. PTT 키 바인딩, faster-whisper 모델 로드, Python 서비스 기동 명령어 등이 들어갈 자리.
