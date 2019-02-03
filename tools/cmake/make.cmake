cmake_minimum_required (VERSION 2.8)

project(make_build)
enable_language(C CXX)

include(CTest)

include(ProcessorCount)
ProcessorCount(MAKE_JOBS)

find_program(MAKE_EXE make)
if(NOT MAKE_EXE)
    message(FATAL_ERROR "Make build system not installed.")
endif()

@PREAMBLE@
auto_search()
preamble(MAKE)

set(MAKE_VARIABLES
        "CC=${CMAKE_C_COMPILER}"
        "CXX=${CMAKE_CXX_COMPILER}"
        "CFLAGS=${MAKE_C_FLAGS}"
        "CXXFLAGS=${MAKE_CXX_FLAGS}"
        "LDFLAGS=${MAKE_LINK_FLAGS}"
        "PREFIX=${CMAKE_INSTALL_PREFIX}"
)

set(BUILD_DIR ${CMAKE_CURRENT_BINARY_DIR}/build)
file(MAKE_DIRECTORY ${BUILD_DIR})

add_custom_target(make_build ALL
    COMMAND ${MAKE_ENV_COMMAND} ${MAKE_EXE} -C ${CMAKE_SOURCE_DIR} -j ${MAKE_JOBS} ${MAKE_VARIABLES}
    COMMENT "${MAKE_EXE} -j ${MAKE_JOBS}"
    VERBATIM
    WORKING_DIRECTORY ${BUILD_DIR}
)

add_custom_target(make_install
    COMMAND ${MAKE_ENV_COMMAND} ${MAKE_EXE} -C ${CMAKE_SOURCE_DIR} install ${MAKE_VARIABLES}
    install
    COMMENT "${MAKE_EXE} install"
    VERBATIM
    WORKING_DIRECTORY ${BUILD_DIR}
)

install(CODE "
execute_process(
    COMMAND ${CMAKE_COMMAND} --build . --target make_install
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
)
")
