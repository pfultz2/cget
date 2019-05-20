cmake_minimum_required (VERSION 2.8)

project(boost)
enable_language(C CXX)

include(CTest)

include(ProcessorCount)
ProcessorCount(B2_JOBS)

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
    get_property_list(${PREFIX}_LINK_FLAGS LINK_FLAGS)
    if(BUILD_SHARED_LIBS)
        string(APPEND ${PREFIX}_LINK_FLAGS " ${CMAKE_SHARED_LINKER_FLAGS}")
    else()
        string(APPEND ${PREFIX}_LINK_FLAGS " ${CMAKE_STATIC_LINKER_FLAGS}")
    endif()
    get_property_list(${PREFIX}_LINK_FLAGS LINK_FLAGS)

    set(${PREFIX}_C_FLAGS "${CMAKE_C_FLAGS} ${${PREFIX}_COMPILE_FLAGS} ${${PREFIX}_PIC_FLAG}")
    set(${PREFIX}_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${${PREFIX}_COMPILE_FLAGS} ${${PREFIX}_PIC_FLAG}")

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
preamble(B2)

set(B2_COMPILER ${CMAKE_CXX_COMPILER})
if (MSVC)
    set(B2_DEFAULT_TOOLCHAIN_TYPE "msvc")
else()
    if (CMAKE_CXX_COMPILER_ID MATCHES "AppleClang")
        set(B2_DEFAULT_TOOLCHAIN_TYPE "clang-darwin")
    elseif (CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        if(WIN32)
            set(B2_DEFAULT_TOOLCHAIN_TYPE "clang-win")
        elseif(APPLE)
            set(B2_DEFAULT_TOOLCHAIN_TYPE "clang-darwin")
        else()
            set(B2_DEFAULT_TOOLCHAIN_TYPE "clang-linux")
        endif()
    elseif (CMAKE_CXX_COMPILER_ID MATCHES "Intel")
        set(B2_DEFAULT_TOOLCHAIN_TYPE "intel")
    else()
        set(B2_DEFAULT_TOOLCHAIN_TYPE "gcc")
    endif()
endif()

set(BOOST_TOOLCHAIN "${B2_DEFAULT_TOOLCHAIN_TYPE}" CACHE STRING "Toolchain for b2")

set(B2_TARGET)

if(CYGWIN)
    set(B2_TARGET "cygwin")
elseif(WIN32)
    set(B2_TARGET "windows")
elseif(IOS)
    set(B2_TARGET "iphone")
elseif(APPLE)
    set(B2_TARGET "darwin")
elseif(ANDROID)
    set(B2_TARGET "android")
elseif("${CMAKE_SYSTEM_NAME}" MATCHES "Linux")
    set(B2_TARGET "linux")
elseif(UNIX)
    set(B2_TARGET "unix")
else()
    message(SEND_ERROR "Unsupported platform")
endif()

set(B2_DEFAULT_LAYOUT system)
if(CMAKE_CONFIGURATION_TYPES)
    set(B2_DEFAULT_LAYOUT tagged)
endif()

set(BOOST_LAYOUT ${B2_DEFAULT_LAYOUT} CACHE STRING "")

set(SEARCH_PATHS)
foreach(PATHS ${CMAKE_PREFIX_PATH})
    set(SEARCH_PATHS "${SEARCH_PATHS}
<include>${CMAKE_PREFIX_PATH}/include
<library-path>${CMAKE_PREFIX_PATH}/lib
")
endforeach()

# set(B2_TOOLCHAIN_VERSION ${CMAKE_CXX_COMPILER_VERSION})
set(B2_TOOLCHAIN_VERSION cget)
set(B2_CONFIG ${CMAKE_CURRENT_BINARY_DIR}/user-config.jam)

# TODO: Make this configurable
set(B2_THREAD_API "pthread")
if(WIN32)
    set(B2_THREAD_API "win32")
endif()
set(B2_CONFIG_CONTENT "
using ${BOOST_TOOLCHAIN} : ${B2_TOOLCHAIN_VERSION} : \"${B2_COMPILER}\" : 
<rc>${CMAKE_RC_COMPILER}
<archiver>${CMAKE_AR}
<ranlib>${CMAKE_RANLIB}
${SEARCH_PATHS}
;
")
message("${B2_CONFIG_CONTENT}")

file(WRITE ${B2_CONFIG} "${B2_CONFIG_CONTENT}")

find_program(B2_EXE b2)
if(NOT ${B2_EXE})
    if(CMAKE_HOST_WIN32)
        add_custom_target(bootstrap
            COMMAND cmd /c ${CMAKE_CURRENT_SOURCE_DIR}/tools/build/bootstrap.bat
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/tools/build/
        )
        set(B2_EXE "${CMAKE_CURRENT_SOURCE_DIR}/tools/build/b2.exe")
    else()
        add_custom_target(bootstrap
            COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/tools/build/bootstrap.sh
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/tools/build/
        )
        set(B2_EXE "${CMAKE_CURRENT_SOURCE_DIR}/tools/build/b2")
    endif()
    install(PROGRAMS ${B2_EXE} DESTINATION bin)
endif()

set(BOOST_LIBS)
get_cmake_property(_variableNames VARIABLES)
foreach (VAR ${_variableNames})
    if(VAR MATCHES "BOOST_WITH")
        string(TOLOWER ${VAR} LIB_FLAG)
        string(REPLACE "boost_without_" "--without-" LIB_FLAG ${LIB_FLAG})
        string(REPLACE "boost_with_" "--with-" LIB_FLAG ${LIB_FLAG})
        list(APPEND BOOST_LIBS ${LIB_FLAG})
    endif()
endforeach()

# Only add these arguments if they are not empty
if(NOT "${B2_C_FLAGS}" STREQUAL "")
    set(B2_C_FLAGS_ARG "cflags=${B2_C_FLAGS}")
endif()

if(NOT "${B2_CXX_FLAGS}" STREQUAL "")
    set(B2_CXX_FLAGS_ARG "cxxflags=${B2_CXX_FLAGS}")
endif()

if(NOT "${B2_LINK_FLAGS}" STREQUAL "")
    set(B2_LINK_FLAGS_ARG "linkflags=${B2_LINK_FLAGS}")
endif()

set(B2_VERBOSE_FLAG)
if(CMAKE_VERBOSE_MAKEFILE)
    set(B2_VERBOSE_FLAG -d+2)
endif()

set(B2_BUILD_DIR ${CMAKE_CURRENT_BINARY_DIR}/build)

set(BOOST_BUILD_FLAGS "" CACHE STRING "Additional flags to pass to boost build")

set(BUILD_FLAGS
    -q
    ${B2_VERBOSE_FLAG}
    -j ${B2_JOBS}
    --ignore-site-config
    --user-config=${B2_CONFIG}
    --build-dir=${B2_BUILD_DIR}
    address-model=${B2_ADDRESS_MODEL}
    link=${B2_LINK}
    target-os=${B2_TARGET}
    threadapi=${B2_THREAD_API}
    threading=multi
    toolset=${BOOST_TOOLCHAIN}-${B2_TOOLCHAIN_VERSION}
    variant=${B2_VARIANT}
    pch=off
    "${B2_C_FLAGS_ARG}"
    "${B2_CXX_FLAGS_ARG}"
    "${B2_LINK_FLAGS_ARG}"
    --layout=${BOOST_LAYOUT}
    --disable-icu
    ${BOOST_LIBS}
    --prefix=${CMAKE_INSTALL_PREFIX}
    --exec-prefix=${CMAKE_INSTALL_PREFIX}/bin
    --libdir=${CMAKE_INSTALL_PREFIX}/lib
    --includedir=${CMAKE_INSTALL_PREFIX}/include
    ${BOOST_BUILD_FLAGS}
)

string(REPLACE ";" " " BUILD_FLAGS_STR "${BUILD_FLAGS}")

add_custom_target(boost ALL
    COMMAND ${B2_ENV_COMMAND} ${B2_EXE} ${BUILD_FLAGS}
    COMMENT "${B2_EXE} ${BUILD_FLAGS_STR}"
    VERBATIM
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

add_custom_target(boost_install
    COMMAND ${B2_ENV_COMMAND} ${B2_EXE} ${BUILD_FLAGS} install
    COMMENT "${B2_EXE} ${BUILD_FLAGS_STR} install"
    VERBATIM
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

if(NOT ${B2_EXE})
    add_dependencies(boost bootstrap)
endif()

install(CODE "
execute_process(
    COMMAND ${CMAKE_COMMAND} --build . --target boost_install
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
)
")
