# 결정 기록 (ADR)

각 ADR은 안정된 `adr-NNN` 슬러그를 앵커로 사용한다. 결정이 바뀔 때는 기존 ADR을 삭제하지 않고 `Status: Superseded by ADR-NNN`으로 표기한 뒤 새 ADR을 추가한다.

## ADR-001: Wine 단일 호스트에서 BW + BWAPI 실행

**Status**: Accepted

**Context**: BW 1.16.1 + Classic BWAPI는 32-bit Windows 전용. 개발 환경은 Arch Linux. 게임과 봇·음성 서비스를 어디서 돌릴지 정해야 한다.

**Decision**: Arch Linux 호스트에서 Wine으로 BW + BWAPI를 실행. 별도 Windows VM이나 듀얼 부팅을 두지 않는다.

**Rationale**: 솔로 개발자에게 마찰이 가장 적은 경로. BWAPI under Wine은 BASIL ladder 등에서 입증된 트랙. PTT 단축키, STT, C++ 봇이 한 머신에 모이고 TCP localhost가 Wine 경계를 그대로 통과한다.

**Consequences**: Wine 버전·BW 패치 레벨 핀 작업이 필요할 수 있다. "런치 자체가 안 됨" 문제의 첫 의심처는 항상 Wine 환경.

**Note (2026-06-04, Wine 11.10)**: Arch 공식 `wine`는 wow64 단일 빌드라 순수 32-bit prefix(`WINEARCH=win32`)를 만들 수 없다 (`win32 ... not supported in wow64 mode` 에러). 따라서 prefix는 `WINEARCH=win64`로 생성하고, 32-bit인 BW 1.16.1은 wine의 wow64 계층이 실행한다. BWAPI 4.4.0 인젝션이 wow64에서 정상 동작하는지는 A2에서 검증한다 — 만약 실패하면 그때 32-bit 전용 wine 빌드를 별도 옵션으로 재검토한다.


## ADR-002: 봇 DLL은 Chaoslauncher의 BWAPI Injector로 주입

**Status**: Superseded by ADR-012

**Context**: Classic BWAPI 봇은 DLL로 빌드되고 StarCraft.exe에 주입되어야 한다. 주입 방식은 여러 가지 (Chaoslauncher / BWHeadless / 수동 인젝션).

**Decision**: Chaoslauncher의 "BWAPI Injector" 플러그인 사용. 봇 DLL은 `bwapi-data/AI/`에 배치.

**Rationale**: 모든 Classic BWAPI 튜토리얼이 전제하는 경로 → 에러 메시지 검색 가능성이 높다. MVP에는 시각적 확인(마린 등장)이 필요하므로 헤드리스 자동화가 의미 없다.

**Consequences**: 매 테스트마다 Chaoslauncher GUI 클릭 몇 번. MVP 규모에서는 허용 범위. 자동화가 절실해지면 그때 BWHeadless로 갈아탄다.


## ADR-003: 봇은 MinGW-w64로 Linux에서 크로스컴파일

**Status**: Superseded by ADR-014

**Context**: 봇은 32-bit Windows DLL. 개발 머신은 Arch Linux. 컴파일을 어디서 어떻게 할지 결정해야 한다.

**Decision**: Arch에서 MinGW-w64로 크로스컴파일. CMake + 직접 작성한 toolchain 파일 + `-std=c++17`. 결과 `.dll`을 `bwapi-data/AI/`에 복사.

**Rationale**: 네이티브 Linux 빌드로 편집·빌드 루프가 빠르다. Wine을 컴파일 단계에 끌어들이지 않는다. BWAPI 헤더 + import lib는 MinGW로 잘 링크된다. 공식 예제의 `.sln`을 CMake로 옮기는 건 일회성 ~30줄 작업.

**Consequences**: 향후 의존성이 MSVC-only `.lib`만 제공하면 MinGW로 링크 불가 → 그때 재검토. MVP 범위에서는 발생하지 않는다.


## ADR-004: Python = TCP 서버, C++ 봇 = 클라이언트

**Status**: Accepted

**Context**: 두 프로세스 + IPC 구조. 어느 쪽이 listen할지 정해야 한다. BWAPI는 매치 종료 시 `AIModule`을 폐기한다.

**Decision**: Python이 서버 (`localhost:5000` listen), 봇이 클라이언트 (매치 시작 시마다 connect). 봇은 N 프레임마다 재연결 시도 로직을 첫 구현부터 포함한다. MVP-A에서는 Python 대신 `nc -l -k 5000`을 사용.

