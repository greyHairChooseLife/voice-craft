"""STT — faster-whisper `base.en` 로컬 전사 (ADR-017).

캡처 워커가 만든 mono 16 kHz `float32` numpy 버퍼를 전사해 소문자 영어 문자열을
돌려준다. `WhisperModel` 은 워커 스레드에 상주하며(시작 시 1회 로드, 콜드 스타트
없음, ADR-015) `transcribe()` 의 무거운 추론은 CTranslate2 네이티브 코드라 GIL 을
풀어 :5000 서버의 응답성을 해치지 않는다(ADR-015 근거).

`base.en` 모델은 첫 로드 시 Hugging Face 캐시에 자동 다운로드된다(~140MB).
"""
from __future__ import annotations

import numpy as np
from faster_whisper import WhisperModel

MODEL = "base.en"  # 영어 전용 — 명령 어휘가 작아 정확도/지연 스위트 스폿 (ADR-017)
# SCV 로 편향하는 짧은 디코드 힌트 — 명령 어휘가 극소라 인식을 거든다 (ADR-017).
INITIAL_PROMPT = "Commands: produce, make, build, train an SCV."


class Transcriber:
    """`base.en` CPU int8 모델을 보유하고 numpy 버퍼를 전사한다 (ADR-017).

    워커 스레드에서 생성·호출한다 — 모델 로드는 블로킹이므로 asyncio 루프 밖에서
    한다. `transcribe()` 도 워커 스레드에서만 호출된다.
    """

    def __init__(self) -> None:
        # device=cpu, compute_type=int8 — GPU 없음, int8 양자화로 CPU 지연 최소화.
        self._model = WhisperModel(MODEL, device="cpu", compute_type="int8")
        print(f"stt: model loaded ({MODEL}, cpu int8)", flush=True)

    def transcribe(self, buf: np.ndarray) -> str:
        """버퍼를 전사해 소문자 텍스트를 돌려준다. 빈/무음이면 빈 문자열.

        `language="en"` 으로 언어 감지를 생략한다(ADR-017). segments 는 lazy
        제너레이터라 join 시점에 추론이 돈다 — 명령 클립은 짧아 세그먼트 1~2개.
        """
        segments, _info = self._model.transcribe(
            buf,
            language="en",
            initial_prompt=INITIAL_PROMPT,
        )
        text = " ".join(seg.text for seg in segments).strip()
        return text.lower()
