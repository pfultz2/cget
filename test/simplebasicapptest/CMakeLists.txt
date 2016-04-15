cmake_minimum_required (VERSION 2.8)

include(CTest)

add_executable (simplebasicapp main.cpp)
install(TARGETS simplebasicapp DESTINATION bin)

add_executable (simplebasicapptest main.cpp)
if(WIN32)
    add_test(NAME simplebasicapptest WORKING_DIRECTORY ${LIBRARY_OUTPUT_PATH} COMMAND simplebasicapptest${CMAKE_EXECUTABLE_SUFFIX})
else()
    add_test(NAME simplebasicapptest COMMAND simplebasicapptest)
endif()
