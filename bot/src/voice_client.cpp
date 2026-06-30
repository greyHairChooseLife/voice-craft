// VoiceClient 구현 — 비차단 Winsock TCP 클라이언트 (ADR-005).
// 봇은 Wine 의 Windows .exe 라 POSIX 가 아니라 Winsock 을 쓴다 (CMake: ws2_32).
#include "voice_client.h"

#include <iostream>

VoiceClient::VoiceClient (std::string host, uint16_t port) : host_ (std::move (host)), port_ (port)
{
        WSADATA wsa;
        if (WSAStartup (MAKEWORD (2, 2), &wsa) == 0)
        {
                wsa_ready_ = true;
        }
        else
        {
                std::cout << "voice: WSAStartup failed" << std::endl;
        }
}

VoiceClient::~VoiceClient ()
{
        drop ();
        if (wsa_ready_)
                WSACleanup ();
}

void
VoiceClient::poll (const VoiceClient::Linehandler &on_line)
{
        if (!wsa_ready_)
                return;

        switch (state_)
        {
        case State::Disconnected:
                start_connect ();
                break;
        case State::Connecting:
                check_connect ();
                break;
        case State::Connected:
                recv_lines (on_line);
                break;
        }
}

void
VoiceClient::start_connect ()
{
        sock_ = socket (AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (sock_ == INVALID_SOCKET)
                return; // 다음 프레임 재시도

        u_long nonblocking = 1;
        ioctlsocket (sock_, FIONBIO, &nonblocking);

        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_port = htons (port_);
        // inet_pton 은 _WIN32_WINNT>=0x0600 필요 (프로젝트는 0x0501). localhost
        // IPv4 점표기 주소엔 inet_addr 로 충분.
        addr.sin_addr.s_addr = inet_addr (host_.c_str ());

        int rc = connect (sock_, reinterpret_cast<sockaddr *> (&addr), sizeof (addr));
        if (rc == 0)
        {
                // localhost 라 즉시 성공할 수 있음
                state_ = State::Connected;
                std::cout << "voice: connected to " << host_ << ":" << port_ << std::endl;
                return;
        }

        // 비차단 connect 는 보통 WSAEWOULDBLOCK → 진행 중
        if (WSAGetLastError () == WSAEWOULDBLOCK)
        {
                state_ = State::Connecting;
        }
        else
        {
                drop (); // 서버 부재 등 → 다음 프레임 재시도
        }
}

void
VoiceClient::check_connect ()
{
        // connect 완료 여부를 비차단으로 확인: 쓰기 가능 = 성공, except = 실패.
        // 비차단 connect의 readiness는 writable 여부로 확인한다. TCP 연결의 규칙
        fd_set write_set;
        fd_set except_set;
        FD_ZERO (&write_set);
        FD_ZERO (&except_set);
        FD_SET (sock_, &write_set);
        FD_SET (sock_, &except_set);

        timeval zero{}; // 즉시 반환 (블록 안 함)

        // Winsock은 내부적으로 fd_set 자체에서 가장 높은 소켓을 알아내기 때문에 nfds가 필요
        // 없습니다. 따라서 POSIX에서의 sock_ + 1 규칙은 Windows에서는 의미가 없고, 0을 넣어도 정상
        // 동작합니다.
        int rc = select (0, nullptr, &write_set, &except_set, &zero);
        if (rc == 0)
                return; // 아직 진행 중

        if (rc < 0 || FD_ISSET (sock_, &except_set))
        {
                drop (); // connect 실패 → 재시도
                return;
        }

        if (FD_ISSET (sock_, &write_set))
        {
                state_ = State::Connected;
                std::cout << "voice: connected to " << host_ << ":" << port_ << std::endl;
        }
}

void
VoiceClient::recv_lines (const VoiceClient::Linehandler &on_line)
{
        char chunk[1024];
        for (;;)
        {
                int n = recv (sock_, chunk, sizeof (chunk), 0);
                if (n > 0)
                {
                        buffer_.append (chunk, static_cast<size_t> (n));
                        continue; // 더 읽을 게 있으면 계속 (한 프레임에 비울 수
                                  // 있는 만큼)
                }
                if (n == 0)
                {
                        std::cout << "voice: server closed" << std::endl;
                        drop ();
                        return;
                }
                // n < 0
                if (WSAGetLastError () == WSAEWOULDBLOCK)
                        break; // 데이터 없음 — 정상, 비차단 반환점

                std::cout << "voice: recv error" << std::endl;
                drop ();
                return;
        }

        // 영구 버퍼에서 완성된 라인(\n)만 잘라 콜백. 부분 라인은 남겨 둔다.
        size_t nl;
        while ((nl = buffer_.find ('\n')) != std::string::npos)
        {
                std::string line = buffer_.substr (0, nl);
                buffer_.erase (0, nl + 1);
                if (!line.empty () && line.back () == '\r') // CRLF 보정
                        line.pop_back ();
                on_line (line);
        }
}

void
VoiceClient::drop ()
{
        if (sock_ != INVALID_SOCKET)
        {
                closesocket (sock_);
                sock_ = INVALID_SOCKET;
        }
        state_ = State::Disconnected;
        buffer_.clear ();
}
