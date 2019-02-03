cmake_minimum_required (VERSION 2.8)

project(meson)
enable_language(C CXX)

include(CTest)
include(TestBigEndian)
include(CheckTypeSize)

# Find meson options first before any meson variables are defined
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


function(to_array OUT)
    set(ARRAY)
    separate_arguments(INPUT UNIX_COMMAND "${ARGN}") 
    foreach(ITEM ${INPUT})
        list(APPEND ARRAY "'${ITEM}'")
    endforeach()
    string(REPLACE ";" ", " ARRAY "${ARRAY}")
    set(${OUT} "${ARRAY}" PARENT_SCOPE)
endfunction()

@PREAMBLE@
auto_search()
preamble(MESON)

set(BUILD_DIR ${CMAKE_CURRENT_BINARY_DIR}/build)
file(MAKE_DIRECTORY ${BUILD_DIR})

set(MESON_CMD ${MESON_EXE} 
    ${CMAKE_CURRENT_SOURCE_DIR} 
    ${BUILD_DIR} 
    --prefix=${CMAKE_INSTALL_PREFIX}
    --buildtype=${MESON_VARIANT}
    --default-library=${MESON_LINK}
    ${MESON_OPTIONS})

if(CMAKE_CROSSCOMPILING)

to_array(C_ARGS ${MESON_C_FLAGS})
to_array(C_LINK_ARGS ${MESON_LINK_FLAGS})

string(TOLOWER "${CMAKE_SYSTEM_NAME}" MESON_SYSTEM)
string(TOLOWER "${CMAKE_SYSTEM_PROCESSOR}" MESON_CPU)
if(NOT CMAKE_SYSTEM_PROCESSOR)
    message(FATAL_ERROR "You must set the processor name when cross-compiling with meson")
endif()
set(MESON_CPU_FAMILY "${MESON_CPU}")

set(EXE_WRAPPER)
if(CMAKE_CROSSCOMPILING_EMULATOR)
set(EXE_WRAPPER "exe_wrapper = '${CMAKE_CROSSCOMPILING_EMULATOR}'")
endif()

set(ROOT)
if(CMAKE_FIND_ROOT_PATH)
# Root in meson can't be a list
list(GET CMAKE_FIND_ROOT_PATH 0 MESON_ROOT)
set(ROOT "root = '${MESON_ROOT}'")
endif()

set(SYSROOT)
if(CMAKE_SYSROOT)
set(SYSROOT "sys_root = '${CMAKE_SYSROOT}'")
endif()

find_program(PKG_CONFIG pkg-config)
check_type_size(int SIZEOF_INT)
check_type_size(wchar_t SIZEOF_WCHAR_T)
test_big_endian(BIG_ENDIAN)
set(MESON_ENDIAN little)
if(BIG_ENDIAN)
    set(MESON_ENDIAN big)
endif()
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/cross-file.txt "
[binaries]
c = '${CMAKE_C_COMPILER}'
cpp = '${CMAKE_CXX_COMPILER}'
ar = '${CMAKE_AR}'
pkgconfig = '${PKG_CONFIG}'
${EXE_WRAPPER}

[properties]
${ROOT}
${SYSROOT}

sizeof_int = ${SIZEOF_INT}
sizeof_wchar_t = ${SIZEOF_WCHAR_T}
sizeof_void* = ${CMAKE_SIZEOF_VOID_P}

alignment_char = 1
alignment_void* = ${CMAKE_SIZEOF_VOID_P}
alignment_double = ${CMAKE_SIZEOF_VOID_P}

has_function_printf = true

c_args = [${C_ARGS}]
c_link_args = [${C_LINK_ARGS}]

# The host machine is the target machine
[host_machine]
system = '${MESON_SYSTEM}'
cpu_family = '${MESON_CPU_FAMILY}'
cpu = '${MESON_CPU}'
endian = '${MESON_ENDIAN}'
")

list(APPEND MESON_CMD --cross-file ${CMAKE_CURRENT_BINARY_DIR}/cross-file.txt)
string(REPLACE ";" " " MESON_COMMENT "${MESON_CMD}")
message("${MESON_COMMENT}")
# Unset these variables as these cause meson cross compile to break
unset(ENV{CC})
unset(ENV{CXX})
unset(ENV{CFLAGS})
unset(ENV{CXXFLAGS})
unset(ENV{LDFLAGS})
exec(COMMAND ${MESON_BASE_ENV_COMMAND} ${MESON_CMD})
else()
string(REPLACE ";" " " MESON_COMMENT "${MESON_CMD}")
message("${MESON_COMMENT}")
exec(COMMAND ${MESON_ENV_COMMAND} ${MESON_CMD})
endif()

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
