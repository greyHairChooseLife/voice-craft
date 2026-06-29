// 봇 비차단 TCP 클라이언트 — A4 (ADR-004, ADR-005).
// 명령 서버(127.0.0.1:5000)에 붙어 매 프레임 polling, 라인 단위 echo.
// JSON 파싱·디스패치는 다음 단계에서 on_line 콜백 자리에 들어간다.
#pragma once

#include <cstdint>
#include <functional>
#include <string>

#include <winsock2.h>

class VoiceClient
{
      public:
        VoiceClient (std::string host, uint16_t port);
        ~VoiceClient ();

        VoiceClient (const VoiceClient &) = delete;
        VoiceClient &operator= (const VoiceClient &) = delete;

        using Linehandler = std::function<void (const std::string &)>;

        // 매 프레임 호출. 비차단. 완성된 각 라인마다 on_line(line) 호출.
        void poll (const Linehandler &on_line);

      private:
        enum class State
        {
                Disconnected,
                Connecting,
                Connected
        };

        void start_connect ();
        void check_connect ();
        void recv_lines (const Linehandler &on_line);
        void drop (); // 소켓 닫고 Disconnected 로

        std::string host_;
        uint16_t port_;
        SOCKET sock_ = INVALID_SOCKET;
        State state_ = State::Disconnected;
        std::string buffer_; // 영구 라인 버퍼 (프레임 간 누적)
        bool wsa_ready_ = false;
};
