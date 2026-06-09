"""asyncio TCP 명령 서버 (:5000) — `nc` 대체 (ADR-019).

봇은 클라이언트로 매치마다 새로 연결한다 (ADR-004). 서버는 매치 전체를
가로질러 살아남으며 봇 1개 연결만 보유한다:

    accept    → writer 저장
    disconnect→ writer 클리어
    reconnect → writer 교체 (두 번째 봇이 붙으면 옛 연결을 닫음 — 단일 봇 불변식)

명령 송신은 JSON 라인 1개 + `\n` (MVP-A 와이어 포맷). 봇 미연결 중 생성된
명령은 드롭 + 로그 — 미래 연결을 위해 큐잉하지 않는다 (ADR-019).
"""
from __future__ import annotations

import asyncio

HOST = "127.0.0.1"
PORT = 5000


class CommandServer:
    """봇 1개 연결을 보유하는 asyncio TCP 서버 (단일 봇 불변식, ADR-019)."""

    def __init__(self, host: str = HOST, port: int = PORT) -> None:
        self._host = host
        self._port = port
        self._loop: asyncio.AbstractEventLoop | None = None
        # 현재 봇 연결. 매치 사이 None (미연결) 일 수 있다.
        self._writer: asyncio.StreamWriter | None = None
        self._peer: str = ""

    async def serve_forever(self) -> None:
        """서버를 띄우고 영구 listen. 매 매치 봇 연결을 가로질러 살아남는다."""
        self._loop = asyncio.get_running_loop()
        server = await asyncio.start_server(self._on_bot, self._host, self._port)
        print(f"tcp: listening on {self._host}:{self._port}", flush=True)
        async with server:
            await server.serve_forever()

    async def _on_bot(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """봇 연결 핸들러. accept → 보유, EOF → 클리어 (ADR-019 생애주기)."""
        peer = _peername(writer)

        # 단일 봇 불변식: 이미 봇이 있으면 옛 연결을 닫고 교체한다.
        if self._writer is not None:
            print(f"tcp: replacing bot {self._peer} with {peer}", flush=True)
            self._close_writer(self._writer)

        self._writer = writer
        self._peer = peer
        print(f"tcp: bot connected {peer}", flush=True)

        try:
            # 봇은 명령을 받기만 한다 (단방향). 연결 종료(EOF) 감지용으로만 읽는다.
            while True:
                data = await reader.read(1024)
                if not data:
                    break  # 봇이 연결을 닫음 (매치 종료)
        except ConnectionError:
            pass
        finally:
            # 그 사이 다른 봇으로 교체됐다면 현재 writer 를 건드리지 않는다.
            if self._writer is writer:
                self._writer = None
                self._peer = ""
                print(f"tcp: bot disconnected {peer}", flush=True)
            self._close_writer(writer)

    def send(self, command: str) -> None:
        """명령 JSON 라인 1개를 봇에 전송. 봇 미연결이면 드롭 + 로그 (ADR-019).

        asyncio 루프 스레드에서 호출해야 한다. 워커 스레드는 `submit()` 을 쓴다.
        """
        line = command.rstrip("\n")
        if self._writer is None:
            print(f"tcp: no bot connected, dropped: {line}", flush=True)
            return
        try:
            self._writer.write((line + "\n").encode())
        except ConnectionError:
            print(f"tcp: write failed, dropped: {line}", flush=True)
            return
        print(f"tcp: sent {line}", flush=True)

    def submit(self, command: str) -> None:
        """워커 스레드 → 메인 루프 브리지 (ADR-015). 스레드 안전.

        `loop.call_soon_threadsafe` 로 `send()` 를 루프 스레드에 예약한다.
        B5 에서 음성 워커가 이 진입점으로 명령을 넘긴다.
        """
        if self._loop is None:
            print(f"tcp: server not running, dropped: {command}", flush=True)
            return
        self._loop.call_soon_threadsafe(self.send, command)

    @staticmethod
    def _close_writer(writer: asyncio.StreamWriter) -> None:
        try:
            writer.close()
        except Exception:
            pass


def _peername(writer: asyncio.StreamWriter) -> str:
    peer = writer.get_extra_info("peername")
    if peer:
        return f"{peer[0]}:{peer[1]}"
    return "?"
