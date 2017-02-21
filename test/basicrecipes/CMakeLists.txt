
file(GLOB_RECURSE RECIPES RELATIVE ${CMAKE_CURRENT_SOURCE_DIR} recipes/*.txt recipes/*.cmake)

macro(get_directory_base OUTPUT_VAR DIR)
    if(CMAKE_VERSION VERSION_LESS "3.0")
        get_filename_component(${OUTPUT_VAR} ${DIR} PATH ${ARGN})
    else()
        get_filename_component(${OUTPUT_VAR} ${DIR} DIRECTORY ${ARGN})
    endif()
endmacro()
get_directory_base(CGET_TEST_DIR ${CMAKE_CURRENT_SOURCE_DIR} CACHE)

message(STATUS "CGET_TEST_DIR: ${CGET_TEST_DIR}")

string(REPLACE "\\" "/" TEST_DIR "${CGET_TEST_DIR}")
message(STATUS "TEST_DIR: ${TEST_DIR}")

foreach(RECIPE ${RECIPES})
    configure_file(${CMAKE_CURRENT_SOURCE_DIR}/${RECIPE} ${CMAKE_CURRENT_BINARY_DIR}/${RECIPE} @ONLY)
    get_directory_base(RECIPE_DIR ${RECIPE})
    install(FILES ${CMAKE_CURRENT_BINARY_DIR}/${RECIPE} DESTINATION etc/cget/${RECIPE_DIR})
    message(STATUS "RECIPE: ${RECIPE}")
    message(STATUS "RECIPE_DIR: ${RECIPE_DIR}")
endforeach()

enable_testing()
