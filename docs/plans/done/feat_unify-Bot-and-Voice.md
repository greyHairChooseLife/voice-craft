# B5 — 전체 음성 경로 결선 (MVP-A + MVP-B 통합)

음성만으로 SCV 생산. PTT 캡처 → STT → NLU → 봇 송신을 한 프로세스에서 결선한다 ([ADR-015](../../decisions.md#adr-015)).

## 배경

B1~B4 로 각 단(서버·PTT·STT·NLU)이 개별 검증됐고, 결선에 필요한 인프라도 이미 존재했다.

-   `server.submit()` — 워커→루프 스레드 브리지 (`call_soon_threadsafe`, ADR-015) — **이미 구현됨**.
-   `nlu.match()` — 명령 이름(`"produce_scv"`) 또는 `None` 반환.
-   `_on_utterance` — 워커 스레드에서 STT+NLU 까지 수행, **로그만** 하고 송신 안 함.

B5 는 마지막 한 줄 결선 + stdin 펌프 은퇴.

## 변경

1.  `voice/voice_craft/__main__.py`
    -   `_make_on_utterance(stt, server)` — NLU 매칭 시 `server.submit(json.dumps({"cmd": cmd}))` 호출.
        명령 이름 → 와이어 JSON 변환을 진입점에서 수행 (nlu/server 불변).
    -   stdin 펌프(`_pump_stdin`) 및 `sys` import 제거 — 음성 전용.
    -   `_main` 이 `server.serve_forever()` 단독 await (TaskGroup 불필요).
2.  문서
    -   `AGENTS.md` — B5 체크박스 완료.
    -   `docs/architecture.md` — 디렉터리 트리에 capture/stt/nlu 추가, `__main__.py` 설명 갱신, pyproject 코멘트 갱신.
    -   `docs/runbook.md` — B1 절에 "stdin 은퇴" 노트.

## 와이어 포맷

봇(`bot/src/main.cpp`)은 `{"cmd":"<name>"}` 한 줄을 파싱 — MVP-A 포맷 그대로. 변경 없음.

## 검증

-   `python3 -m py_compile` 통과.
-   런타임 검증(게임+봇+음성)은 X11·Wine 필요 — runbook [반복 실행](../../runbook.md#반복-실행) 절차로 사용자가 수행:
    `,` → "produce SCV" → `,` → CC 가 SCV 1기 생산. `tcp: sent produce_scv` 로그.

## 결정

-   새 ADR 없음 — B5 는 [ADR-015](../../decisions.md#adr-015)(2-스레드 + 브리지)의 구현이지 새 결정이 아니다.
