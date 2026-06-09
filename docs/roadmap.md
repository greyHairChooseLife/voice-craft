# 로드맵

장기 계획. "이 도구가 어디로 가는가"를 마일스톤 단위로 본다. 완료된 작업의 *세부 기록*은 [CHANGELOG.md](../CHANGELOG.md), 현재 구조는 [architecture.md](architecture.md), 결정 이유는 [decisions.md](decisions.md).


**document guide**

-   **마일스톤** - 굵은 단위 목표. `##` 헤더 + 이름 옆 상태 배지. 위에서 아래로 시간순(오래된 것이 위, 미래가 아래).
-   **상태 배지** - 마일스톤 헤더 옆:
    -   `== Done ==` 완료
    -   `== Active ==` 진행 중 (체크리스트에 `[x]`/`[ ]` 가 섞여 있는 마일스톤)
    -   `== Planned ==` 예정 (아직 잘게 쪼개지 않음)
-   **하위 단계 마크** - 마일스톤 아래 체크리스트:
    -   `- [x]  ` 완료
    -   `- [ ]  ` 예정
    -   `- [c]  ` 취소·대체됨 - `~취소선~` + 짧은 이유. **삭제하지 않는다.**
-   하위 단계는 진행 중 바뀔 수 있다. 바뀐 단계는 지우지 말고 `[c]`로 표시해 흔적을 남긴다.


## MVP  == Done ==

음성 명령 "produce SCV" 하나로 스톡 melee Command Center에서 SCV 1기 생산. 봇 경로(A)와 음성 경로(B) 두 단계로 진행.

- [x]   A1. Wine + BW 실행 확인 (메인 메뉴 도달) - `chore_wine-and-BW`
- [x]   A2. injectory로 BWAPI 인젝션 검증 - `chore_wine-and-BW`
- [x]   A3. MinGW(Docker) + BWAPI Client API 봇 .exe - `chore_bot-boilerplate`
- [x]   A4. 비차단 TCP 클라이언트 + 라인 버퍼 - `feat_non-block-tcp-client-reading-receive-buffer`
- [x]   A5. JSON 디스패치 → SCV 생산 - `feat_json-dispatch`
- [x]   B1. `voice/` 스캐폴드 + asyncio TCP 서버 (:5000) - `feat_tcp-part-of-voice-server`
- [x]   B2. PTT 캡처 (`,` 토글 + 마이크) - `feat_capture-keyboard-input`
- [x]   B3. faster-whisper STT (`base.en`) - `feat_STT-with-fast-whisper`
- [x]   B4. 키워드 NLU → `produce_scv` JSON - `feat_NLU-by-pattern-matching`
- [x]   B5. 전체 경로 결선, 음성만으로 SCV 생산 - `feat_unify-Bot-and-Voice`


## 스쿼드 엔진  == Planned ==

MVP의 단발 명령("produce SCV")을 넘어, 플레이어가 *지휘관*으로 의도를 말하면 봇이 실행하는 구조로 가는 첫 걸음. 여러 유닛을 **스쿼드**로 묶어 명령하고 시간이 지나도 그 스쿼드를 다시 가리키는, 이후 모든 마일스톤이 딛고 설 봇 실행 층을 만들어 실제 플레이로 검증한다 ([ADR-021](decisions.md#adr-021)~[ADR-023](decisions.md#adr-023)). 상대는 필요 없다(스톡 melee 시작 상태가 그대로 harness). 음성 해석은 MVP의 키워드 NLU를 그대로 쓴다.

- [ ]   요청/응답 IPC - `feat_request-response-ipc`
    -   기존 단방향 fire-and-forget을 상관 `id` 기반 요청/응답으로 교체. `create_squad`가 `squad_id`를 돌려주고, 게임 상태를 질의할 수 있어야 함
    -   ADR-005/019 개정, [ADR-023](decisions.md#adr-023), [ADR-027](decisions.md#adr-027) (와이어 봉투)
- [ ]   스쿼드 레지스트리 - `feat_squad-registry`
    -   봇이 `squad_id → {유닛 ID, 마지막 명령}`을 소유. 명령 시점의 술어로 선택해 생성, id로 참조, 매 프레임 죽은 멤버 정리, 분리 시 새 스쿼드
    -   [ADR-022](decisions.md#adr-022), [ADR-027](decisions.md#adr-027) (선택 술어 문법)
- [ ]   공간 지시 + 명령 동사 - `feat_squad-commands`
    -   랜드마크("command center") 해석, `gather`/`move`/`stop`
    -   [ADR-024](decisions.md#adr-024), [ADR-027](decisions.md#adr-027) (위치 인자)
- [ ]   데모 - `feat_squad-engine-demo`
    -   SCV 4기로 스쿼드 생성 → 미네랄 채취 → 절반을 분리(새 스쿼드)해 CC 근처로 이동 → 정지. 시각 확인 + `query_squad`로 검증


## 생산·건설 확장  == Planned ==

스쿼드 엔진이 증명한 봇 실행 층 위에, **음성으로 테란 기지를 실제로 키울 수 있을 만큼** 명령 종류를 넓힌다. 새 개념은 없고 명령 표면의 *폭*만 늘린다 — 같은 스쿼드 자료구조를 재사용하고, 음성 해석도 여전히 키워드 NLU ([ADR-024](decisions.md#adr-024)).

- [ ]   유닛 생산 확장 - `feat_train-units`
    -   `train`을 SCV 너머로(마린 등). 선행 건물이 없으면 만들 수 없으므로 선행 사슬(배럭 → 마린 등)을 함께 다룸
- [ ]   건물 건설 - `feat_build-placement`
    -   `build(건물 타입, 대략적 구역)`. 플레이어는 타일을 찍지 않고, 봇 배치 탐색 엔진이 그 구역 안에서 적법한 타일을 고름
    -   [ADR-024](decisions.md#adr-024), [ADR-027](decisions.md#adr-027) (위치 인자)


## Discussion needed

-   NLU를 pattern matching에서 LLM 에이전트 방식으로 전환
-   LLM의 기억·이름 참조·되묻기 큐·standing instruction
-   봇이 먼저 알리는 알림(지금은 플레이어가 물어야만 상태를 앎)
-   지시대명사 공간 지정("미네랄 뒤")·정밀 건물 배치
