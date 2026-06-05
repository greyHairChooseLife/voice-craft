cmake_minimum_required(VERSION 3.16)
project(voice-craft-bot CXX)

# ADR-014: BWAPI Client API 봇 .exe, MinGW 크로스컴파일.
# 빌드 레시피는 spike 로 검증됨 (project-bwapi-client-build 메모리 참조).

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(BWAPI ${CMAKE_CURRENT_SOURCE_DIR}/third_party/bwapi)

# NOMINMAX: windows.h 의 min/max 매크로 차단. _WIN32_WINNT: shared memory/pipe API.
add_compile_definitions(NOMINMAX=1 _WIN32_WINNT=0x0501)

# vendored BWAPI Client 라이브러리 (prebuilt 없음 → 소스에서 함께 빌드).
# shim: <Windows.h> → <windows.h> (MinGW 소문자). 루트: svnrev.h stub.
include_directories(
    ${BWAPI}/shim
    ${BWAPI}
    ${BWAPI}/include
    ${BWAPI}/include/BWAPI/Client
    ${BWAPI}/BWAPIClient/Source
    ${BWAPI}/Util/Source
    ${BWAPI}/Storm
    ${BWAPI}/Shared
)

file(GLOB_RECURSE BWAPI_CLIENT_SRC
    ${BWAPI}/BWAPIClient/Source/*.cpp
    ${BWAPI}/Util/Source/Util/*.cpp
    ${BWAPI}/Storm/*.cpp
    ${BWAPI}/Shared/*.cpp
    ${BWAPI}/BWAPILIB/Source/*.cpp
    ${BWAPI}/BWAPILIB/UnitCommand.cpp
)

add_library(bwapiclient STATIC ${BWAPI_CLIENT_SRC})
# vendored 소스는 GCC 경고가 많음 → 빌드 노이즈 억제 (우리 코드엔 적용 안 함).
target_compile_options(bwapiclient PRIVATE -w)

add_executable(voice-craft-bot src/main.cpp src/voice_client.cpp)
# ADR-008: nlohmann/json single-header (bot/third_party/nlohmann/json.hpp).
target_include_directories(voice-craft-bot PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/third_party)
target_link_libraries(voice-craft-bot PRIVATE
    bwapiclient
    ws2_32
    -static -static-libgcc -static-libstdc++
)
set_target_properties(voice-craft-bot PROPERTIES OUTPUT_NAME "voice-craft-bot")
