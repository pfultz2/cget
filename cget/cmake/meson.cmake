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

# preamble
set(PATH_SEP ":")
if(CMAKE_HOST_WIN32)
    set(PATH_SEP ";")
endif()
macro(adjust_path PATH_LIST)
    string(REPLACE ";" "${PATH_SEP}" ${PATH_LIST} "${${PATH_LIST}}")
endmacro()
macro(get_property_list VAR PROP)
    get_directory_property(${VAR} ${PROP})
    string(REPLACE ";" " " ${VAR} "${${VAR}}")
endmacro()
function(exec)
    execute_process(${ARGN} RESULT_VARIABLE RESULT)
    if(NOT RESULT EQUAL 0)
        message(FATAL_ERROR "Process failed: ${ARGN}")
    endif()
endfunction()
if(CMAKE_CROSSCOMPILING)
    set(PREFIX_PATH ${CMAKE_FIND_ROOT_PATH})
else()
    set(PREFIX_PATH ${CMAKE_PREFIX_PATH})
endif()
if(CMAKE_CROSSCOMPILING)
    set(PREFIX_SYSTEM_PATH)
else()
    set(PREFIX_SYSTEM_PATH ${CMAKE_SYSTEM_PREFIX_PATH})
endif()
macro(auto_search)
    foreach(P ${PREFIX_PATH})
        include_directories(SYSTEM ${P}/include)
        link_directories(${P}/lib)
    endforeach()
