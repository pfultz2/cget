cmake_minimum_required (VERSION 2.8)

install (FILES include/simple.h DESTINATION include)
configure_file(simple.pc.in simple.pc)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/simple.pc DESTINATION lib/pkgconfig)

include(CTest)

add_executable (simpletest test.cpp)
if(WIN32)
    add_test(NAME simpletest WORKING_DIRECTORY ${LIBRARY_OUTPUT_PATH} COMMAND simpletest${CMAKE_EXECUTABLE_SUFFIX})
else()
    add_test(NAME simpletest COMMAND simpletest)
endif()

include_directories(include)

