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

**Status**: Accepted

**Context**: Classic BWAPI 봇은 DLL로 빌드되고 StarCraft.exe에 주입되어야 한다. 주입 방식은 여러 가지 (Chaoslauncher / BWHeadless / 수동 인젝션).

**Decision**: Chaoslauncher의 "BWAPI Injector" 플러그인 사용. 봇 DLL은 `bwapi-data/AI/`에 배치.

**Rationale**: 모든 Classic BWAPI 튜토리얼이 전제하는 경로 → 에러 메시지 검색 가능성이 높다. MVP에는 시각적 확인(마린 등장)이 필요하므로 헤드리스 자동화가 의미 없다.

**Consequences**: 매 테스트마다 Chaoslauncher GUI 클릭 몇 번. MVP 규모에서는 허용 범위. 자동화가 절실해지면 그때 BWHeadless로 갈아탄다.


## ADR-003: 봇은 MinGW-w64로 Linux에서 크로스컴파일

**Status**: Accepted

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


## ADR-005: 봇 TCP I/O는 `onFrame`에서 폴링하는 비차단 소켓

**Status**: Accepted

**Context**: BWAPI는 단일 스레드 모델이고 워커 스레드에서의 BWAPI 호출은 정의되지 않은 동작. `onFrame`은 게임 속도에 묶여 호출되므로 블로킹 I/O 금지.

**Decision**: 비차단 소켓(`O_NONBLOCK` / `FIONBIO`)을 `onFrame`마다 `recv()`. 영구 라인 버퍼에 누적, `\n` 만날 때마다 한 명령 파싱·실행. 스레드 없음, 락 없음.

**Rationale**: localhost TCP는 마이크로초 단위로 반환되므로 워커 스레드의 이득이 없다. 워커를 둬도 BWAPI 호출은 결국 `onFrame`에서 해야 하므로 단순한 폴링이 lock-free로 충분.

**Consequences**: 루프가 한 번에 한 명령만 처리하면 자연스럽게 "프레임당 한 명령"으로 rate-limit된다. MVP 트래픽(음성 발화당 ~1 명령)에서는 문제 없음. 대량 버스트가 현실화되면 워커 + 큐로 재설계 — 사용자가 "필요 시 변경" 지점으로 명시.


## ADR-006: `produce_marine`은 가장 한가한 idle barracks 선택

**Status**: Accepted

**Context**: 명령은 유닛 *타입* 기반이며 특정 unit ID를 지정하지 않는다. 봇이 대상 배럭을 골라야 한다.

**Decision**: `Broodwar->self()->getUnits()`에서 완성된 Terran Barracks만 필터, `getTrainingQueue().size()`가 가장 작은 것을 선택, `< 5`이면 `train(UnitTypes::Terran_Marine)`. 매 호출 후 `Broodwar->getLastError()`를 로깅.

**Rationale**: "가장 한가한 idle"은 MVP 규모(배럭 1기)에서는 no-op tiebreaker지만 배럭 수가 늘어나도 코드 변경 없이 합리적으로 작동한다. `train()`은 미네랄·서플라이·큐 부족 시 조용히 실패하므로 `getLastError()` 로깅이 없으면 "왜 마린이 안 나오지?" 디버깅이 어려워진다.

**Consequences**: 큐가 5로 가득 찬 상태에서 명령을 반복하면 추가 명령은 조용히 드롭된다 (이건 의도된 동작). 로그 라인이 화면에 보여야 사용자가 이유를 안다.


## ADR-007: 테스트 맵은 ScmDraft 2로 직접 제작, 트리거 없음

**Status**: Accepted

**Context**: MVP-A 검증을 위해 통제된 시작 상태가 필요. 옵션은 자체 제작 / 기존 sandbox 맵 차용 / 매번 수동 셋업.

**Decision**: ScmDraft 2로 직접 제작. Player 1 테란 시작 위치, Player 1 소유 Terran Barracks 1기 사전 배치, 시작 미네랄 1000+, 서플라이 여유, 트리거·메시지·승패 조건 없음. Wine에서 ScmDraft가 잘 안 되면 사용자의 Windows 머신에서 제작 후 `.scx` 복사.

**Rationale**: 맵은 모든 MVP-A 반복의 harness — 일회성 제작 비용이 매 실행마다의 수동 셋업 비용을 압도. 트리거 없는 minimal 맵이 실패 원인을 봇 코드로 격리시켜준다.

**Consequences**: **배럭 소유자가 봇의 player slot(Player 1)과 일치하지 않으면** `getUnits()`가 비고 모든 명령이 조용히 실패. 첫 실행 전 BW의 "Use Map Settings" 모드에서 시각적으로 소유자를 확인할 것.


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

**Consequences**: 무료 리마스터 배포판은 이 프로젝트에 쓸 수 없다 (호환성). STARTcraft는 기본적으로 Injectory로 주입하지만 우리는 ADR-002에 따라 Chaoslauncher를 쓴다 — zip에 Chaoslauncher가 포함되지 않으면 별도 다운로드가 필요할 수 있다 (A2에서 확인). 미러 URL이 죽으면 cs.mun.ca 구 도메인이 아니라 davechurchill.ca 최신 경로를 재확인한다.
