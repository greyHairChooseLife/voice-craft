"""voice-craft 음성 서비스 진입점.

B1: asyncio TCP 서버(:5000)만 띄우고, 봇 연결을 검증하기 위해 **stdin** 으로
JSON 라인을 받아 봇에 전달한다 (`nc` 대체의 수동 입력판). 음성 경로(PTT·STT·
NLU)는 B2~B5 에서 stdin 자리를 워커 스레드로 교체한다 (ADR-015).

    mise run voice
    # 봇 connect 로그 확인 후, 한 줄 입력:
    {"cmd":"produce_scv"}
"""
from __future__ import annotations

import asyncio
import sys

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


async def _main() -> None:
    server = CommandServer()
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
