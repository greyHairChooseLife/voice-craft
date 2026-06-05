// voice-craft 봇 — A4 (ADR-014).
// BWAPI Client API 로 게임에 shared memory 연결, 매치 진입 시 채팅에 hello.
// A4: 명령 서버에 비차단 TCP 로 붙어 들어온 라인을 echo (ADR-004/005).
// JSON 파싱·디스패치는 다음 단계에서 on_line 콜백 자리에 들어간다.
// winsock2.h 는 windows.h(BWAPI 가 끌어옴) 보다 먼저 와야 함 → voice_client.h 를 맨 위에.
#include "voice_client.h"

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

  // 명령 서버 클라이언트. 봇↔서버 연결은 매치 수명과 무관하게 유지된다
  // (ADR-004 note: 봇↔BWAPI 와 봇↔서버는 별개의 두 연결).
  VoiceClient voice("127.0.0.1", 5000);
  // A4: 받은 라인을 콘솔에 echo. 다음 단계에서 여기에 JSON 파싱·디스패치가 들어간다.
  auto on_line = [](const std::string& line) {
    std::cout << "voice recv: " << line << std::endl;
  };

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
      voice.poll(on_line);
    }

    // 테스트용: 사람이 마우스/키보드로도 유닛을 조종할 수 있게 (기본은 off).
    // 봇 명령 경로와 무관 — 디버깅 편의일 뿐이라 나중에 제거 가능.
    Broodwar->enableFlag(Flag::UserInput);

    // A3 통과 조건: 매치 진입 시 한 번만 출력
    Broodwar->sendText("hello voice-craft, this is SANGYEON");
    std::cout << "in match: sent hello" << std::endl;

    // 매치 동안 프레임 진행. ADR-005: update() 직후가 polling 지점.
    while (Broodwar->isInGame())
    {
      BWAPIClient.update();
      if (!BWAPIClient.isConnected())
        break;
      voice.poll(on_line);
    }
    std::cout << "match ended" << std::endl;
  }

  return 0;
}
