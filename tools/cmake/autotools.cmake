cmake_minimum_required (VERSION 2.8)

project(autotools)
enable_language(C CXX)

include(CTest)

include(ProcessorCount)
ProcessorCount(AUTOTOOLS_JOBS)

# set(AUTOTOOLS_FLAGS)

find_program(MAKE_EXE make)
if(NOT MAKE_EXE)
    message(FATAL_ERROR "Make build system not installed.")
endif()


@PREAMBLE@
preamble(AUTOTOOLS)
adjust_path(AUTOTOOLS_SYSTEM_PATH)

set(BUILD_DIR ${CMAKE_CURRENT_BINARY_DIR}/build)
file(MAKE_DIRECTORY ${BUILD_DIR})

file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/autotools.cmake "
set(ENV{CC} ${CMAKE_C_COMPILER})
set(ENV{CXX} ${CMAKE_CXX_COMPILER})

set(ENV{CFLAGS} ${AUTOTOOLS_C_FLAGS})
set(ENV{CXXFLAGS} ${AUTOTOOLS_CXX_FLAGS})
set(ENV{LDFLAGS} ${AUTOTOOLS_LINK_FLAGS})

set(ENV{PATH} \"${AUTOTOOLS_SYSTEM_PATH}${PATH_SEP}\$ENV{PATH}\")

execute_process(COMMAND  
    ${CMAKE_CURRENT_SOURCE_DIR}/configure
    --prefix=${CMAKE_INSTALL_PREFIX}
    ${CONFIGURE_OPTIONS}
    WORKING_DIRECTORY ${BUILD_DIR} 
)

")

execute_process(COMMAND ${CMAKE_COMMAND} -P ${CMAKE_CURRENT_BINARY_DIR}/autotools.cmake)

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
