"""PTT 마이크 캡처 — F12 전역 핫키 + sounddevice 녹음 (ADR-016).

F12 를 누른 동안만 녹음한다(누른 동안 녹음 PTT). `pynput` 전역 핫키가
StarCraft(Wine 창)에 포커스가 있어도 동작하고, `sounddevice` InputStream 이
콜백으로 주는 청크를 모아 mono 16 kHz `float32` numpy 배열로 연결한다.
디스크·WAV 없음 — 버퍼를 바로 콜백에 넘긴다(B3 에서 whisper 전사로 교체).

워커 측 단(ADR-015): pynput 리스너 스레드 + sounddevice 오디오 스레드. asyncio
루프와 분리돼 녹음·전사 중에도 :5000 서버가 멈추지 않는다.

X11 세션 필요 — Wayland 은 보안 모델상 전역 핫키가 막힌다(ADR-016, 범위 밖).
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import sounddevice as sd
from pynput import keyboard

SAMPLE_RATE = 16_000  # whisper 입력 (ADR-016)
PTT_KEY = keyboard.Key.f12  # BW 미사용 키 — 게임 동작과 충돌 없음 (ADR-016)


class CaptureWorker:
    """F12 누른 동안 마이크를 녹음해 numpy 버퍼를 콜백으로 넘긴다.

    `on_utterance(buf)` 는 F12-up 마다 1회 호출된다 — `buf` 는 1차원 mono
    `float32` 배열(@16 kHz). 빈 캡처(즉시 떼기)도 길이 0 배열로 호출한다.
    """

    def __init__(self, on_utterance: Callable[[np.ndarray], None]) -> None:
        self._on_utterance = on_utterance
        self._stream: sd.InputStream | None = None
        # 오디오 스레드가 append, PTT 스레드가 정지 후 읽는다. 콜백은 append 만
        # 하므로 락 없이도 안전(정지 시 콜백이 더는 안 불린다).
        self._chunks: list[np.ndarray] = []
        self._recording = False

    def start(self) -> None:
        """핫키 리스너 등록. 논블로킹 — 리스너는 자체 스레드에서 돈다."""
        listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        listener.start()
        print("ptt: ready (F12 to talk)", flush=True)

    def _on_press(self, key: keyboard.Key) -> None:
        # 키 리피트 가드: F12 를 누르고 있으면 on_press 가 반복된다 — 첫 down 만.
        if key is not PTT_KEY or self._recording:
            return
        self._recording = True
        self._chunks = []
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=self._on_audio,
        )
        self._stream.start()
        print("ptt: recording...", flush=True)

    def _on_release(self, key: keyboard.Key) -> None:
        if key is not PTT_KEY or not self._recording:
            return
        self._recording = False
        assert self._stream is not None
        self._stream.stop()
        self._stream.close()
        self._stream = None

        if self._chunks:
            buf = np.concatenate(self._chunks).reshape(-1)
        else:
            buf = np.empty(0, dtype="float32")
        self._chunks = []

        secs = len(buf) / SAMPLE_RATE
        if len(buf):
            print(f"ptt: captured {secs:.1f}s", flush=True)
        else:
            print("ptt: captured 0.0s (empty)", flush=True)
        self._on_utterance(buf)

    def _on_audio(self, indata: np.ndarray, frames: int, time, status) -> None:
        # 오디오 스레드. 청크 복사본만 쌓는다(indata 는 재사용 버퍼).
        if status:
            print(f"ptt: audio status {status}", flush=True)
        self._chunks.append(indata.copy())