**Rationale**: Python을 서버로 두면 매치 사이에 faster-whisper 모델을 메모리에 유지할 수 있어 콜드 스타트가 없다. 봇이 서버였다면 매 매치마다 listener가 죽고 재기동되며 클라이언트(Python)의 재연결 로직이 더 복잡해진다.

**Consequences**: 봇은 재연결 루프가 필수. 누락 시 두 번째 매치부터 작동하지 않는다.

**Note ([ADR-014](#adr-014))**: 본 ADR의 Context에 적힌 "BWAPI는 매치 종료 시 `AIModule`을 폐기한다"는 AIModule(DLL) 방식 전제였다. ADR-014에서 봇이 Client API(.exe)로 바뀌면서, 봇은 AIModule이 아니라 독립 프로세스로 살아있고 매치 사이에 `BWAPIClient.connect()`를 재시도한다. "봇=클라이언트, 재연결 루프 필수"라는 결론과 Python=서버 구조는 그대로 유효하다 — 봇이 BWAPI(게임)에 재연결하는 것과, 봇이 Python(명령 소스)에 재연결하는 것은 별개의 두 연결이다.


## ADR-005: 봇 TCP I/O는 `onFrame`에서 폴링하는 비차단 소켓

**Status**: Accepted

**Context**: BWAPI는 단일 스레드 모델이고 워커 스레드에서의 BWAPI 호출은 정의되지 않은 동작. `onFrame`은 게임 속도에 묶여 호출되므로 블로킹 I/O 금지.

**Decision**: 비차단 소켓(`O_NONBLOCK` / `FIONBIO`)을 `onFrame`마다 `recv()`. 영구 라인 버퍼에 누적, `\n` 만날 때마다 한 명령 파싱·실행. 스레드 없음, 락 없음.

**Rationale**: localhost TCP는 마이크로초 단위로 반환되므로 워커 스레드의 이득이 없다. 워커를 둬도 BWAPI 호출은 결국 `onFrame`에서 해야 하므로 단순한 폴링이 lock-free로 충분.

**Consequences**: 루프가 한 번에 한 명령만 처리하면 자연스럽게 "프레임당 한 명령"으로 rate-limit된다. MVP 트래픽(음성 발화당 ~1 명령)에서는 문제 없음. 대량 버스트가 현실화되면 워커 + 큐로 재설계 — 사용자가 "필요 시 변경" 지점으로 명시.

**Note ([ADR-014](#adr-014))**: Client API(.exe) 방식에선 BWAPI `onFrame` 콜백이 없다. 대신 봇이 메인 루프에서 `BWAPIClient.update()`를 호출하면 그게 한 프레임을 진행시키고 반환한다 → 매 `update()` 직후가 본 ADR의 `onFrame` 폴링 지점에 대응한다. "비차단 소켓을 프레임마다 폴링, 라인 버퍼 누적, 단일 스레드" 결정은 그대로 유효하다. 봇은 단일 스레드 메인 루프 안에서 BWAPI `update()` + Python 소켓 polling을 함께 돈다.


## ADR-006: `produce_scv`는 가장 한가한 idle Command Center 선택

**Status**: Accepted

**Context**: 명령은 유닛 *타입* 기반이며 특정 unit ID를 지정하지 않는다. 봇이 대상 생산 건물을 골라야 한다.

**Decision**: `Broodwar->self()->getUnits()`에서 완성된 Terran Command Center만 필터, `getTrainingQueue().size()`가 가장 작은 것을 선택, `< 5`이면 `train(UnitTypes::Terran_SCV)`. 매 호출 후 `Broodwar->getLastError()`를 로깅.

**Rationale**: MVP-A의 목표는 "JSON 명령 한 줄로 BWAPI `train()` 호출을 구동할 수 있는가"의 검증뿐이다. `train(Marine)`과 `train(SCV)`는 동일한 단일 호출이라 봇 로직 복잡도는 같다. SCV를 고르면 생산 건물이 melee 시작 상태의 Command Center라 별도 테스트 맵·미네랄·배럭 사전 배치가 전부 불필요해진다([ADR-007](#adr-007)) — 검증 비용이 가장 낮다. "가장 한가한 idle"은 MVP 규모(CC 1기)에서는 no-op tiebreaker지만 건물 수가 늘어나도 코드 변경 없이 작동한다. `train()`은 미네랄·서플라이·큐 부족 시 조용히 실패하므로 `getLastError()` 로깅이 없으면 "왜 SCV가 안 나오지?" 디버깅이 어려워진다.

**Note**: 원래 명령은 `produce_marine`(생산 건물 = Terran Barracks)이었다. MVP-A를 "명령 경로 검증"으로 좁히면서, 별도 맵 제작과 배럭/서플라이/미네랄 셋업을 모두 없애기 위해 melee 기본 시작 유닛인 Command Center에서 SCV를 뽑는 쪽으로 바꿨다. Marine 데모는 실제 맵이 생기는 MVP-B에서 복귀할 수 있다.

**Consequences**: 큐가 5로 가득 찬 상태에서 명령을 반복하면 추가 명령은 조용히 드롭된다 (이건 의도된 동작). 로그 라인이 화면에 보여야 사용자가 이유를 안다.


## ADR-007: 테스트 맵 없음 — 스톡 melee 시작 상태를 harness로 사용

**Status**: Accepted

**Context**: MVP-A 검증을 위해 통제된 시작 상태가 필요. 옵션은 자체 제작(ScmDraft) / 기존 sandbox 맵 차용 / 스톡 melee 기본 시작 상태 사용.

**Decision**: 별도 맵을 만들지 않는다. 스톡 melee 맵을 테란으로 single-player 로드하면 봇 슬롯이 Command Center 1기 + SCV 4기 + 시작 미네랄(50) + 서플라이 여유를 이미 갖는다. `produce_scv`([ADR-006](#adr-006))는 이 기본 Command Center에서 SCV를 뽑으므로 사전 배치·소유자 설정·미네랄 조정이 전부 불필요하다.

**Rationale**: MVP-A는 "명령 한 줄로 `train()` 호출이 동작하는가"만 검증한다. SCV 생산으로 바꾸면 melee 기본 상태가 그대로 harness가 되어 ScmDraft 제작 비용(특히 Wine에서의 마찰)과 "배럭 소유자가 Player 1인가" 확인 단계가 통째로 사라진다. 통제된 시작 상태가 필요하다는 원래 요구는 melee 기본값이 충족한다.

**Consequences**: SCV 생산은 새 유닛이 기존 4기 SCV 사이에 등장해 시각적 확인이 마린보다 약하다 → CC 훈련 progress bar / 서플라이 카운트 증가 + `train()` 후 `getLastError()` 로그로 확인한다. 실제 통제 맵이 필요해지는 시점(MVP-B 등)에 ScmDraft 제작을 다시 도입한다.

**Note**: 원래 결정은 "ScmDraft 2로 Terran Barracks 사전 배치 맵 직접 제작"이었다. MVP-A를 명령 경로 검증으로 좁히고 생산 유닛을 SCV로 바꾸면서 맵 제작 자체를 제거했다.


## ADR-008: JSON 파싱은 nlohmann/json (single-header, vendoring)

**Status**: Accepted

**Context**: 봇은 JSON-lines를 파싱해야 한다. 라이브러리 선택지: nlohmann / RapidJSON / picojson / 수제 substring 매칭.

**Decision**: nlohmann/json `json.hpp` 한 파일을 `bot/third_party/nlohmann/`에 vendoring. 패키지 매니저 없음, 별도 링크 없음.

**Rationale**: AGENTS.md는 "JSON lines"를 프로토콜로 명시했고, 이는 필드 기반 접근을 전제로 한다. 수제 substring 매칭은 두 번째 명령이나 파라미터가 생기는 순간 무너진다. MinGW-w64에서 무난히 컴파일되고 추가 의존성이 없다.

**Consequences**: 파싱 에러는 로깅 후 해당 라인 드롭, 봇 크래시 금지. 컴파일 시간 ~1-2초 증가 (수용 가능).


## ADR-009: 저장소는 최상위 `bot/` + `voice/`, 컴포넌트 내부에 자체 `src/`

**Status**: Accepted

**Context**: 저장소 구조. 옵션은 최상위 컴포넌트 디렉터리 / 최상위 `src/`로 묶기 / 언어별 디렉터리.

**Decision**: 최상위에 `bot/`과 `voice/`. 각 컴포넌트는 내부에 자체 `src/`를 둔다 (`bot/src/`, `bot/include/`, `bot/third_party/`, `voice/<python_package>/`).

**Rationale**: AGENTS.md 어휘 ("게임 측" / "음성 측")와 일치 → 디렉터리 이름 자체가 문서가 된다. 두 컴포넌트짜리 프로젝트에 평탄한 구조가 어울린다. 컴포넌트마다 어차피 자체 `src/`가 필요하므로 최상위 `src/`로 한 번 더 감싸면 `src/bot/src/`처럼 어색해진다.

**Consequences**: 향후 컴포넌트가 늘어도 같은 패턴으로 확장 가능. 최상위 `src/`를 나중에 도입하지 않는다.


## ADR-010: 문서는 AGENTS.md (인덱스) + architecture.md (스냅샷) + decisions.md (ADR) + runbook.md (운영)

**Status**: Accepted

**Context**: MVP 시점에 어떤 문서를 만들지. 후보: contributing / architecture / features / decisions / test / runbook.

**Decision**: AGENTS.md를 얇은 인덱스 + 개발 일정 + 문서 사용 가이드로 두고, 세부는 `docs/architecture.md`, `docs/decisions.md`, `docs/runbook.md`로 분리. architecture.md는 *스냅샷*만 담고 *왜*는 모두 decisions.md로 위임 (인라인 `[ADR-NNN]` 링크). contributing.md / test.md / features.md는 내용이 생기기 전까지 만들지 않는다.

**Rationale**: 솔로 MVP 단계에서 빈 문서는 부채. 사실/이유/조작을 세 곳으로 명확히 분리하면 갱신 위치를 헷갈리지 않는다. 인라인 ADR 링크는 architecture.md의 특정 주장이 깨졌을 때 정확히 어느 ADR을 다시 봐야 하는지 알려준다.

**Consequences**: 새 결정마다 ADR 추가 + architecture.md 인라인 링크 갱신이 필요. AGENTS.md의 "문서 유지 규칙" 섹션이 이 흐름을 강제한다.


## ADR-011: BW 1.16.1은 STARTcraft 재호스팅 패키지로 확보

**Status**: Accepted

**Context**: BWAPI 4.x Classic은 BW 1.16.1 바이너리의 정확한 메모리 오프셋에 의존한다. Blizzard의 무료 StarCraft 배포판은 1.18+ 리마스터 클라이언트라 BWAPI Classic과 호환되지 않으며, 리마스터 출시 이후 공식 경로로 1.16.1을 받을 수 없다. 솔로 개발자가 정당하게 1.16.1 게임 폴더를 확보할 경로가 필요하다.

**Decision**: David Churchill(AIIDE StarCraft AI Competition 운영자)의 STARTcraft 배포 패키지를 사용한다.

-   URL: `https://davechurchill.ca/starcraft/files/startcraft/scbw_bwapi440.zip`
-   내용: BW 1.16.1 게임 파일 + BWAPI 4.4.0이 합쳐진 ~97 MB zip.
-   검증(2026-06-04): HTTP 200, `application/zip`, 101,643,261 bytes, ZIP 매직바이트 `PK\x03\x04` 정상.

**Rationale**: Blizzard가 리마스터 출시 후 AIIDE 대회용으로 1.16.1 재호스팅을 허가했고, 이 파일은 대회 운영자 본인 도메인에서 제공된다 → 정당성과 안정성 모두 확보. 게임과 BWAPI 4.4.0이 한 패키지라 A1(BW 실행)과 A2(BWAPI 설치)를 같은 자료로 진행할 수 있다. 우리 환경(Wine + MinGW-w64 + BWAPI 4.4.0)과 STARTcraft의 Linux 셋업이 일치한다.

**Consequences**: 무료 리마스터 배포판은 이 프로젝트에 쓸 수 없다 (호환성). STARTcraft는 Injectory로 주입하며 Chaoslauncher를 포함하지 않는다 → A2 검증 결과 Chaoslauncher 대신 injectory를 채택했다 ([ADR-012](#adr-012)). 미러 URL이 죽으면 cs.mun.ca 구 도메인이 아니라 davechurchill.ca 최신 경로를 재확인한다.


## ADR-012: 봇 DLL 주입은 injectory CLI (ADR-002 대체)

**Status**: Accepted

**Context**: ADR-002는 Chaoslauncher의 BWAPI Injector를 전제했다. 그러나 실제 확보한 STARTcraft 패키지([ADR-011](#adr-011))는 Chaoslauncher를 포함하지 않고 `injectory_x86.exe`(CLI 인젝터)와 주입용 bat을 제공한다. 봇 선택은 `bwapi-data/bwapi.ini`의 `ai =` 줄로 한다.

**Decision**: injectory CLI로 BWAPI.dll + WMode.dll을 StarCraft.exe에 주입한다. 봇 DLL 경로는 bwapi.ini의 `ai =`로 지정. Chaoslauncher는 쓰지 않는다.

```
wine injectory_x86.exe --launch StarCraft.exe --inject bwapi-data/BWAPI.dll WMode.dll
```

**Rationale**: injectory는 이미 패키지에 있어 추가 확보가 없다. CLI라 `mise run` 워크플로(ADR-011에서 구축)에 그대로 들어가고 A3~A6 반복 실행에서 GUI 클릭이 사라진다. ADR-002가 Chaoslauncher를 고른 두 번째 근거("MVP는 시각 확인이 필요하니 헤드리스 자동화 무의미")는 injectory를 배제하지 않는다 — injectory는 게임 화면을 똑같이 띄우고 *주입 단계만* CLI로 자동화할 뿐이다. Wine + i3 + CLI 중심 환경에 더 맞는다.

**Consequences**: 봇 전환은 bwapi.ini 편집(GUI 드롭다운 아님)으로 한다. BWAPI 위키 스크린샷은 대부분 Chaoslauncher 기준이라 GUI 튜토리얼과 1:1 대응하지 않지만, STARTcraft/BASIL 문서가 injectory 경로를 다룬다. injectory가 Wine에서 BWAPI를 정상 주입하는지는 A2에서 검증한다 ([ADR-013](#adr-013)).


## ADR-013: A2는 봇 없이 BWAPI 인젝션만 검증

**Status**: Accepted

**Context**: A2의 원래 정의는 "Chaoslauncher + ExampleAIModule 검증 (스톡 봇 동작)"이었다. 그러나 BWAPI 4.4.0 공식 배포(BWAPI.7z)는 ExampleAIModule의 **소스만** 제공하고 빌드된 `.dll`이 없다 (MSVC 빌드 전제). 빌드된 스톡 봇을 외부에서 구하는 것은 불확실하고, 우리 MinGW 툴체인은 A3에서야 들어온다.

**Decision**: A2를 "봇 없이 BWAPI 인젝션 파이프라인 검증"으로 축소한다. bwapi.ini의 `ai =`를 비운 채 injectory로 BWAPI를 주입하고, BW가 BWAPI 로드 상태로 크래시 없이 실행되는지(메뉴/게임 진입, `bwapi-data/logs/` 정상)를 확인한다. "봇이 실제로 움직인다"는 검증은 A3(자체 hello DLL)로 옮긴다.

**Rationale**: A2의 본질적 가치는 "Wine에서 BWAPI 주입 자체가 동작하는가"의 격리 검증이고, 이는 봇 없이도 달성된다. 빌드된 스톡 봇 확보는 불확실한 우회로다. 인젝션(A2)과 자체 코드 로딩(A3)을 분리해 두면 A3 실패 시 원인을 좁힐 수 있다.

**Consequences**: A2 통과 조건이 "스톡 봇이 자기 할 일을 한다"에서 "BWAPI가 주입된 채 크래시 없이 실행된다"로 바뀐다. AGENTS.md A2 항목 문구도 이에 맞춘다.


## ADR-014: 봇은 BWAPI Client API(.exe), MinGW 크로스컴파일 (ADR-003 대체)

**Status**: Accepted

**Context**: A3에서 자체 봇을 MinGW로 빌드하려다, BWAPI의 C++ `AIModule`(DLL) 인터페이스가 **MSVC 전용**임을 확인했다. C++ 네임 맹글링이 컴파일러마다 달라, MinGW로 빌드한 DLL은 주입된 BWAPI.dll과 심볼이 안 맞는다 (BWAPI 위키·포럼이 명시: `cl.exe`/`link.exe`로만 링크 가능). 또한 BWAPI 4.4.0은 prebuilt `.lib`을 동봉하지 않는다 (VS2017 호환성 문제로 제거). 이로써 ADR-003의 두 전제("헤더+import lib는 MinGW로 잘 링크된다", "봇은 DLL")가 모두 무너졌다.

**Decision**: 봇을 `AIModule` DLL이 아니라 **BWAPI Client API 기반 독립 실행파일(.exe)**로 만든다. 봇은 별도 프로세스로 실행돼 주입된 BWAPI.dll과 **shared memory + named pipe**로 통신한다. Client 라이브러리는 prebuilt가 없으므로 BWAPI 4.4.0 소스를 `bot/third_party/bwapi/`에 vendoring해 봇과 함께 MinGW로 빌드한다. 빌드는 Docker 컨테이너(Debian + g++-mingw-w64-i686 + cmake)에서 수행하고 호스트엔 MinGW를 설치하지 않는다.

**Rationale**: Client API는 봇 측 코드가 전부 봇 바이너리에 컴파일돼 들어가므로(주입 DLL과 C++ ABI를 공유하지 않음) MinGW로 빌드 가능하다 — Linux/MinGW 빌드 선례가 있다. 봇 로직 API(`Broodwar->sendText` 등)는 AIModule 방식과 동일해 produce_marine 등 상위 설계가 거의 보존된다. 컨테이너 빌드로 ADR-003의 "Wine을 컴파일에 안 끌어들인다, 네이티브 편집·빌드 루프" 의도를 유지하면서 호스트 오염도 없앤다. spike에서 ExampleAIClient.exe(PE32)가 MinGW로 끝까지 빌드됨을 검증했다.

**Consequences**:
-   봇 형태가 DLL→.exe로 바뀐다. `bwapi-data/AI/`에 두지 않고, bwapi.ini의 `ai =`는 비운 채(ADR-013 상태 유지) injectory로 게임만 주입한 뒤 봇 .exe를 Wine으로 별도 실행한다.
-   봇과 게임이 **같은 Wine prefix**에서 돌아야 shared memory(`Global\bwapi_shared_memory_*`)를 공유한다 (A3에서 검증 대상).
-   vendored 소스에 MinGW/GCC 호환 패치가 필요하다 (CommandTemp.h, SharedMemory.h — 별도 커밋). `<Windows.h>`→`<windows.h>` shim, `svnrev.h` stub도 함께 둔다.
-   onFrame 콜백 대신 봇이 메인 루프에서 `BWAPIClient.update()`로 프레임 동기화한다 ([ADR-005](#adr-005) Note 참조).
-   ADR-003을 대체한다. ADR-004(봇=TCP 클라이언트)의 "봇=클라이언트" 결론은 유지되나 근거의 AIModule 폐기 서술은 [ADR-004](#adr-004) Note로 갱신한다.


## ADR-015: 음성 서비스는 단일 프로세스 2-스레드 (asyncio TCP + 음성 워커)

**Status**: Accepted

**Context**: MVP-B의 Python 음성 서비스는 다섯 단계를 묶는다 — PTT 키 리스너 → 마이크 캡처 → faster-whisper STT → 키워드 NLU → TCP 서버(:5000, 봇에 송신). 두 가지 제약이 동시성 구조를 강제한다: (1) TCP 서버는 매치 사이에 살아남아야 하고(봇이 매치마다 재연결, [ADR-004](#adr-004)), (2) STT 추론은 CPU 바운드 블로킹 호출이다. STT가 소켓과 같은 실행 단위에 있으면 전사 중 :5000이 멈춘다.

**Decision**: TCP 서버와 음성 파이프라인을 분리하되, **별도 프로세스가 아니라 한 프로세스 안의 두 스레드**로 둔다.

-   **메인 스레드** = asyncio 이벤트 루프. `127.0.0.1:5000` TCP 서버를 돌리고, 봇 연결을 보유하며, 스레드 안전 큐에서 명령을 꺼내 봇 소켓에 쓴다. whisper 모델을 메모리에 보유(콜드 스타트 없음, [ADR-004](#adr-004) 근거 유지).
-   **워커 스레드** = PTT(`,`) 리스너 + 마이크 캡처 + whisper 전사 + NLU. 인식된 JSON 라인을 `loop.call_soon_threadsafe(...)`로 메인 루프에 넘긴다.
-   스레드→asyncio 브리지는 `loop.call_soon_threadsafe`로 처리한다.

**Rationale**: 경계를 넘나드는 것은 분당 몇 개의 작은 JSON 라인뿐이고 단방향이다. 큰 공유 상태가 경계를 넘지 않는다(whisper 모델은 워커, 봇 소켓은 메인에 각각 갇혀 있음). 스레드로 충분한 이유: faster-whisper의 무거운 추론은 CTranslate2 네이티브 코드에서 GIL을 풀어주므로 TCP 스레드가 응답성을 유지한다 — GIL 경합이 실질 문제가 아니다. 별도 프로세스로 가면 voice→(로컬 IPC)→tcp→(TCP)→봇이라 25바이트 문자열 하나를 옮기는 데 IPC를 하나 더 발명해야 한다. 프로세스의 유일한 실이익(크래시 격리)은 단일 운영자가 한 터미널을 보는 MVP 규모에서 그 배관 비용을 정당화하지 못한다.

**Consequences**: whisper 크래시가 TCP 서버도 죽인다 — MVP에선 어차피 전체 재기동이 정상 대응이므로 허용. STT를 봇/TCP 재시작과 독립적으로 살리고 싶거나 STT를 별도 머신에서 돌리고 싶어지면 그때 2-프로세스로 분리한다 ([ADR-005](#adr-005)의 "필요 시 변경" 노트와 같은 성격의 재검토 지점).


## ADR-016: PTT는 `,` 토글, X11 전역 핫키

**Status**: Accepted (Revised — 원안은 F12 누른 동안 녹음, B2 구현 중 토글로 변경)

**Context**: 트리거는 푸시-투-토크([architecture.md](architecture.md) 확정). 운영자는 StarCraft(Wine 창)에 포커스를 둔 채 게임을 하므로 PTT 키는 터미널이 아니라 **시스템 전역**에서 잡혀야 한다. 녹음 구간 정의(누른 동안만 vs 토글), 핫키 라이브러리, 게임과의 키 충돌을 정해야 한다.

**Decision**:

-   **토글 녹음**: `,` 한 번 → 마이크 스트림 시작, 다시 `,` → 정지 후 전사. 발화 동안 키를 계속 누르고 있지 않아도 된다.
-   **전역 핫키**: `pynput.keyboard.Listener`의 `on_press`/`on_release` 엣지. `on_press` 가 토글, `on_release` 는 키 리피트 가드 해제용(한 물리적 누름 = 한 토글). X11에서 동작(개발 환경은 Arch + i3 = X11). Wayland은 보안 모델상 전역 핫키가 막히므로 범위 밖.
-   **키 선택**: `,` — 운영자가 손쉽게 닿는 키.
-   **캡처 포맷**: 마이크 = 시스템 기본 입력 장치, mono 16 kHz. 콜백 청크를 메모리에 모아 `numpy` `float32` 배열로 연결 → whisper에 직접 전달. 디스크·WAV 파일 없음.

**Rationale**: 누른 동안 녹음(원안)은 긴 발화에서 키를 계속 누르고 있어야 해 UX가 불편하다 → 토글이 손에 부담이 없다. 전역 핫키는 게임에 포커스가 있어도 동작해야 하므로 필수. `pynput`은 root 불필요·pip 단독 설치라 `keyboard`(root 필요)·`evdev`(과도하게 저수준)보다 적합. `sounddevice`(PortAudio)는 16 kHz mono를 NumPy로 바로 주므로 `pyaudio`(raw bytes)보다 whisper 연결이 깔끔하다.

**Consequences**: 라이브러리 셋: `pynput` + `sounddevice` + `numpy` + `faster-whisper`. Wayland로 전환하면 전역 핫키 경로 재검토 필요. `,` 는 인쇄 가능한 키라 (1) 포커스된 텍스트 입력에 문자가 들어가고 (2) BW 단축키와 겹칠 수 있다 — 실제 게임에서 충돌 여부 확인(운영자 검증), 겹치면 키를 바꾼다. 토글은 정지 누름을 빠뜨리면 녹음이 계속되므로 `recording...`/`captured` 로그로 상태를 확인한다.


## ADR-017: STT는 faster-whisper `base.en`, CPU int8

**Status**: Accepted

**Context**: STT는 faster-whisper 로컬([ADR-004](#adr-004)). 모델 크기·device·compute_type을 정해야 한다. 두 사실이 계산을 단순화한다: (1) 음성 인식은 **영어 전용**(접근성 확장은 나중), (2) 명령 어휘가 극히 작다 — NLU가 키워드만 잡으면 되므로 STT 정확도 요구가 낮다. 머신은 **CPU 전용**(GPU 없음).

**Decision**:

-   **모델**: `base.en` (영어 전용 `.en` 모델 — 같은 크기 multilingual보다 영어에 강하고 작다).
-   **device/compute**: `device="cpu"`, `compute_type="int8"`. ~1–2초 명령 클립을 CPU에서 1초 미만으로 전사.
-   **로드**: 시작 시 1회, 워커 스레드에 상주(콜드 스타트 없음 — [ADR-004](#adr-004) 근거 실현).
-   **디코드 힌트**: `language="en"` 명시(언어 감지 생략), "SCV"로 편향하는 짧은 `initial_prompt` 옵션.

**Rationale**: 명령 어휘가 작아 `base.en`이 정확도/지연의 스위트 스폿이다. int8 양자화는 `base.en`에서 충분하고 CPU 지연을 낮게 유지한다. API STT는 [ADR-004](#adr-004)의 "로컬 모델 메모리 상주 → 콜드 스타트 없음" 근거를 무너뜨리고, PTT가 원하는 *빠르고 예측 가능한* 지연 대신 가변 네트워크 왕복(1–3초)을 들이며, 키/인증/레이트리밋 같은 MVP가 검증하지 않는 실패 모드를 추가한다 → 로컬 유지.

**Consequences**: CPU 지연이 불만이면 `tiny.en`으로 낮추고, 정확도가 불만이면 `small.en`으로 올린다(문자열 한 줄). 영어 외 언어는 범위 밖 — 다국어가 필요해지면 multilingual 모델 + `language` 동적 설정으로 재검토.


## ADR-018: NLU는 (키워드, 명령) 규칙 리스트, 동사 + 명사 부분일치

**Status**: Accepted

**Context**: NLU는 키워드 딕셔너리 + 부분일치 스캔([architecture.md](architecture.md) 확정). 입력은 STT가 준 소문자 영어 문자열(예: `"produce an scv"`, `"build s c v"`, 잡음 `"the scframework"`), 출력은 `{"cmd":"produce_scv"}` 또는 **무명령**. 규칙 구조와 매칭 엄격도를 정해야 한다.

**Decision**:

-   **구조**: `(키워드 집합, 명령)` 규칙 리스트, 순서대로 스캔. MVP-B는 production 동사(`produce`/`make`/`build`/`train`) **그리고** `scv`가 모두 있어야 발화.
    ```python
    RULES = [
        # 동사 집합 AND "scv" 가 transcript에 모두 있으면 발화
        (["produce", "make", "build", "train"], ["scv"], "produce_scv"),
    ]
    ```
-   **매칭**: 정규화(소문자화, 구두점 제거, 공백 압축) 후 부분일치 스캔. "S.C.V."도 점 제거 후 "scv" 포함.
-   **무매칭 → 무명령**: `nlu: no rule matched: "<transcript>"` 로깅. 봇에 잡음을 절대 보내지 않는다.
-   **first-match-wins**: 여러 규칙이 발화 가능하면 순서가 우선순위. 명령 1개에선 무의미하나 두 번째 명령 전에 동작을 정의해 둔다.

**Rationale**: 부분일치는 filler 단어("an", "please", "i want")를 견디는데, 그게 정확 일치 대신 키워드 NLU를 쓰는 이유다. 동사 + 명사 동시 요구는 "cancel scv"·"move scv" 같은 오발화를 막아 좀 더 의도적이다.

**Consequences**: 명령이 겹치기 시작하면(예: cancel/move도 scv를 포함) negative 키워드나 더 정교한 동사 로직이 필요하다 — 그 시점에 규칙 구조를 확장한다. 빈/공백 전사는 NLU 이전에 조기 종료(`stt: (empty)`).


## ADR-019: Python TCP 서버가 `nc`를 대체, 봇 없을 때 명령 드롭

**Status**: Accepted

**Context**: MVP-B에서 Python 서비스가 :5000 서버가 되어 MVP-A의 `nc -l -k 5000`을 은퇴시킨다([ADR-004](#adr-004)의 Python=서버 설계 실현). 봇은 클라이언트로 **매치마다 재연결**한다. 서버는 매치 전체를 가로질러 살아남으며 "봇 미연결 / 연결 / 끊김(매치 종료) / 재연결" 생애주기를 처리해야 한다. 동시에 음성 스레드가 언제든 명령을 만들어낸다.

**Decision**:

-   **asyncio 서버** `127.0.0.1:5000`, 한 번에 봇 1개 연결만 수용(봇은 항상 1개).
-   현재 봇 writer 참조를 보유: accept → 저장, disconnect → 클리어, reconnect → 교체. 두 번째 봇이 붙으면 옛 writer를 닫고 교체(단일 봇 불변식).
-   **봇 미연결 중 생성된 명령 → 드롭 + 로그**(`tcp: no bot connected, dropped: produce_scv`). 미래 연결을 위해 큐잉하지 않는다.
-   전송 = JSON 라인 1개 + `\n`(MVP-A가 검증한 와이어 포맷 그대로).

**Rationale**: 드롭-비큐잉의 근거: 30초 전에 말한 "produce SCV"가 다음 매치 시작 순간 발화하면 놀랍고 틀린 동작이다. 명령은 현재 매치에 묶인 실시간 의도이고, 이는 MVP-A의 fire-and-forget 느낌과 일치한다.

**Consequences**: `nc`는 MVP-B에서 은퇴한다(디버그 폴백으로도 두지 않음 — [AGENTS.md] done-criteria). 봇이 매치에 없을 때 말한 명령은 사라지므로 운영자는 봇 로그에서 매치 진입을 확인한 뒤 말한다. 명령을 버퍼링하고 싶어지면 그때 "마지막 명령만 connect 시 flush" 같은 정책으로 재검토.
