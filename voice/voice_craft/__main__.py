"""voice-craft 음성 서비스 진입점.

asyncio TCP 서버(:5000) + PTT 마이크 캡처(F12)를 함께 띄운다.

- B1: 봇 연결 검증용 **stdin** → 봇 펌프 (`nc` 대체 수동 입력판).
- B2: PTT 캡처 워커 — F12 누른 동안 녹음 → numpy 버퍼 길이만 로그(ADR-016).
  버퍼는 B3 에서 whisper 전사로, B5 에서 봇 송신으로 이어진다(ADR-015).

stdin 펌프는 음성 경로가 완전 결선되는 B5 까지 PTT 와 동시 실행으로 둔다.

    mise run voice
    # 봇 connect 로그 확인 후, 한 줄 입력하거나 F12 눌러 말한다:
    {"cmd":"produce_scv"}
"""
from __future__ import annotations

import asyncio
import sys

import numpy as np

from .capture import CaptureWorker
from .server import CommandServer


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


def _on_utterance(buf: np.ndarray) -> None:
    """B2: 캡처된 버퍼는 길이만 로그(capture 가 이미 출력) — 봇에 안 보낸다.

    B3 에서 이 콜백이 whisper 전사로, B5 에서 NLU + `server.submit()` 으로
    교체된다. B2 는 캡처가 동작하는지만 검증한다.
    """
    del buf  # B2 미사용


async def _main() -> None:
    server = CommandServer()
    capture = CaptureWorker(_on_utterance)
    capture.start()  # pynput 리스너 스레드 등록 (논블로킹, ADR-015)
    async with asyncio.TaskGroup() as tg:
        tg.create_task(server.serve_forever())
        tg.create_task(_pump_stdin(server))


def main() -> None:
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
