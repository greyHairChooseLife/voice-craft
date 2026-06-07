"""voice-craft 음성 서비스 진입점 — 전체 음성 경로 결선 (B5, MVP-B 완료).

asyncio TCP 서버(:5000) + PTT 마이크 캡처(`,` 토글)를 한 프로세스에서 띄워
음성만으로 봇에 명령을 보낸다(ADR-015):

    PTT 캡처(B2) → STT 전사(B3) → NLU 매칭(B4) → 봇 송신(B5)

- B2: PTT 캡처 워커 — `,` 토글로 녹음 → numpy 버퍼(ADR-016).
- B3: 캡처 버퍼를 faster-whisper 로 전사 → `stt: "..."` 로그(ADR-017).
- B4: 전사를 키워드 NLU 로 매칭 → `nlu: matched <cmd>` 로그(ADR-018).
- B5: 매칭된 명령을 와이어 JSON 으로 감싸 `server.submit()` 으로 봇에 송신.

전사·NLU·송신은 모두 워커 스레드(pynput 콜백)에서 돌고, `server.submit()` 이
`call_soon_threadsafe` 로 asyncio 루프에 브리지한다(ADR-015) — 녹음·전사 중에도
:5000 서버가 멈추지 않는다. stdin 수동 입력은 B5 에서 은퇴했다(음성 전용).

    mise run voice
    # 봇 connect 로그 확인 후, `,` 눌러 시작 → 말하고 → `,` 눌러 정지.
"""
from __future__ import annotations

import asyncio
import json

import numpy as np

from . import nlu
from .capture import CaptureWorker, SAMPLE_RATE
from .server import CommandServer
from .stt import Transcriber


def _make_on_utterance(stt: Transcriber, server: CommandServer):
    """전체 음성 경로 콜백: 캡처 버퍼 → STT → NLU → 봇 송신 (B5, ADR-015).

    빈 버퍼(바로 정지)는 전사를 건너뛰고 `stt: (empty)`. 전사가 NLU 규칙에
    매칭되면 명령을 와이어 JSON(`{"cmd": ...}`, MVP-A 포맷)으로 감싸
    `server.submit()` 으로 봇에 보낸다 — 무매칭이면 아무것도 안 보낸다(잡음
    차단, ADR-018). 워커 스레드(pynput 콜백)에서 호출되므로 전사·송신이
    asyncio 루프를 막지 않는다(`submit` 이 루프 스레드로 브리지, ADR-015).
    """

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
    server = CommandServer()
    capture = CaptureWorker(_make_on_utterance(stt, server))
    capture.start()  # pynput 리스너 스레드 등록 (논블로킹, ADR-015)
    await server.serve_forever()


def main() -> None:
    # whisper 모델은 asyncio 루프 시작 전에 1회 로드한다(콜드 스타트 없음,
    # ADR-017). 로드는 블로킹이지만 이후 전사는 워커 콜백 스레드에서만 돈다.
    stt = Transcriber()
    try:
        asyncio.run(_main(stt))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
