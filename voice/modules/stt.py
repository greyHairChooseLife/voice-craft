"""
STT — faster-whisper `base.en` 로컬 전사 (ADR-017).

capture 워커가 만든 mono 16 kHz `float32` numpy 버퍼를 전사해 소문자 영어 문자열을
돌려준다.

`WhisperModel` 은 시작 시 1회 로드, 콜드 스타트 없음(ADR-015)

`transcribe()` 의 무거운 추론은 CTranslate2 네이티브 코드라 GIL 을 풀어 :5000
서버의 응답성을 해치지 않는다(ADR-015 근거).

`base.en` 모델은 첫 로드 시 Hugging Face 캐시에 자동 다운로드된다(~140MB).
"""

from __future__ import annotations

import numpy as np
from faster_whisper import WhisperModel

MODEL = "base.en"      # 영어 전용 — 명령 어휘가 작아 정확도/지연 스위트 스폿 (ADR-017)
DEVICE = "cpu"
COMPUTE_TYPE = "int8"  # 양자화
INITIAL_PROMPT = "Commands: produce, make, build, train an SCV."


class Transcriber:
    def __init__(self) -> None:
        self._model = WhisperModel(MODEL, DEVICE, compute_type=COMPUTE_TYPE)  # default: ~/.cache/huggingface/hub
        print(f"stt: model loaded ({MODEL}, {DEVICE}, {COMPUTE_TYPE})", flush=True)

    def transcribe(self, buf: np.ndarray) -> str:
        """버퍼를 전사해 소문자 텍스트를 돌려준다. 빈/무음이면 빈 문자열.

        `language="en"` 으로 언어 감지를 생략한다(ADR-017). segments 는 lazy
        제너레이터라 join 시점에 추론이 돈다 — 명령 클립은 짧아 세그먼트 1~2개.
        """
        segments, _ = self._model.transcribe(
            buf,
            language="en",
            initial_prompt=INITIAL_PROMPT,
        )
        text = " ".join(seg.text for seg in segments).strip()
        return text.lower()
