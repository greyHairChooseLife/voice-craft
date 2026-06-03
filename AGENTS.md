# 프로젝트 개요

스타크래프트: 브루드워를 **음성 명령만으로** 플레이할 수 있게 하는 도구.

-   사용자가 마이크에 명령을 말하면, 도구가 이를 게임 입력으로 변환해 BW에 전달.
-   본체는 음성 명령 모드(Voice-Only Command). 마우스/키보드 조작 없이 음성으로만 운영.


## MPV

-   구현: 단일 명령 "마린 생산" → 사전 배치된 배럭에서 마린 1기 생산.
-   테스트 맵: 배럭 1개 + 미네랄 1000+ + 서플라이 여유 (ScmDraft 2로 제작).
-   작업 순서:
    1. C++ BWAPI 봇 먼저. `nc localhost <port>`로 JSON 수동 주입해 검증.
    2. Python 음성 서비스 나중.


## 아키텍처

두 개 프로세스 + IPC 구조.

```
[키 누름]
  ↓
[mic 녹음]
  ↓
[faster-whisper STT]
  ↓
[키워드 딕셔너리 NLU]
  ↓
[JSON 한 줄] → TCP localhost → [C++ BWAPI 봇]
                                   ↓
                               [BWAPI: barracks.train(Marine)]
                                   ↓
                               [게임 화면에 마린 등장]
```

### 게임 측

-   **BW 1.16.1 + Classic BWAPI**.
-   **C++ BWAPI 봇**: 명령 받아 BWAPI 호출만 하는 얇은 레이어.

### 음성 측 (Python)

-   **트리거**: 푸시-투-토크.
-   **STT**: faster-whisper (로컬).
-   **NLU**: 키워드 딕셔너리 + 부분일치 스캔.

### IPC

-   TCP localhost
-   JSON lines. 예: `{"cmd": "produce_marine"}`.
-   Python = 서버 (여러 매치 동안 유지), C++ 봇 = 클라이언트 (매치 시작 시 연결).
