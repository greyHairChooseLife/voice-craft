# B3 — STT (faster-whisper `base.en` 으로 캡처 버퍼 전사)

worktree `feat_STT-with-fast-whisper`. B2(PTT 캡처 → numpy 버퍼)에 이어, 캡처 버퍼를 faster-whisper 로 전사해 `stt: "..."` 를 로그한다. NLU(B4)·봇 송신(B5) 전 단계.

## 범위

-   **포함**: `Transcriber` (faster-whisper `base.en`, `device="cpu"`, `compute_type="int8"`, `language="en"`). 시작 시 1회 로드. `_on_utterance` 가 캡처 버퍼를 전사해 `stt: "<전사>"` 로그. 빈/무음 캡처는 모델을 안 돌리고 `stt: (empty)`.
-   **불포함 (다음 단계)**: 키워드 NLU(B4), 워커→asyncio 브리지로 명령 송신(B5). B3 은 전사 텍스트를 로그만 한다 — 봇에 아무것도 안 보낸다.
-   **유지**: B1 의 stdin→봇 펌프, B2 의 PTT 캡처는 그대로 동시 동작.

근거 ADR: [ADR-017](../../decisions.md#adr-017) (faster-whisper `base.en`, CPU int8, `language="en"`, 시작 시 1회 로드), [ADR-015](../../decisions.md#adr-015) (전사는 워커 스레드, CTranslate2 가 GIL 을 풀어 :5000 응답성 유지).

## B3 통과 조건

1.  `mise run voice` → `stt: model loaded (base.en, cpu int8)` + 서버 listen + `ptt: ready`.
2.  `,` 토글로 발화 캡처 → `stt: "<전사>"` 로그(발화에 대응).
3.  빈 캡처(바로 정지)는 모델을 안 돌리고 `stt: (empty)`.
4.  전사 중에도 :5000 서버는 listen(봇 connect 가능) — GIL 분리 확인.
5.  모델은 시작 시 1회만 로드(매 발화마다 재로드 없음).

마이크는 시스템 기본 입력 장치. `base.en` 모델은 첫 실행 시 자동 다운로드·캐시(~140MB).

## 설계 결정

### 별도 모듈 `stt.py`

전사(모델 로드 + `transcribe`)는 캡처·서버와 책임이 다르고 B4 에서 NLU 가 붙을 자리다 → `capture.py`/`server.py` 처럼 떼어 둔다. `Transcriber` 클래스가 `WhisperModel` 수명을 소유.

### 모델 로드 위치 — asyncio 루프 시작 전 1회

`Transcriber()` 를 `main()` 에서 `asyncio.run()` **전에** 구성한다. 로드는 블로킹이지만 1회뿐이라 루프 시작 전에 끝낸다(콜드 스타트 없음, ADR-017). 이후 `transcribe()` 는 pynput 콜백(워커 스레드)에서만 호출돼 asyncio 루프를 막지 않는다(ADR-015).

### 전사 호출은 워커 콜백 스레드

`_on_utterance` 는 캡처의 정지 토글(`_stop`)에서 호출되고, 그건 pynput 리스너 스레드다 → 전사가 이미 메인 루프 밖에서 돈다. faster-whisper 의 무거운 추론은 CTranslate2 네이티브라 GIL 을 풀어 :5000 TCP 스레드가 응답성을 유지(ADR-015 근거 실현).

### 빈/무음 캡처 가드

`len(buf) < 16000 * 0.1` (<0.1s) 이면 모델을 건너뛰고 `stt: (empty)`. 바로 정지한 빈 캡처나 오발에 무거운 추론을 안 돌린다. 전사 결과가 빈 문자열이어도 `stt: (empty)`.

### 디코드 힌트

`language="en"` 로 언어 감지 생략(ADR-017). SCV 로 편향하는 짧은 `initial_prompt` 로 극소 명령 어휘 인식을 거든다. 전사 결과는 소문자로 정규화(B4 NLU 가 소문자 영어 입력을 가정, ADR-018).

### 콜백 팩토리 `_make_on_utterance(stt)`

`_on_utterance` 가 모델 핸들을 클로저로 잡도록 팩토리로 감싼다 — 전역 상태 없이 `Transcriber` 를 콜백에 주입. B4 에서 같은 자리에 NLU 를, B5 에서 `server.submit()` 을 더한다.

## 모델 크기 트레이드오프 (운영자 노트)

faster-whisper 패키지 + CTranslate2 런타임은 설치가 크다(휠 + 의존성 ~수백 MB). `base.en` 모델 자체는 ~140MB(첫 실행 다운로드, HF 캐시 재사용). CPU 지연이 불만이면 `tiny.en`(~75MB), 정확도가 불만이면 `small.en`(~460MB) 로 `stt.py` `MODEL` 한 줄 조정(ADR-017 Consequences).
