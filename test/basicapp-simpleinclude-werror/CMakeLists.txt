cmake_minimum_required (VERSION 2.8)

include(CTest)

if(NOT MSVC)
    add_compile_options(-Wall -Wextra -Wunused-parameter -Werror)
endif()

add_executable (basicapp main.cpp)
install(TARGETS basicapp DESTINATION bin)

add_executable (basciapptest main.cpp)
if(WIN32)
    add_test(NAME basicapptest WORKING_DIRECTORY ${LIBRARY_OUTPUT_PATH} COMMAND basciapptest${CMAKE_EXECUTABLE_SUFFIX})
else()
    add_test(NAME basicapptest COMMAND basciapptest)
endif()



