# Changelog

음성 명령으로 스타크래프트: 브루드워를 플레이하는 도구의 *나간 것* 기록. 최신 마일스톤이 위.

각 항목은 워크트리(브랜치) 단위로, 실제 작업한 내용을 적는다. 장기 계획·취소된 시도는 [docs/roadmap.md](docs/roadmap.md), 결정 이유는 [docs/decisions.md](docs/decisions.md), 구조는 [docs/architecture.md](docs/architecture.md), 완료 플랜은 [docs/plans/done/](docs/plans/done/).


## MVP-B — 음성 경로 (2026-06-08)

전체 음성 경로 PTT → STT → NLU → JSON → 봇. 영어 전용. Python 음성 서비스가 :5000 서버가 되어 `nc`를 은퇴 (ADR-015~019).

-   asyncio TCP 서버 (:5000, 봇 connect/echo, `nc` 대체) — `feat_tcp-part-of-voice-server` (ADR-019)
-   PTT 캡처: `,` 토글 전역 핫키 + 마이크 녹음 → numpy 버퍼 — `feat_capture-keyboard-input` (ADR-016)
-   STT: faster-whisper `base.en` cpu/int8, 버퍼 → 텍스트 — `feat_STT-with-fast-whisper` (ADR-017)
-   키워드 NLU: 동사+scv → `produce_scv` JSON, 무매칭 드롭 — `feat_NLU-by-pattern-matching` (ADR-018)
-   전체 경로 결선: 워커 스레드→asyncio 브리지, 음성만으로 SCV 생산 — `feat_unify-Bot-and-Voice` (ADR-015)


## MVP-A — 봇 + nc (2026-06-06)

C++ 봇 + `nc`로 JSON 수동 주입 → SCV 등장.

-   Wine + BW 1.16.1 실행, injectory로 BWAPI 4.4.0 인젝션 검증 — `chore_wine-and-BW` (ADR-013)
-   MinGW(Docker) + BWAPI Client API 봇 .exe, 게임 채팅에 "hello" 출력 — `chore_bot-boilerplate` (ADR-014)
-   비차단 TCP 클라이언트 + 라인 버퍼, nc 입력이 봇 화면에 에코 — `feat_non-block-tcp-client-reading-receive-buffer`
-   JSON 디스패치 → 스톡 melee CC에서 SCV train — `feat_json-dispatch` (ADR-006/007/008)
