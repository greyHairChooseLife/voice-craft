"""voice-craft 음성 서비스 패키지 (MVP-B).

메인 스레드 = asyncio TCP 서버(:5000, 봇 1개 연결 보유), 워커 스레드 =
PTT·마이크·STT·NLU (ADR-015). B1=TCP 서버, B2=PTT 캡처(F12+마이크).
"""