endmacro()
macro(preamble PREFIX)
    set(${PREFIX}_ADDRESS_MODEL "64")
    if(CMAKE_SIZEOF_VOID_P EQUAL 4)
        set(${PREFIX}_ADDRESS_MODEL "32")
    endif()
    set(${PREFIX}_SYSTEM_PATH)
    foreach(P ${PREFIX_PATH} ${PREFIX_SYSTEM_PATH})
        list(APPEND ${PREFIX}_SYSTEM_PATH ${P}/bin)
    endforeach()
    adjust_path(${PREFIX}_SYSTEM_PATH)

    set(${PREFIX}_PKG_CONFIG_PATH)
    foreach(P ${PREFIX_PATH} ${PREFIX_SYSTEM_PATH})
        foreach(SUFFIX lib lib${${PREFIX}_ADDRESS_MODEL} share)
            list(APPEND ${PREFIX}_PKG_CONFIG_PATH ${P}/${SUFFIX}/pkgconfig)
        endforeach()
    endforeach()
    adjust_path(${PREFIX}_PKG_CONFIG_PATH)

    get_property_list(${PREFIX}_COMPILE_FLAGS COMPILE_OPTIONS)
    get_directory_property(${PREFIX}_INCLUDE_DIRECTORIES INCLUDE_DIRECTORIES)
    foreach(DIR ${${PREFIX}_INCLUDE_DIRECTORIES})
        if(MSVC)
            string(APPEND ${PREFIX}_COMPILE_FLAGS " /I ${DIR}")
        else()
            string(APPEND ${PREFIX}_COMPILE_FLAGS " -isystem ${DIR}")
        endif()
    endforeach()
    get_directory_property(${PREFIX}_COMPILE_DEFINITIONS COMPILE_DEFINITIONS)
    foreach(DEF ${${PREFIX}_COMPILE_DEFINITIONS})
        if(MSVC)
            string(APPEND ${PREFIX}_COMPILE_FLAGS " /D ${DEF}")
        else()
            string(APPEND ${PREFIX}_COMPILE_FLAGS " -D${DEF}")
        endif()
    endforeach()
    get_directory_property(${PREFIX}_LINK_DIRECTORIES LINK_DIRECTORIES)
    foreach(LIB_DIR ${${PREFIX}_LINK_DIRECTORIES})
        if(MSVC)
            string(APPEND ${PREFIX}_LINK_FLAGS " /LIBPATH:${LIB_DIR}")
        else()
            string(APPEND ${PREFIX}_LINK_FLAGS " -L ${LIB_DIR}")
        endif()
    endforeach()

    set(${PREFIX}_LINK "static")
    if(BUILD_SHARED_LIBS)
        set(${PREFIX}_LINK "shared")
    endif()

    set(${PREFIX}_PIC_FLAG)
    if(CMAKE_POSITION_INDEPENDENT_CODE AND NOT WIN32)
        set(${PREFIX}_PIC_FLAG "-fPIC")
    endif()

    set(${PREFIX}_C_FLAGS "${CMAKE_C_FLAGS} ${${PREFIX}_COMPILE_FLAGS} ${${PREFIX}_PIC_FLAG}")
    set(${PREFIX}_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${${PREFIX}_COMPILE_FLAGS} ${${PREFIX}_PIC_FLAG}")
    if (APPLE)
        set(${PREFIX}_C_FLAGS "${${PREFIX}_C_FLAGS} -isysroot ${CMAKE_OSX_SYSROOT}")
        set(${PREFIX}_CXX_FLAGS "${${PREFIX}_CXX_FLAGS} -isysroot ${CMAKE_OSX_SYSROOT}")
        set(${PREFIX}_LINK_FLAGS "${${PREFIX}_LINK_FLAGS} -isysroot ${CMAKE_OSX_SYSROOT}")
    endif (APPLE)

    get_property_list(${PREFIX}_LINK_FLAGS LINK_FLAGS)
    if(BUILD_SHARED_LIBS)
        string(APPEND ${PREFIX}_LINK_FLAGS " ${CMAKE_SHARED_LINKER_FLAGS}")
    else()
        string(APPEND ${PREFIX}_LINK_FLAGS " ${CMAKE_STATIC_LINKER_FLAGS}")
    endif()
    get_property_list(${PREFIX}_LINK_FLAGS LINK_FLAGS)

    foreach(LANG C CXX)
        foreach(DIR ${CMAKE_${LANG}_STANDARD_INCLUDE_DIRECTORIES})
            if(MSVC)
                string(APPEND ${PREFIX}_${LANG}_FLAGS " /I ${DIR}")
            else()
                string(APPEND ${PREFIX}_${LANG}_FLAGS " -isystem ${DIR}")
            endif()
        endforeach()
    endforeach()

    # Compensate for extra spaces in the flags, which can cause build failures
    foreach(VAR ${PREFIX}_C_FLAGS ${PREFIX}_CXX_FLAGS ${PREFIX}_LINK_FLAGS)
        string(REGEX REPLACE "  +" " " ${VAR} "${${VAR}}")
        string(STRIP "${${VAR}}" ${VAR})
    endforeach()

    # TODO: Check against the DEBUG_CONFIGURATIONS property
    string(TOLOWER "${CMAKE_BUILD_TYPE}" BUILD_TYPE)
    if(BUILD_TYPE STREQUAL "debug")
        set(${PREFIX}_VARIANT "debug")
    else()
        set(${PREFIX}_VARIANT "release")
    endif()

    set(${PREFIX}_BASE_ENV_COMMAND ${CMAKE_COMMAND} -E env
        "PATH=${${PREFIX}_SYSTEM_PATH}${PATH_SEP}$ENV{PATH}"
        "PKG_CONFIG_PATH=${${PREFIX}_PKG_CONFIG_PATH}"
    )

    # TODO: Set also PKG_CONFIG_SYSROOT_DIR
    if(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE STREQUAL "ONLY")
        list(APPEND ${PREFIX}_BASE_ENV_COMMAND "PKG_CONFIG_LIBDIR=${${PREFIX}_PKG_CONFIG_PATH}")
    endif()

    set(${PREFIX}_ENV_COMMAND ${${PREFIX}_BASE_ENV_COMMAND}
        "CC=${CMAKE_C_COMPILER}"
        "CXX=${CMAKE_CXX_COMPILER}"
        "CFLAGS=${${PREFIX}_C_FLAGS}"
        "CXXFLAGS=${${PREFIX}_CXX_FLAGS}"
        "LDFLAGS=${${PREFIX}_LINK_FLAGS}") 
endmacro()
# preamble

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
