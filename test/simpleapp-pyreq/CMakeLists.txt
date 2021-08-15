cmake_minimum_required (VERSION 2.8)

include(CTest)

add_executable (simpleapp main.cpp)
install(TARGETS simpleapp DESTINATION bin)

add_executable (simpleapptest main.cpp)
if(WIN32)
    add_test(NAME simpleapptest WORKING_DIRECTORY ${LIBRARY_OUTPUT_PATH} COMMAND simpleapptest${CMAKE_EXECUTABLE_SUFFIX})
else()
    add_test(NAME simpleapptest COMMAND simpleapptest)
endif()
