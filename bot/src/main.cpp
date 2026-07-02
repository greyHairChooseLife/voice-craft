// voice-craft 봇 — A5 (ADR-014).
// BWAPI Client API 로 게임에 shared memory 연결, 매치 진입 시 채팅에 hello.
// A4: 명령 서버에 비차단 TCP 로 붙어 들어온 라인을 echo (ADR-004/005).
// A5: 라인을 JSON 으로 파싱해 produce_scv 를 train() 호출로 디스패치
// (ADR-006/008). winsock2.h 는 windows.h(BWAPI 가 끌어옴) 보다 먼저 와야 함 →
// voice_client.h 를 맨 위에.
#include "voice_client.h"

#include <BWAPI.h>
#include <BWAPI/Client.h>

#include <nlohmann/json.hpp>

#include <chrono>
#include <iostream>
#include <thread>

using namespace BWAPI;

static void
produce_scv ()
{
        for (Unit u : Broodwar->self ()->getUnits ())
        {
                if (u->getType () == UnitTypes::Terran_Command_Center)
                {
                        u->train (UnitTypes::Terran_SCV);
                        std::cout << "produce_scv: train(SCV) -> " << Broodwar->getLastError ()
                                  << std::endl;
                        return;
                }
        }
        std::cout << "produce_scv: no Command Center found" << std::endl;
}

static void
dispatch (const std::string &line)
{
        nlohmann::json j;
        try
        {
                j = nlohmann::json::parse (line);
        }
        catch (const nlohmann::json::parse_error &e)
        {
                std::cout << "dispatch: bad JSON, dropping line: " << e.what () << std::endl;
                return;
        }

        if (!j.contains ("cmd") || !j["cmd"].is_string ())
        {
                std::cout << "dispatch: missing/invalid 'cmd', dropping line" << std::endl;
                return;
        }

        const std::string cmd = j["cmd"].get<std::string> ();
        if (cmd == "produce_scv")
        {
                // 매치 밖에서 들어온 명령은 실행 대상 게임 상태가 없으니 드롭.
                if (Broodwar->isInGame ())
                        produce_scv ();
                else
                        std::cout << "dispatch: produce_scv ignored (not in game)" << std::endl;
        }
        else
        {
                std::cout << "dispatch: unknown cmd '" << cmd << "', dropping" << std::endl;
        }
}

namespace
{
// connect BWAPI.dll through shared-memory
void
reconnect ()
{
        while (!BWAPIClient.connect ())
        {
                std::this_thread::sleep_for (std::chrono::milliseconds{ 1000 });
        }
        std::cout << "connected to the BWAPI";
}

/**
 * 게임 상태를 업데이트합니다.
 * BWAPI 클라이언트를 업데이트하고, 연결이 끊어졌을 경우 재연결을 시도합니다.
 */
void
update_game_state ()
{
        BWAPIClient.update ();
        if (!BWAPIClient.isConnected ())
        {
                std::cout << "reconnecting..." << std::endl;
                reconnect ();
        }
}
}

int
main ()
{
        std::cout << "voice-craft-bot: connecting to BWAPI..." << std::endl;
        reconnect ();

        // 명령 서버 클라이언트. 봇↔서버 연결은 매치 수명과 무관하게 유지
        // (봇↔BWAPI 와 봇↔서버는 별개의 두 연결)
        VoiceClient voice ("127.0.0.1", 5000);
        auto on_line = [] (const std::string &line) { dispatch (line); };

        voice.poll (on_line); // just start connection to the voice-server

        while (true)
        {
                // 매치 진입 대기
                std::cout << "waiting to enter match" << std::endl;
                while (!Broodwar->isInGame ())
                {
                        std::this_thread::sleep_for (std::chrono::milliseconds{ 1000 });
                        update_game_state ();
                }

                // 매치 시작
                Broodwar->sendText ("hello voice-craft, this is SANGYEON");
                Broodwar->enableFlag (
                    Flag::UserInput); // 테스트용: 사람이 마우스/키보드로도 유닛을 조종할 수 있게

                // 매치 동안 프레임 진행
                while (Broodwar->isInGame ())
                {
                        update_game_state ();
                        voice.poll (on_line);
                }
                std::cout << "match ended" << std::endl;
        }

        return 0;
}
