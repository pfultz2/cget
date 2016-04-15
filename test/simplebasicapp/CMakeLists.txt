cmake_minimum_required (VERSION 2.8)

include(CTest)

add_executable (simplebasicapp2 main.cpp)
install(TARGETS simplebasicapp2 DESTINATION bin)

add_executable (simplebasicapp2test main.cpp)
if(WIN32)
    add_test(NAME simplebasicapp2test WORKING_DIRECTORY ${LIBRARY_OUTPUT_PATH} COMMAND simplebasicapp2test${CMAKE_EXECUTABLE_SUFFIX})
else()
    add_test(NAME simplebasicapp2test COMMAND simplebasicapp2test)
endif()
