cmake_minimum_required (VERSION 2.8)

project(autotools)
enable_language(C CXX)

include(CTest)

include(ProcessorCount)
ProcessorCount(AUTOTOOLS_JOBS)

find_program(MAKE_EXE make)
if(NOT MAKE_EXE)
    message(FATAL_ERROR "Make build system not installed.")
endif()

set(CONFIGURE_OPTIONS ${AUTOTOOLS_CONFIGURE_OPTIONS})

@PREAMBLE@
auto_search()
preamble(AUTOTOOLS)

set(BUILD_DIR ${CMAKE_CURRENT_BINARY_DIR}/build)
file(MAKE_DIRECTORY ${BUILD_DIR})

if(CMAKE_CROSSCOMPILING)
execute_process(COMMAND ${CMAKE_C_COMPILER} -dumpmachine OUTPUT_VARIABLE AUTOTOOLS_TARGET)
string(STRIP "${AUTOTOOLS_TARGET}" AUTOTOOLS_TARGET)
execute_process(COMMAND cc -dumpmachine OUTPUT_VARIABLE AUTOTOOLS_HOST)
string(STRIP "${AUTOTOOLS_HOST}" AUTOTOOLS_HOST)
list(APPEND CONFIGURE_OPTIONS
    --build=${AUTOTOOLS_HOST}
    --host=${AUTOTOOLS_TARGET}
    --target=${AUTOTOOLS_TARGET}
)
endif()

execute_process(COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/configure --help OUTPUT_VARIABLE AUTOTOOLS_AVAILABLE_OPTIONS)

if(AUTOTOOLS_AVAILABLE_OPTIONS MATCHES "--disable-option-checking")
    set(AUTOTOOL_IMPLICIT_CONFIGURE_OPTIONS On CACHE BOOL "")
else()
    set(AUTOTOOL_IMPLICIT_CONFIGURE_OPTIONS Off CACHE BOOL "")
endif()

if(AUTOTOOL_IMPLICIT_CONFIGURE_OPTIONS)
    list(APPEND CONFIGURE_OPTIONS --disable-option-checking)
    if(BUILD_SHARED_LIBS)
        list(APPEND CONFIGURE_OPTIONS --disable-static)
        list(APPEND CONFIGURE_OPTIONS --enable-shared)
    else()
        list(APPEND CONFIGURE_OPTIONS --enable-static)
        list(APPEND CONFIGURE_OPTIONS --disable-shared)
    endif()
endif()

message(STATUS "Configure options: ${CONFIGURE_OPTIONS}")

# TODO: Check flags of configure script
exec(COMMAND ${AUTOTOOLS_ENV_COMMAND} ${CMAKE_CURRENT_SOURCE_DIR}/configure
    --prefix=${CMAKE_INSTALL_PREFIX}
    ${CONFIGURE_OPTIONS}
    WORKING_DIRECTORY ${BUILD_DIR})

add_custom_target(autotools ALL
    COMMAND ${MAKE_EXE} -j ${AUTOTOOLS_JOBS}
    COMMENT "${MAKE_EXE} -j ${AUTOTOOLS_JOBS}"
    VERBATIM
    WORKING_DIRECTORY ${BUILD_DIR}
)

add_custom_target(autotools_install
    COMMAND ${MAKE_EXE} install
    install
    COMMENT "${MAKE_EXE} install"
    VERBATIM
    WORKING_DIRECTORY ${BUILD_DIR}
)

install(CODE "
execute_process(
    COMMAND ${CMAKE_COMMAND} --build . --target autotools_install
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
)
")
