cmake_minimum_required (VERSION 2.8)

project(boost)
enable_language(C CXX)

include(CTest)

include(ProcessorCount)
ProcessorCount(B2_JOBS)

@PREAMBLE@
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

set(BOOST_PYTHON "" CACHE STRING "python executable to use for boost build")
set(BOOST_BOOTSTRAP_ARGS "" CACHE STRING "additional arguments to boost bootstrap")

if (BOOST_PYTHON)
    find_program(BOOST_PYTHON_FOUND ${BOOST_PYTHON} REQUIRED)
    get_filename_component(BOOST_PYTHON_FOUND_REAL "${BOOST_PYTHON_FOUND}" REALPATH)
    message(STATUS "found python: '${BOOST_PYTHON_FOUND}' -> '${BOOST_PYTHON_FOUND_REAL}'")
    set(B2_CONFIG_CONTENT "${B2_CONFIG_CONTENT}
    using python : : ${BOOST_PYTHON_FOUND_REAL} ;
    ")
endif (BOOST_PYTHON)

message("${B2_CONFIG_CONTENT}")

file(WRITE ${B2_CONFIG} "${B2_CONFIG_CONTENT}")

find_program(B2_EXE b2)
if(NOT ${B2_EXE})
    if (BOOST_PYTHON)
        set(BOOST_BOOTSTRAP_PYTHON_ARG "--with-python=${BOOST_PYTHON_FOUND_REAL}")
    endif (BOOST_PYTHON)
    if(CMAKE_HOST_WIN32)
        add_custom_target(bootstrap
            COMMAND cmd /c ${CMAKE_CURRENT_SOURCE_DIR}/bootstrap.bat ${BOOST_BOOTSTRAP_ARGS} ${BOOST_BOOTSTRAP_PYTHON_ARG}
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        )
        set(B2_EXE "${CMAKE_CURRENT_SOURCE_DIR}/tools/build/b2.exe")
    else()
        add_custom_target(bootstrap
            COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/bootstrap.sh ${BOOST_BOOTSTRAP_ARGS} ${BOOST_BOOTSTRAP_PYTHON_ARG}
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        )
        set(B2_EXE "${CMAKE_CURRENT_SOURCE_DIR}/b2")
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
