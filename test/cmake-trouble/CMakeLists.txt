cmake_minimum_required (VERSION 2.8)

file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/dummy.cmake "")

install (FILES ${CMAKE_CURRENT_BINARY_DIR}/dummy.cmake DESTINATION bin/cmake)

include(CTest)

