cmake_minimum_required(VERSION 3.16)
project(probabilistic_council_cpp LANGUAGES CXX)

add_library(probabilistic_council src/council.cpp src/jevlike_tiny.cpp)
target_include_directories(probabilistic_council PUBLIC include)
target_compile_features(probabilistic_council PUBLIC cxx_std_17)
target_compile_options(probabilistic_council PRIVATE -Wall -Wextra -Wpedantic)
find_package(Threads REQUIRED)
target_link_libraries(probabilistic_council PUBLIC Threads::Threads)

add_executable(council_synthetic_pilot examples/synthetic_pilot.cpp)
target_link_libraries(council_synthetic_pilot PRIVATE probabilistic_council)

add_executable(jevlike_predict examples/jevlike_predict.cpp)
target_link_libraries(jevlike_predict PRIVATE probabilistic_council)
