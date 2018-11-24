cmake_minimum_required (VERSION 2.8)

add_library(simple simple.cpp)
target_include_directories(simple PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>)
set_target_properties(simple PROPERTIES SOVERSION 1)

install (FILES include/simple.h DESTINATION include)
install(TARGETS simple 
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    INCLUDES DESTINATION include)

include(CTest)

add_executable (simpletest test.cpp)
target_link_libraries(simpletest simple)
if(WIN32)
    add_test(NAME simpletest WORKING_DIRECTORY ${LIBRARY_OUTPUT_PATH} COMMAND simpletest${CMAKE_EXECUTABLE_SUFFIX})
else()
    add_test(NAME simpletest COMMAND simpletest)
endif()


