cmake_minimum_required (VERSION 2.8)

include(CTest)

add_executable (simpleappall main.cpp)
install(TARGETS simpleappall DESTINATION bin)

add_executable (simpleapptestall main.cpp)
if(WIN32)
    add_test(NAME simpleapptestall WORKING_DIRECTORY ${LIBRARY_OUTPUT_PATH} COMMAND simpleapptestall${CMAKE_EXECUTABLE_SUFFIX})
else()
    add_test(NAME simpleapptestall COMMAND simpleapptestall)
endif()
