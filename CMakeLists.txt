cmake_minimum_required(VERSION 3.15)
project(SheepStealer CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Optimised build unless told otherwise (ray tracing is much faster this way).
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

find_package(Threads REQUIRED)

add_executable(sheepstealer src/main.cpp)
target_link_libraries(sheepstealer PRIVATE Threads::Threads)
