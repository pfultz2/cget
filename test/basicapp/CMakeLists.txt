cmake_minimum_required (VERSION 2.8)

include(CTest)

add_executable (basicapp main.cpp)
find_package(PkgConfig)
pkg_check_modules(BASICAPP_PKGS REQUIRED simple)
include_directories(${BASICAPP_PKGS_INCLUDE_DIRS})
target_link_libraries(basicapp ${BASICAPP_PKGS_LDFLAGS})
install(TARGETS basicapp DESTINATION bin)

add_executable (basciapptest main.cpp)
target_link_libraries(basciapptest ${BASICAPP_PKGS_LDFLAGS})
if(WIN32)
    add_test(NAME basicapptest WORKING_DIRECTORY ${LIBRARY_OUTPUT_PATH} COMMAND basciapptest${CMAKE_EXECUTABLE_SUFFIX})
else()
    add_test(NAME basicapptest COMMAND basciapptest)
endif()



