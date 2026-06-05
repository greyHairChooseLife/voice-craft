// voice-craft 봇 — A5 (ADR-014).
// BWAPI Client API 로 게임에 shared memory 연결, 매치 진입 시 채팅에 hello.
// A4: 명령 서버에 비차단 TCP 로 붙어 들어온 라인을 echo (ADR-004/005).
// A5: 라인을 JSON 으로 파싱해 produce_scv 를 train() 호출로 디스패치 (ADR-006/008).
// winsock2.h 는 windows.h(BWAPI 가 끌어옴) 보다 먼저 와야 함 → voice_client.h 를 맨 위에.
#include "voice_client.h"

#include <BWAPI.h>
#include <BWAPI/Client.h>

#include <nlohmann/json.hpp>

#include <iostream>
#include <thread>
#include <chrono>

using namespace BWAPI;

// ADR-006: Command Center 에서 SCV 한 기 훈련.
// MVP-A 는 스톡 melee 시작 상태(CC 1기 + SCV 4기 + 미네랄 50, ADR-007)라 후보 선택이 필요 없다 —
// 첫 Command Center 를 찾아 train. 호출 직후 getLastError() 로깅:
// train() 은 미네랄/서플라이/큐 부족 시 조용히 실패하므로 로그가 있어야 이유를 안다.
static void produce_scv()
{
  for (Unit u : Broodwar->self()->getUnits())
  {
    if (u->getType() == UnitTypes::Terran_Command_Center)
    {
      u->train(UnitTypes::Terran_SCV);
      std::cout << "produce_scv: train(SCV) -> " << Broodwar->getLastError() << std::endl;
      return;
    }
  }
  std::cout << "produce_scv: no Command Center found" << std::endl;
}

// A5: 한 라인을 JSON 으로 파싱해 cmd 필드로 디스패치.
// ADR-008: 파싱 실패·미지 명령은 로깅 후 드롭, 봇 크래시 금지.
static void dispatch(const std::string& line)
{
  nlohmann::json j;
  try
  {
    j = nlohmann::json::parse(line);
  }
  catch (const nlohmann::json::parse_error& e)
  {
    std::cout << "dispatch: bad JSON, dropping line: " << e.what() << std::endl;
    return;
  }

  if (!j.contains("cmd") || !j["cmd"].is_string())
  {
    std::cout << "dispatch: missing/invalid 'cmd', dropping line" << std::endl;
    return;
  }

  const std::string cmd = j["cmd"].get<std::string>();
  if (cmd == "produce_scv")
  {
    // 매치 밖에서 들어온 명령은 실행 대상 게임 상태가 없으니 드롭.
    if (Broodwar->isInGame())
      produce_scv();
    else
      std::cout << "dispatch: produce_scv ignored (not in game)" << std::endl;
  }
  else
  {
    std::cout << "dispatch: unknown cmd '" << cmd << "', dropping" << std::endl;
  }
}

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
  // A5: 받은 라인마다 JSON 파싱·디스패치 (A4 의 echo 콜백 자리를 그대로 대체).
  auto on_line = [](const std::string& line) { dispatch(line); };

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
