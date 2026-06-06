# B4 — 키워드 NLU (동사 집합 + "scv" 부분일치 → `produce_scv`) — 완료

worktree `feat_NLU-by-pattern-matching`. B3(캡처 버퍼 → faster-whisper 전사)에 이어, 전사 텍스트를 `(키워드, 명령)` 규칙으로 매칭해 `nlu: matched <cmd>` 를 로그한다. 봇 송신(B5) 전 단계.

## 범위

-   **포함**: `nlu.py` — `RULES` 리스트 + `match(transcript) -> str | None`. 정규화(소문자·구두점 제거·공백 압축) 후 부분일치 스캔. production 동사(`produce`/`make`/`build`/`train`) **그리고** `scv` 가 모두 있어야 `produce_scv` 발화. first-match-wins. `_on_utterance` 가 STT 뒤에 NLU 를 돌려 `nlu: matched produce_scv` 또는 `nlu: no rule matched: "<transcript>"` 로그.
-   **불포함 (다음 단계)**: 워커→asyncio 브리지로 봇 송신(B5, `server.submit()`). B4 는 매칭 결과를 로그만 한다 — 봇에 아무것도 안 보낸다.
-   **유지**: B1 의 stdin→봇 펌프, B2 의 PTT 캡처, B3 의 STT 전사는 그대로 동시 동작.

근거 ADR: [ADR-018](../../decisions.md#adr-018) (`(키워드, 명령)` 규칙 리스트, 동사 + 명사 부분일치, 정규화, first-match-wins, 무매칭 → 무명령).

## B4 통과 조건

1.  `mise run voice` 기동 후 `,` 토글로 "produce an scv" 발화 → `stt: "..."` 뒤에 `nlu: matched produce_scv`.
2.  `build/make/train + scv` 변형도 매칭. filler("an", "please")는 부분일치라 견딘다.
3.  "S.C.V." 같은 점 표기는 정규화 후 "scv" 포함으로 매칭.
4.  동사 또는 scv 없는 잡음(예: "the scframework") → `nlu: no rule matched: "..."`, 봇에 안 보냄.
5.  빈/무음 캡처는 B3 그대로 `stt: (empty)` 에서 조기 종료 — NLU 안 돌림.

## 설계 결정

### 별도 모듈 `nlu.py`

NLU 는 STT·캡처·서버와 책임이 다르다 → `capture.py`/`stt.py`/`server.py` 처럼 떼어 둔다. 순수 함수 + 모듈 상수(`RULES`)라 클래스 불필요 — 상태가 없다.

### 규칙 구조 — `(동사 집합, 명사 집합, 명령)`

ADR-018 그대로. 동사 집합 AND 명사 집합이 모두 transcript 에 부분일치하면 발화. MVP-B 는 1개 규칙:

```python
RULES = [
    (["produce", "make", "build", "train"], ["scv"], "produce_scv"),
]
```

각 집합은 "하나라도 있으면(any)" 충족, 집합 간은 AND. 명령 1개라 first-match-wins 는 무의미하나 두 번째 명령 전에 우선순위 동작을 정의해 둔다.

### 정규화 후 부분일치

소문자화 → 구두점 제거(`.`/`,` 등) → 공백 압축. 정규화된 문자열에 키워드가 부분문자열로 있는지 스캔. 부분일치라 filler 단어를 견딘다(정확 일치 대신 키워드 NLU 를 쓰는 이유, ADR-018 Rationale). 단어 경계 없이 부분문자열 검사 — "scv" 가 "ascv" 류에도 맞을 수 있으나 명령 어휘가 극소라 허용.

### `_on_utterance` 배선 — STT 뒤 NLU

B3 의 콜백에서 전사 텍스트가 나오면 `nlu.match()` 를 호출한다. 빈 전사는 B3 가 이미 `stt: (empty)` 로 조기 종료하므로 NLU 는 비지 않은 텍스트만 본다. 매칭 → `nlu: matched <cmd>`, 무매칭 → `nlu: no rule matched: "..."`. B5 에서 매칭 결과를 `server.submit(<cmd>)` 으로 잇는다 — 같은 자리.
