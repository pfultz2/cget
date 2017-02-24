cmake_minimum_required (VERSION 2.8)

if(DEFINED CGET_FLAG1 AND DEFINED CGET_FLAG2)
if(CGET_FLAG1 AND CGET_FLAG2)
install (FILES include/simple.h DESTINATION include)

include(CTest)

add_executable (simpletest test.cpp)
if(WIN32)
    add_test(NAME simpletest WORKING_DIRECTORY ${LIBRARY_OUTPUT_PATH} COMMAND simpletest${CMAKE_EXECUTABLE_SUFFIX})
else()
    add_test(NAME simpletest COMMAND simpletest)
endif()

include_directories(include)
endif()
else()
    message("CGET_FLAGs not defined")
endif()
