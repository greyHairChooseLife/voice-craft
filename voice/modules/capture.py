"""PTT 마이크 캡처 — `,` 토글 핫키 + sounddevice 녹음 (ADR-016).

`,` 를 한 번 누르면 녹음 시작, 다시 누르면 정지(토글 PTT). `pynput` 전역
핫키가 StarCraft(Wine 창)에 포커스가 있어도 동작하고, `sounddevice`
InputStream 이 콜백으로 주는 청크를 모아 mono 16 kHz `float32` numpy 배열로
연결한다. 디스크·WAV 없음 — 버퍼를 바로 콜백에 넘긴다.

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
PTT_KEY = keyboard.KeyCode.from_char(",")  # 토글 키 (ADR-016)


class CaptureWorker:
    """`,` 토글로 마이크 녹음을 시작/정지해 numpy 버퍼를 콜백(on_utterance)으로 넘긴다.

    `on_utterance(buf)` 는 정지(2번째 누름)마다 1회 호출된다 — `buf` 는 1차원
    mono `float32` 배열(@16 kHz). 빈 캡처(바로 정지)도 길이 0 배열로 호출한다.

    Attributes:
        _on_utterance: 녹음 정지 시 호출할 콜백
        _stream: 녹음 중일 때만 존재, 정지 후 None
        _chunks: 오디오 스레드가 쌓임. _stop 에서만 읽고, 다시 사용시 초기화함. lock-free: 2개
        쓰레드가 쓰기/읽기 위해 접근하지만, 겹치는 구간이 없으니 안전
        _is_recording: 현재 녹음 중 여부
        _is_key_pressed: 키 리피트 가드 — 물리적 누름 1회만 토글
    """

    def __init__(self, on_utterance: Callable[[np.ndarray], None]) -> None:
        self._on_utterance = on_utterance
        self._stream: sd.InputStream | None = None
        self._chunks: list[np.ndarray] = []
        self._is_recording = False
        self._is_key_pressed = False

    def start(self) -> None:
        """핫키 리스너 등록. 논블로킹 — 리스너는 자체 스레드에서 돈다."""
        listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release  # pyright: ignore[reportArgumentType]
        )
        listener.start()
        print("ptt: ready (, to start/stop)", flush=True)

    def _on_press(self, key: keyboard.Key) -> None:
        if key != PTT_KEY or self._is_key_pressed:
            return
        self._is_key_pressed = True
        if self._is_recording:
            self._stop()
        else:
            self._start()

    def _on_release(self, key: keyboard.Key) -> None:
        if key == PTT_KEY:
            self._is_key_pressed = False  # 다음 물리적 누름을 허용

    def _start(self) -> None:
        self._is_recording = True
        self._chunks = [] # 초기화
        self._stream = sd.InputStream(
            channels=1, # mono, one-mic/user
            dtype="float32",
            # blocksize=0 by default so it fits OS asks
            samplerate=SAMPLE_RATE,
            callback=self._on_audio, # execute every blocksize/samplerate, adjustmetn between quality and speed
        )
        self._stream.start()
        print("ptt: recording...", flush=True)

    def _stop(self) -> None:
        self._is_recording = False
        assert self._stream is not None
        self._stream.stop()
        self._stream.close()
        self._stream = None

        if self._chunks:
            buf = np.concatenate(self._chunks).reshape(-1)  # pure audio sample array
        else:
            buf = np.empty(0, dtype="float32")
        self._chunks = []

        secs = len(buf) / SAMPLE_RATE
        if len(buf):
            print(f"ptt: captured {secs:.1f}s", flush=True)
        else:
            print("ptt: captured 0.0s (empty)", flush=True)
        self._on_utterance(buf)

    def _on_audio(self, indata: np.ndarray, _frames: int, _time, status) -> None:
        if status:
            print(f"ptt: audio status {status}", flush=True)
        self._chunks.append(indata.copy())
