cmake_minimum_required (VERSION 2.8)

project(meson)
enable_language(C CXX)

include(CTest)

# find meson
find_program(MESON_EXE meson)
if(NOT MESON_EXE)
    message(FATAL_ERROR "Meson build system not installed.")
endif()

find_program(NINJA_EXE ninja)
if(NOT NINJA_EXE)
    message(FATAL_ERROR "Ninja build system not installed.")
endif()
get_filename_component(NINJA_PATH ${NINJA_EXE} DIRECTORY)

set(MESON_OPTIONS)
get_cmake_property(_variableNames VARIABLES)
foreach (VAR ${_variableNames})
    if(VAR MATCHES "MESON_")
        string(TOLOWER ${VAR} OPTION)
        string(REPLACE "_" "-" OPTION ${OPTION})
        string(REPLACE "meson-" "" OPTION ${OPTION})
        list(APPEND MESON_OPTIONS -D ${OPTION}=${${VAR}})
    endif()
endforeach()

@PREAMBLE@
preamble(MESON)
list(APPEND MESON_SYSTEM_PATH ${NINJA_PATH})
adjust_path(MESON_SYSTEM_PATH)

set(BUILD_DIR ${CMAKE_CURRENT_BINARY_DIR}/build)
file(MAKE_DIRECTORY ${BUILD_DIR})

set(MESON_CMD ${MESON_EXE} 
    ${CMAKE_CURRENT_SOURCE_DIR} 
    ${BUILD_DIR} 
    --prefix=${CMAKE_INSTALL_PREFIX}
    --buildtype=${MESON_VARIANT}
    --default-library=${MESON_LINK}
    ${MESON_OPTIONS})

string(REPLACE ";" " " MESON_COMMENT "${MESON_CMD}")

file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/meson.cmake "
set(ENV{CC} ${CMAKE_C_COMPILER})
set(ENV{CXX} ${CMAKE_CXX_COMPILER})

set(ENV{CFLAGS} ${MESON_C_FLAGS})
set(ENV{CXXFLAGS} ${MESON_CXX_FLAGS})
set(ENV{LDFLAGS} ${MESON_LINK_FLAGS})

set(ENV{PATH} \"${MESON_SYSTEM_PATH}${PATH_SEP}\$ENV{PATH}\")

execute_process(COMMAND ${MESON_CMD})

")

message("${MESON_COMMENT}")
execute_process(COMMAND ${CMAKE_COMMAND} -P ${CMAKE_CURRENT_BINARY_DIR}/meson.cmake)

add_custom_target(meson ALL
    COMMAND ${NINJA_EXE}
    COMMENT "${NINJA_EXE}"
    VERBATIM
    WORKING_DIRECTORY ${BUILD_DIR}
)

add_custom_target(meson_install
    COMMAND ${NINJA_EXE} install
    install
    COMMENT "${NINJA_EXE} install"
    VERBATIM
    WORKING_DIRECTORY ${BUILD_DIR}
)

install(CODE "
execute_process(
    COMMAND ${CMAKE_COMMAND} --build . --target meson_install
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
)
")
