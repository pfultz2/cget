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

set(CONFIGURE_OPTIONS)

@PREAMBLE@
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
