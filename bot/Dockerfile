# 32-bit Windows DLL 크로스컴파일 환경 (호스트에 MinGW 미설치).
# - g++-mingw-w64-i686: i686 타깃 C++ 크로스컴파일러
# - binutils-mingw-w64-i686: dlltool (BWAPI.dll → MinGW import lib)
# - mingw-w64-tools: gendef (.dll → .def)
# - cmake, make: 빌드 드라이버
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        g++-mingw-w64-i686 \
        binutils-mingw-w64-i686 \
        mingw-w64-tools \
        cmake \
        make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
