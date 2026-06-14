from __future__ import annotations

import asyncio
import json

import numpy as np

from modules import nlu
from modules.capture import CaptureWorker, SAMPLE_RATE
from modules.server import VoiceServer
from modules.stt import Transcriber


def _make_on_utterance(stt: Transcriber, server: VoiceServer):
    def _on_utterance(buf: np.ndarray) -> None:
        if len(buf) < SAMPLE_RATE * 0.1:  # <0.1s — 무음/오발에 모델 안 돌린다
            print("stt: (empty)", flush=True)
            return
        text = stt.transcribe(buf)
        if not text:
            print("stt: (empty)", flush=True)
            return
        print(f'stt: "{text}"', flush=True)
        cmd = nlu.match(text)
        if not cmd:
            print(f'nlu: no rule matched: "{text}"', flush=True)
            return
        print(f"nlu: matched {cmd}", flush=True)
        server.submit(json.dumps({"cmd": cmd}))

    return _on_utterance


async def _main(stt: Transcriber) -> None:
    server = VoiceServer()
    capture = CaptureWorker(_make_on_utterance(stt, server))
    capture.start()
    await server.start_infinitely()


def main() -> None:
    stt = Transcriber()  # at first, load model
    try:
        # create coroutine -> start event-loop -> convert conroutine to task -> execute task asynchronously
        asyncio.run(_main(stt))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
