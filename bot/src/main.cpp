// voice-craft 봇 — A3 최소 버전 (ADR-014).
// BWAPI Client API 로 게임에 shared memory 연결, 매치 진입 시 채팅에 hello.
// A5 에서 TCP, A6 에서 JSON 디스패치가 이 루프에 들어온다.
#include <BWAPI.h>
#include <BWAPI/Client.h>

#include <iostream>
#include <thread>
#include <chrono>

using namespace BWAPI;

static void reconnect()
{
  while (!BWAPIClient.connect())
  {
    std::this_thread::sleep_for(std::chrono::milliseconds{1000});
  }
}

int main()
{
  std::cout << "voice-craft-bot: connecting to BWAPI..." << std::endl;
  reconnect();

  while (true)
  {
    // 매치 진입 대기
    std::cout << "waiting to enter match" << std::endl;
    while (!Broodwar->isInGame())
    {
      BWAPIClient.update();
      if (!BWAPIClient.isConnected())
      {
        std::cout << "reconnecting..." << std::endl;
        reconnect();
      }
    }

    // A3 통과 조건: 매치 진입 시 한 번만 출력
    Broodwar->sendText("hello voice-craft, this is SANGYEON");
    std::cout << "in match: sent hello" << std::endl;

    // 매치 동안 프레임 진행 (여기가 A5 TCP polling / A6 dispatch 지점)
    while (Broodwar->isInGame())
    {
      BWAPIClient.update();
      if (!BWAPIClient.isConnected())
        break;
    }
    std::cout << "match ended" << std::endl;
  }

  return 0;
}
