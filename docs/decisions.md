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

**Status**: Superseded by ADR-020 (개발 일정·진행 기록을 roadmap.md/CHANGELOG.md로 분리)

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


## ADR-020: 진행 기록을 roadmap.md(계획) + CHANGELOG.md(나간 것)로 분리, AGENTS.md는 인덱스만 ([ADR-010](#adr-010) 일부 대체)

**Status**: Accepted

**Context**: MVP 완료 후 기능 확장 단계로 넘어간다. [ADR-010](#adr-010)은 AGENTS.md에 "개발 일정"(체크박스 일람)을 두었는데, 이는 MVP의 고정된 A1~B5 목록에는 맞았으나 (1) 장기 비전과 미래 마일스톤을 담을 곳이 없고, (2) 완료 목록이 인덱스 문서를 비대하게 만들며, (3) "계획"과 "나간 것"이 한 체크박스에 뭉개져 있었다.

**Decision**:

-   **`docs/roadmap.md`** — 장기 계획. 마일스톤(coarse) 단위, 시간순 단일 축(오래된 것이 위). 헤더 옆 상태 배지 `== Done == / == Active == / == Planned ==`. 진행 중 마일스톤만 잠정 하위 체크리스트. 하위 단계 마크 `[x]`/`[ ]`/`[c]`(취소·대체, 삭제하지 않고 `~~취소선~~` + 이유). 완료 마일스톤도 체크리스트째 보존.
-   **`CHANGELOG.md`**(리포 루트) — 나간 것 기록. 역시간순(최신이 위), 마일스톤 헤더에 날짜, 워크트리(브랜치) 단위 항목 + ADR. 무엇이 실제로 나갔는지의 권위 기록. roadmap의 잠정 목록과 어긋나면 CHANGELOG가 맞다.
-   **AGENTS.md** — 개발 일정 섹션 삭제. 개요 + 문서 인덱스 + 유지 규칙(체크포인트 완료 의식 포함) + 에이전트 규칙만 남긴다.
-   README.md, CHANGELOG 자동 생성은 보류(roadmap "미뤄둔 것").

**Rationale**: 계획(forward, 비전·취소 흔적 포함)과 나간 것(backward, 깔끔한 출고 목록)은 수명과 독자가 다르다. "어디로 가나"는 roadmap을 위에서 아래로, "최근 뭐가 바뀌었나"는 CHANGELOG를 위에서 읽는다(정렬 방향이 반대인 게 의도). 진행 중 작업은 git 브랜치 + `plans/active/`가 이미 추적하므로 별도 라이브 백로그는 두지 않는다(썩는다).

**Consequences**: 체크포인트 완료 시 갱신 지점이 늘어난다(plan→done, roadmap, CHANGELOG, 필요 시 architecture/decisions). AGENTS.md "문서 유지 규칙"의 완료 의식이 이 순서를 강제한다. 미래 마일스톤(MVP-C+)은 별도 세션에서 설계해 roadmap에 채운다.


## ADR-021: 음성 melee 플레이는 "지휘관 puppet" 모델 — 플레이어가 두뇌, 봇이 실행자, 재미가 목표

**Status**: Accepted

**Context**: MVP가 끝나고 "플레이어가 실제로 테란 melee 게임을 음성으로 플레이"하는 단계로 넘어간다. melee 한 판은 경제·건설·생산·정찰·교전·테크를 모두 요구한다. 음성이 *유일 입력*인지 마우스/키보드를 *보조*하는지, 그리고 군대를 누가 통제하는지가 전체 프로젝트의 성격을 가른다.

**Decision**: **지휘관 모델** — 플레이어가 두뇌, 봇이 손발이다. 플레이어는 의도를 말하고(무엇을·어디로), 봇이 공간적 세부를 채워 충실히 실행한다. 단, **봇은 스스로 *목표*나 *대상*을 고르지 않는다** — 플레이어가 준 *무엇*의 *어떻게*만 실행한다. 군대는 플레이어가 명령하지 않으면 (게임 기본 동작 이상으로) 움직이지 않는다. **성공 척도는 승률이 아니라 "음성으로 melee를 두는 것이 재미있는가"** 이다.

**Rationale**: 다른 길은 둘 다 막혔다. 음성을 *유일한* 입력으로 삼으면 유닛 선택·위치 지정·실시간 마이크로라는 미해결 난제에 빠진다. 반대로 음성을 마우스의 *보조* 단축키로만 쓰면 음성이 부차적 도구가 되어 프로젝트의 의의를 잃는다. 지휘관 모델은 기존 설계의 강점("봇이 대상 유닛·건물을 고른다")을 자연스럽게 확장하면서 플레이어를 *의도* 수준에 머물게 한다 — 음성이 실제로 잘하는 층위다. 봇을 *자율 플레이어*가 아니라 *손발*로 두는 것이 핵심이다 — 강한 자율 봇을 만드는 건 이미 수많은 사람이 매달린 거대한 일이고, 그 위에 음성을 얹으면 음성은 곁가지가 된다. 이 프로젝트가 소유할 새 질문은 "사람이 음성 의도만으로 melee를 둘 수 있는가"이고, 이는 사람이 실제로 운전할 때만 성립한다. **재미를 척도로 두면** 가장 어려운 제약(음성 지연, 실시간 마이크로의 불가능성)이 *치명적 결함*에서 *설계 파라미터*로 바뀐다 — 고수에게 질지언정 매끄럽게 느껴지는 속도와 분업을 고를 수 있다.

**Consequences**: 플레이어가 느리거나 침묵하면 군대는 멍청하고 진다 — 그 마찰 자체가 프로젝트의 연구 질문이다. 봇은 "얇은 번역기"(자체 의사결정 없음, [architecture.md](architecture.md))라는 기존 테제를 유지하되, *실행*(스쿼드 통제·건물 배치)은 책임진다. 자율 전략 엔진은 명시적으로 범위 밖.


## ADR-022: 스쿼드는 봇 소유 레지스트리, 술어로 선택, 명령 1회 발행, auto-run 없음

**Status**: Accepted

**Context**: puppet 모델([ADR-021](#adr-021))에서 플레이어는 "마린으로 6시 공격" 같은 명령을 낸다. *어떤* 유닛인지 지정해야 하고(선택 문제 — BWAPI에 네이티브 control group 개념 없음, `getID()`/`exists()` + 술어 필터만 제공), 명령 후 군대가 침묵 구간에도 계속 실행돼야 하며, 나중에 그 부대를 다시 참조할 수 있어야 한다. 동시에 LLM 에이전트는 느려 프레임 루프에 못 들어간다.

**Decision**:

-   **봇(C++)이 스쿼드 레지스트리 소유**: `squad_id → {살아있는 유닛 ID 집합, 마지막 발행 명령}`. 봇은 게임 진실의 단일 출처이자 유일한 BWAPI 리더.
-   **선택은 항상 봇이 평가하는 술어(predicate)**: 음성 해석 층은 유닛을 일일이 열거하지 않는다. `create_squad(select-predicate, order)` 가 명령 *시점*에 술어(`getType()==Marine && isIdle()` 등)를 평가해 구체 유닛 ID를 모아 스쿼드를 만들고 **불투명한 `squad_id` 를 반환**한다. **개수/비율 지정**도 포함(스쿼드의 N기/절반 등 — 봇이 결정적 규칙으로 선택, 예: ID가 낮은 N개).
-   **분리 = 새 스쿼드**: 스쿼드의 부분집합이 새 명령을 받으면 원 스쿼드에서 떨어져 나와 **독립한 새 스쿼드**가 된다(스쿼드 = 같은 task 를 공유하는 유닛). 부모/자식 트리·supersede 의미론 없음.
-   **명령 1회 발행, auto-run 없음**: 각 명령은 **한 번** 발행하고 BW 의 네이티브 명령 지속성(예: `Gather` 는 자원 고갈까지 끈질김, attack-move 는 경로상 교전)에 의존한다. 봇은 프레임마다 명령을 *재발행하지 않는다*. 매 프레임 작업은 **죽은 멤버 정리(`exists()`) + 새 요청 처리**뿐. 봇은 시키지 않은 어떤 standing behavior 도 주입하지 않는다.
-   스쿼드는 **로스터 + 마지막 발행 명령 기록**이지 프레임별 컨트롤러가 아니다.

**Rationale**: 유닛 ID는 매 프레임 바뀌는 빠른 데이터다 — 느린 LLM이 직접 들고 있으면 프레임마다 `exists()`로 갱신하지 못해 스쿼드 상태를 *상상*하게 된다(결정성 위배). 그래서 빠른 쪽(봇)이 ID를 들고, 느린 쪽(음성 해석 층, 추후 LLM)은 *손잡이*(`이름표 → squad_id`)만 든다. auto-run을 없앤 근거: 진짜 끝없는 반복 작업은 *게임이 이미* 자동화한다(채취는 자원 고갈까지 무한 지속) — 거기에 봇의 자동 채취를 더하는 건 게임이 푼 걸 다시 푸는 것이다. 명령을 한 번만 발행하면 봇은 "시킨 것만 한다"는 결정적 동작이 되고 단순해진다.

**Consequences**: id로 스쿼드를 가리키는 건 스쿼드 엔진 마일스톤부터 가능하다(봇이 레지스트리를 소유하므로). *이름·서술*로 가리키는 건 LLM의 기억이 필요해 그때까지 보류한다([ADR-026](#adr-026)). 명령이 끝나거나 끊긴 뒤 *다시 시켜야* 하는 상황(예: 정지시킨 유닛은 영원히 놀고 있음)은 의도된 동작이다 — 필요하면 플레이어가 새 명령을 낸다. 봇 측 신규 프로토콜: `create_squad(select, order)→id`, `retask_squad(id, order)`, `query_squad(id)`, 빈 스쿼드는 자동 소멸.


## ADR-023: IPC는 요청/응답 + 상관 id, pull 전용 (ADR-005/019 개정)

**Status**: Accepted ([ADR-005](#adr-005), [ADR-019](#adr-019) 개정)

**Context**: 기존 IPC는 단방향 fire-and-forget이다(Python → JSON 라인 → 봇 실행, 응답 없음, 봇 미연결 시 드롭). 지휘관 puppet 모델([ADR-021](#adr-021))은 (1) `create_squad` 가 **squad_id 반환**을 요구하고, (2) 현재 게임 상태를 **질의**해야 하며(자원·스쿼드 상태), (3) 모호할 때 플레이어에게 되묻기를 요구한다 — 모두 요청에 응답이 따라야 한다. 한편 봇은 여전히 단일 스레드라 BWAPI 호출은 메인 루프(`update()` 직후)에서만 가능하다([ADR-005](#adr-005) 불변).

**Decision**:

-   **토폴로지 불변**: 봇=TCP 클라이언트, Python=서버, **소켓 1개**([ADR-004](#adr-004) 유지). 네 에이전트(향후)는 **in-process Python 객체**, 별도 프로세스 아님.
-   **요청/응답 + 상관 `id`**: `{id, cmd, …}` → `{id, ok, …}`. 봇이 `id` 를 에코해 응답을 요청에 매칭. JSON-RPC 형태.
-   **in-process dispatcher** 가 소켓을 소유, 나가는 요청에 `(agent, id)` 태그, 들어온 응답을 요청한 주체의 큐로 팬아웃. 에이전트는 소켓을 직접 만지지 않는다.
-   **봇은 프레임마다 수신 버퍼를 비운다**(`update()` 직후), 요청을 순서대로 실행하고 응답한다. **더는 드롭하지 않는다.**
-   **pull 전용**: 모든 에이전트 메시지가 봇 응답을 받는다. **push/event 스트리밍은 보류**(전투 중 능동 알림 없음 — 묻기 전엔 모름, 재미 우선 단계에선 허용).

**Rationale**: 요청/**응답**이 되는 순간 응답이 *발신자*를 찾아야 한다 — 네 발신자가 한 파이프를 공유하므로 `id` 상관이 필수(거의 공짜). 폴링 유지는 [ADR-005](#adr-005) 제약 그대로(단일 스레드, BWAPI 는 프레임 루프에서만). 에이전트가 in-process 라 새 소켓·새 IPC 발명 없이 dispatcher 하나만 추가하면 된다. push 보류는 event-driven 복잡도(에이전트가 능동적으로 깨어나는가?)를 미루고, 플레이어가 화면을 보는 단계에선 갭이 견딜 만하다.

**Consequences**: 봇 TCP I/O 가 "라인 폴 후 발사"에서 "요청 수신→실행→응답"으로 바뀐다 — 프레이밍·응답 상관·드롭 금지. [ADR-005](#adr-005)의 폴링/단일 스레드 결론과 [ADR-004](#adr-004)의 토폴로지는 유효하나, [ADR-019](#adr-019)의 fire-and-forget 드롭 정책은 폐기된다. pull 전용 갭(전투 중 무알림)은 알려진 부채.


## ADR-024: 공간 지시는 시계 방향 + 명명 랜드마크만

**Status**: Accepted

**Context**: 모든 명령(`build`, `create_squad(attack X)`, "그 스쿼드 Y 로")은 결국 *어디*로 귀결되는데 음성엔 마우스가 없다. 위치를 결정적으로 부르는 방법을 정해야 한다.

**Decision**: **시계 방향**("6시", "11시" → 맵 영역) + **명명 랜드마크**("내 본진", "앞마당", "내 ramp", "적 본진" → BWAPI base/choke 위치)만 사용한다. 이동/공격 대상도, 건물 배치 구역도 이 둘로 지정한다. 봇이 시계→영역, 랜드마크→위치로 해석하고, **건물은 플레이어가 타일을 찍지 않는다** — 의도 + 대략적 구역을 주면 봇 Building 매니저가 적법 타일을 고른다.

**Rationale**: 스쿼드 대상은 대략적 지정으로 충분하다("6시 공격" → 봇이 경로탐색). 건물은 플레이어가 정확 타일을 거의 신경 쓰지 않고 *의도*를 신경 쓴다 — 봇은 어차피 적법 배치(`canBuildHere`)를 풀어야 하므로 의도 + 구역이 자연스럽다. **지시대명사**("미네랄 뒤")는 봇이 기하를 *상상*하게 해 결정성을 깨고, **좌표 그리드**("G7에 지어")는 지휘관 판타지를 부순다 → 둘 다 보류.

**Consequences**: 봇의 Building 매니저가 실체 있는 컴포넌트가 된다("(건물 타입, 대략적 구역) → 적법 타일"을 푸는 배치 탐색, 애드온 간격, 추후 ramp 막기 등). "내 본진/내 ramp"보다 정밀한 배치나 지시대명사 지정은 보류 — 필요해지면 그때 도입한다.


## ADR-025: 명령은 대상을 호명해서 보낸다 (한 명령 = 한 대상)

**Status**: Accepted

**Context**: LLM 단계([ADR-026](#adr-026))에 가면 명령을 받는 쪽이 책임별로 여러 개로 나뉜다(생산 담당, 건설 담당, 전투 담당 등 — 정확한 구성은 미정). 그런데 음성은 한 줄기 텍스트로 들어온다. "마린 3기 뽑아"가 어느 담당에게 가야 하는지 정하는 방법이 필요하다.

**Decision**: 플레이어가 명령 앞에 **대상을 직접 부른다**: `"생산 담당, 마린 3기"`. 시스템은 그 이름표를 보고 해당 담당에게 그대로 넘긴다 — 내용을 해석해 알아서 분배하지 않는다. **한 번의 발화는 한 대상에게만** 간다(한 문장이 여러 담당을 동시에 움직이지 않는다).

**Rationale**: 대안은 두 가지였다 — (a) 내용을 읽고 알아서 올바른 담당을 고르는 라우터, (b) 모든 담당에게 뿌리고 각자 "내 일인가?" 판단하기. 둘 다 *추측하는* 부품을 새로 들인다. 이 프로젝트의 담당들은 의도적으로 단순하고 추측하지 않게 설계하므로([ADR-021](#adr-021)), 이름표로 직접 보내는 쪽이 결정적이고 단순하다. 매번 이름을 부르는 번거로움은 작고, 무전 호출처럼 들려 지휘관 느낌과도 맞는다.

**Consequences**: 한 문장으로 두 담당에 걸치는 복합 명령은 불가 — 이름 붙인 명령 두 개로 나눠 말한다. 담당을 *몇 개로, 어떤 책임으로* 나눌지는 아직 정하지 않았다(스타크래프트 봇 커뮤니티의 매니저 계층에서 빌린 아이디어일 뿐 확정 아님) — LLM 작업 착수 전 별도 세션에서 정한다([ADR-026](#adr-026)).


## ADR-026: 봇 실행 층을 먼저, 음성 해석은 키워드 NLU로 시작해 나중에 LLM으로 교체

**Status**: Accepted

**Context**: 시스템은 두 층으로 나뉜다. **(1) 음성 해석 층** — STT가 받아쓴 문장을 봇 명령(JSON)으로 바꾼다. 지금은 키워드 패턴 매칭([ADR-018](#adr-018))이고, 장기적으로는 LLM(기억·되묻기·복합 명령 가능)으로 바꾸고 싶다. **(2) 봇 실행 층** — 스쿼드 관리·건물 배치·게임 상태 조회. 이 (2)는 (1)이 키워드든 LLM이든 *똑같이 필요*하다. 둘 중 무엇을 먼저 만들지가 문제다.

**Decision**:

-   **봇 실행 층 먼저, 음성 해석은 키워드 NLU로**: 스쿼드 엔진·요청/응답 IPC·건물 배치를 먼저 만들어 실제 플레이로 검증한다. 그 동안 음성 해석은 키워드 NLU로 둔다. LLM은 아직 도입하지 않는다.
-   **스쿼드 엔진 마일스톤**: 요청/응답 IPC + 스쿼드 레지스트리 + 술어 선택 + 랜드마크 + `gather`/`move`/`stop`. 키워드 NLU로 구동.
-   **생산·건설 마일스톤**: 명령 종류를 넓힌다 — `train` 확장(+선행 건물 사슬), `build` + 배치 엔진. 같은 스쿼드 자료구조 재사용. 여전히 키워드 NLU.
-   **LLM 전환 시점**: 위 두 마일스톤을 내보낸 뒤 판단한다.
-   **스쿼드 참조**: **id로 가리키는 건 스쿼드 엔진 단계부터** 된다(봇이 레지스트리를 소유하므로). 반면 **이름·서술로 가리키는 것**("북쪽으로 보낸 그 부대")은 기억을 가진 LLM이 있어야 가능하므로 그때까지 없다.

**Rationale**: 봇 실행 층은 음성 해석이 무엇이든 필요하므로 먼저 지어도 낭비가 아니다 — 핵심 골격을 실제 플레이로 *느껴보며* 검증한 뒤에 LLM에 투자한다. 키워드 NLU만으로도 봇에 직접 JSON을 흘려넣어(MVP-A의 `nc`처럼) 봇 실행 층 전체를 테스트할 수 있고, 나중에 음성 해석을 키워드→LLM으로 갈아끼워도 봇은 건드리지 않는다. id 참조와 이름 참조를 구분해 둔 이유: "LLM 없이는 스쿼드를 못 가리킨다"는 오해를 막기 위해서다 — id로는 가리킬 수 있다. LLM이 더해주는 건 *이름으로 부르는 편의*지, 가리키는 *능력 자체*가 아니다.

**Consequences**: 두 봇-실행 마일스톤은 LLM의 기억·되묻기·standing instruction 없이 키워드 NLU로 진행한다. 스쿼드 엔진 데모의 "절반을 가리켜 이동"은 *한 번의 연속 데모 세션* 안에서만 성립한다(그 세션 동안 squad_id를 손에 들고 있으니까) — 시간을 건너뛴 "아까 그 부대" 참조는 아니다. 전환 결정은 두 마일스톤을 내보낸 경험을 보고 내린다.


## ADR-027: IPC 와이어 프로토콜 — 요청/응답 봉투 + 선택 술어 문법

**Status**: Accepted

**Context**: MVP-A는 명령이 `{"cmd":"produce_scv"}` 하나뿐이라 와이어 포맷을 따로 정할 필요가 없었다. 이후 마일스톤은 명령(`create_squad`/`retask_squad`/`build`/`train`)과 질의(`query_squad`/자원)가 여럿이고, 모두 **공통 봉투**(요청/응답 + 상관 `id`, [ADR-023](#adr-023))와 **공통 선택 술어**([ADR-022](#adr-022))를 공유한다. 이 두 가지는 *교차 관심사*라, 각 체크포인트 플랜이 따로 발명하면 필드 이름·구조가 갈라진다. 명령별 세부 스키마가 아니라 **봉투와 술어 문법만** 먼저 못 박는다(나머지는 각 플랜이 정의).

**Decision**:

**1. 요청/응답 봉투** ([ADR-023](#adr-023)). 모든 메시지는 JSON 한 줄(`\n` delimited), 양방향 동일 봉투.

-   요청: `{"id": <int>, "cmd": "<name>", ...args}` — `id`는 음성 해석 층이 매기는 단조 증가 정수, 응답 매칭용.
-   성공 응답: `{"id": <같은 int>, "ok": true, ...result}`.
-   실패 응답: `{"id": <같은 int>, "ok": false, "error": "<reason>"}` — 봇 크래시 대신 항상 응답(파싱 실패·미지 cmd·BWAPI 거부 등).
-   봇은 `id`를 그대로 에코한다. 요청 없는 push 메시지는 없다(pull 전용, [ADR-023](#adr-023)).

**2. 선택 술어**(select-predicate, [ADR-022](#adr-022)). 유닛 집합을 *기술*하는 객체. 봇이 명령 시점에 평가해 구체 유닛 ID로 환원한다. 음성 해석 층은 유닛을 열거하지 않는다.

-   필드(모두 선택적, AND 결합):
    -   `"type"`: BWAPI UnitType 키워드 — `"scv"`, `"marine"` 등.
    -   `"state"`: 상태 술어 — `"idle"`, `"gathering"`, `"attacking"` 등(BWAPI `is*()`에 대응).
    -   `"squad"`: 기존 `squad_id` — 그 스쿼드 멤버로 한정.
    -   `"count"`: 정수. 매치 중 N기만(봇이 결정적으로 선택, 예: ID 낮은 N개).
    -   `"fraction"`: `0<f≤1`. 매치 중 비율(예: `0.5` = 절반). `count`와 동시 지정 금지.
-   예: `{"type":"scv","count":4}` (SCV 4기), `{"squad":1,"fraction":0.5}` (스쿼드 1의 절반), `{"type":"marine","state":"idle"}` (노는 마린 전부).

**3. 위치 인자**(공간 지시, [ADR-024](#adr-024)). 명령의 대상 위치는 문자열 토큰으로 표현, 봇이 좌표로 해석.

-   시계 방향: `"6oclock"` … `"12oclock"`. 명명 랜드마크: `"my_main"`, `"my_natural"`, `"my_ramp"`, `"enemy_main"`, `"command_center"` 등.

**범위 밖(각 플랜이 정의)**: 명령별 인자 스키마(`create_squad`의 `order` 객체 모양, `build`의 인자 등), 랜드마크 토큰의 BWAPI 해석 방법, 에러 문자열 목록.

**Rationale**: 봉투와 술어는 *모든* 명령에 공통이라 한 곳에 고정하지 않으면 체크포인트마다 재발명되어 어긋난다(MVP-A는 명령 1개라 이 문제가 없었다). 명령별 세부까지 지금 정하면 쓰이기 전에 추측으로 굳어져 [CLAUDE.md "Simplicity First"]에 어긋난다 — 그래서 교차 관심사만 정하고 나머지는 실제 구현하는 플랜에 맡긴다. `id` 에코는 [ADR-023](#adr-023)의 요청/응답 상관을 와이어로 실현한 것일 뿐이다. 술어를 `count`/`fraction`/`squad`까지 포함해 정의해 두면 스쿼드 엔진 데모의 "절반 분리"가 새 메커니즘 없이 표현된다.

**Consequences**: 각 체크포인트 플랜은 이 봉투·술어를 *참조*하고 자신의 명령 인자만 정의한다. 술어에 필드를 더해야 하면(예: `state` 종류 추가) 이 ADR을 갱신해 단일 출처를 유지한다. 키워드 NLU가 내보내는 JSON도, 추후 LLM이 내보내는 JSON도 같은 봉투·술어를 쓴다([ADR-026](#adr-026)) — 음성 해석 층 교체가 와이어 포맷을 건드리지 않는다.
