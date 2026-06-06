# B2 — PTT 캡처 (`,` 토글 전역 핫키 + 마이크 녹음 → numpy 버퍼) — 완료

worktree `feat_capture-keyboard-input`. B1(asyncio TCP 서버, stdin→봇)에 이어, 음성 경로의 첫 입력단을 만든다 — `,` 토글로 마이크를 녹음해 mono 16 kHz `float32` numpy 버퍼로 만든다. STT(B3)·NLU(B4) 전 단계.

## 범위

-   **포함**: PTT 캡처 워커. `pynput` 전역 핫키(`,`)의 `on_press` 가 녹음을 토글(시작/정지)하고 `on_release` 가 키 리피트 가드를 푼다. 정지 시 콜백 청크를 모아 mono 16 kHz `float32` numpy 배열로 연결, 캡처 길이를 로그. 워커 스레드에서 실행(ADR-015).
-   **불포함 (다음 단계)**: faster-whisper STT(B3), 키워드 NLU(B4), 워커→asyncio 브리지로 명령 송신(B5). B2 는 버퍼를 만들고 길이만 로그한다 — 봇에 아무것도 안 보낸다.
-   **유지**: B1 의 stdin→봇 펌프는 그대로 둔다(PTT 워커와 동시 실행). 음성 경로가 완전 결선되는 B5 에서 stdin 제거 재검토.

근거 ADR: [ADR-016](../../decisions.md#adr-016) (PTT=`,` 토글, X11 전역 핫키, mono 16 kHz float32 numpy), [ADR-015](../../decisions.md#adr-015) (음성 입력은 워커 스레드).

## B2 통과 조건

1.  `mise run voice` → 서버 listen + `ptt: ready (, to start/stop)` 로그.
2.  `,` 누름 → `ptt: recording...`, sounddevice 스트림 시작.
3.  다시 `,` → 스트림 정지, `ptt: captured <N>s` (실제 발화 길이에 비례).
4.  반복: 또 `,` 토글하면 또 캡처. 버퍼는 매 캡처마다 초기화.
5.  녹음 중에도 :5000 서버는 계속 listen(워커 스레드 분리 확인) — 봇 connect 가능.

X11 세션 필요(전역 핫키 — Wayland 미지원, ADR-016). 마이크는 시스템 기본 입력 장치.

## 설계 결정

### 별도 모듈 `capture.py`

PTT 캡처(키 리스너 + 마이크 스트림 + 버퍼 누적)는 서버와 책임이 다르고 B3 에서 STT 콜백이 붙을 자리다 → 떼어 둔다. `CaptureWorker` 클래스가 pynput 리스너와 sounddevice 스트림 수명을 소유.

### 토글 PTT (누른 동안 녹음에서 변경)

원안(ADR-016)은 누른 동안 녹음이었으나 긴 발화에서 키를 계속 누르고 있어야 해 UX가 불편했다 → `,` 한 번에 시작, 다시 `,` 에 정지하는 토글로 바꿨다(ADR-016 Revised). `,` 는 인쇄 가능한 키라 BW 단축키·텍스트 입력과 겹칠 수 있다 — 실제 게임에서 충돌 확인(운영자 검증).

### 콜백으로 버퍼 전달 (B3 대비)

정지 시 완성된 numpy 버퍼를 콜백(`on_utterance: Callable[[np.ndarray], None]`)으로 넘긴다. B2 콜백은 길이만 로그. B3 에서 이 콜백이 whisper 전사로 교체된다 — `__main__` 배선은 그대로.

### sounddevice InputStream, 콜백 청크 누적

-   `sd.InputStream(samplerate=16000, channels=1, dtype="float32", callback=...)`.
-   콜백은 오디오 스레드에서 호출됨 — 청크(`indata.copy()`)를 리스트에 append 만 한다(락 최소화).
-   정지 토글에서 스트림 정지 후 `np.concatenate` 로 1차원 배열 생성, 리스트 비움.
-   시작 토글에서 스트림 시작.

### pynput 키 리피트 가드

`,` 를 누르고 있으면 `on_press` 가 반복 발화돼 토글이 빠르게 뒤집힌다 → `_key_down` 플래그로 한 물리적 누름당 한 번만 토글하고, `on_release` 가 플래그를 풀어 다음 누름을 허용한다.

### 길이 로그 단위

`captured <samples>/16000` 초, 소수 1자리. 빈 캡처(바로 정지)는 `ptt: captured 0.0s (empty)` — B3 에서 STT 조기 종료로 이어질 자리.
