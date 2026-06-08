# 로드맵

장기 계획. "이 도구가 어디로 가는가"를 마일스톤 단위로 본다. 완료된 작업의 *세부 기록*은 [CHANGELOG.md](../CHANGELOG.md), 현재 구조는 [architecture.md](architecture.md), 결정 이유는 [decisions.md](decisions.md).


**document guide**

-   **마일스톤** - 굵은 단위 목표. `##` 헤더 + 이름 옆 상태 배지. 위에서 아래로 시간순(오래된 것이 위, 미래가 아래).
-   **상태 배지** - 마일스톤 헤더 옆:
    -   `== Done ==` 완료
    -   `== Active ==` 진행 중 (체크리스트에 `[x]`/`[ ]` 가 섞여 있는 마일스톤)
    -   `== Planned ==` 예정 (아직 잘게 쪼개지 않음)
-   **하위 단계 마크** - 마일스톤 아래 체크리스트:
    -   `[x]` 완료
    -   `[ ]` 예정
    -   `[c]` 취소·대체됨 - `~~취소선~~` + 짧은 이유. **삭제하지 않는다.**
-   하위 단계는 진행 중 바뀔 수 있다. 바뀐 단계는 지우지 말고 `[c]`로 표시해 흔적을 남긴다.
-   진행 중 마일스톤만 잠정 체크리스트를 가진다. 잠정 목록은 *계획*이며, 실제로 무엇이 나갔는지의 권위 기록은 CHANGELOG다 (둘이 어긋나면 CHANGELOG가 맞다).


## MVP  == Done ==

음성 명령 "produce SCV" 하나로 스톡 melee Command Center에서 SCV 1기 생산. 봇 경로(A)와 음성 경로(B) 두 단계로 진행.

-   [x] A1. Wine + BW 실행 확인 (메인 메뉴 도달) - `chore_wine-and-BW`
-   [x] A2. injectory로 BWAPI 인젝션 검증 - `chore_wine-and-BW`
-   [x] A3. MinGW(Docker) + BWAPI Client API 봇 .exe - `chore_bot-boilerplate`
-   [x] A4. 비차단 TCP 클라이언트 + 라인 버퍼 - `feat_non-block-tcp-client-reading-receive-buffer`
-   [x] A5. JSON 디스패치 → SCV 생산 - `feat_json-dispatch`
-   [x] B1. `voice/` 스캐폴드 + asyncio TCP 서버 (:5000) - `feat_tcp-part-of-voice-server`
-   [x] B2. PTT 캡처 (`,` 토글 + 마이크) - `feat_capture-keyboard-input`
-   [x] B3. faster-whisper STT (`base.en`) - `feat_STT-with-fast-whisper`
-   [x] B4. 키워드 NLU → `produce_scv` JSON - `feat_NLU-by-pattern-matching`
-   [x] B5. 전체 경로 결선, 음성만으로 SCV 생산 - `feat_unify-Bot-and-Voice`
