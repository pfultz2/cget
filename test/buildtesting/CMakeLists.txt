cmake_minimum_required(VERSION 2.8)
project(buildtesting)

if(BUILD_TESTING)
    message(FATAL_ERROR "BUILD_TESTING is set. Aborting.")
endif()

add_custom_target(check)

install(CODE "")
