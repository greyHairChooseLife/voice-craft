"""voice-craft 음성 서비스 진입점.

asyncio TCP 서버(:5000) + PTT 마이크 캡처(`,` 토글)를 함께 띄운다.

- B1: 봇 연결 검증용 **stdin** → 봇 펌프 (`nc` 대체 수동 입력판).
- B2: PTT 캡처 워커 — `,` 토글로 녹음 → numpy 버퍼(ADR-016).
- B3: 캡처 버퍼를 faster-whisper 로 전사 → `stt: "..."` 로그(ADR-017).
  전사 텍스트는 B4 에서 NLU 로, B5 에서 봇 송신으로 이어진다(ADR-015).

stdin 펌프는 음성 경로가 완전 결선되는 B5 까지 PTT 와 동시 실행으로 둔다.

    mise run voice
    # 봇 connect 로그 확인 후, 한 줄 입력하거나 `,` 눌러 말한다:
    {"cmd":"produce_scv"}
"""
from __future__ import annotations

import asyncio
import sys

import numpy as np

from .capture import CaptureWorker, SAMPLE_RATE
from .server import CommandServer
from .stt import Transcriber


async def _pump_stdin(server: CommandServer) -> None:
    """stdin 라인을 읽어 봇에 전달 (B1 수동 검증용).

    `run_in_executor` 로 블로킹 readline 을 워커에 넘겨 asyncio 루프를 막지
    않는다. EOF(Ctrl-D / 파이프 종료)면 조용히 멈춘다 — 서버는 계속 돈다.
    """
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:  # EOF
            return
        line = line.strip()
        if line:
            server.send(line)


def _make_on_utterance(stt: Transcriber):
    """B3: 캡처 버퍼를 whisper 로 전사해 `stt: "..."` 로그 — 봇엔 아직 안 보낸다.

    빈 버퍼(바로 정지)는 전사를 건너뛰고 `stt: (empty)`. 워커 스레드(pynput
    콜백)에서 호출되므로 전사가 asyncio 루프를 막지 않는다(ADR-015). B4 에서
    전사 텍스트가 NLU 로, B5 에서 `server.submit()` 으로 이어진다.
    """

    def _on_utterance(buf: np.ndarray) -> None:
        if len(buf) < SAMPLE_RATE * 0.1:  # <0.1s — 무음/오발에 모델 안 돌린다
            print("stt: (empty)", flush=True)
            return
        text = stt.transcribe(buf)
        if text:
            print(f'stt: "{text}"', flush=True)
        else:
            print("stt: (empty)", flush=True)

    return _on_utterance


async def _main(stt: Transcriber) -> None:
    server = CommandServer()
    capture = CaptureWorker(_make_on_utterance(stt))
    capture.start()  # pynput 리스너 스레드 등록 (논블로킹, ADR-015)
    async with asyncio.TaskGroup() as tg:
        tg.create_task(server.serve_forever())
        tg.create_task(_pump_stdin(server))


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
