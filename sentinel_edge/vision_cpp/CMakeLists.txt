cmake_minimum_required(VERSION 3.10)
project(sentinel_vision)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Pybind11 via the python environment
find_package(pybind11 REQUIRED)

# Find OpenCV
find_package(OpenCV REQUIRED)

# Find NCNN (Expects installed config or NCNN_DIR variable)
find_package(ncnn REQUIRED)

# Deposit the compiled .so library directly into the core Python execution directory
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/../core)

pybind11_add_module(sentinel_vision vision_bindings.cpp)

# Link dependencies safely
target_link_libraries(sentinel_vision PRIVATE ${OpenCV_LIBS} ncnn)
