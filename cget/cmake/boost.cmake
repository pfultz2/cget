
include(CTest)

include(ProcessorCount)
ProcessorCount(B2_JOBS)

set(B2_LINK "static")
if(BUILD_SHARED_LIBS)
    set(B2_LINK "shared")
endif()

set(B2_LINK_FLAGS ${CMAKE_STATIC_LINKER_FLAGS})
if(BUILD_SHARED_LIBS)
    set(B2_LINK_FLAGS ${CMAKE_SHARED_LINKER_FLAGS})
endif()

string(TOLOWER "{CMAKE_BUILD_TYPE}" BUILD_TYPE)
if(BUILD_TYPE STREQUAL "debug")
    set(B2_VARIANT "debug")
else()
    set(B2_VARIANT "release")
endif()

set(B2_ADDRESS_MODEL "64")
if(CMAKE_SIZEOF_VOID_P EQUAL 4)
    set(B2_ADDRESS_MODEL "32")
endif()

set(B2_COMPILER ${CMAKE_CXX_COMPILER})
if (MSVC)
    set(B2_TOOLCHAIN_TYPE "msvc")
else()
    if (CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        if(WIN32)
            set(B2_TOOLCHAIN_TYPE "clang-win")
        else()
            set(B2_TOOLCHAIN_TYPE "clang-linux")
        endif()
    elseif (CMAKE_CXX_COMPILER_ID MATCHES "AppleClang")
        set(B2_TOOLCHAIN_TYPE "clang-darwin")
    elseif (CMAKE_CXX_COMPILER_ID MATCHES "Intel")
        set(B2_TOOLCHAIN_TYPE "intel")
    else()
        set(B2_TOOLCHAIN_TYPE "gcc")
    endif()
endif()

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

# set(B2_TOOLCHAIN_VERSION ${CMAKE_CXX_COMPILER_VERSION})
set(B2_TOOLCHAIN_VERSION cget)
set(B2_CONFIG ${CMAKE_CURRENT_BINARY_DIR}/user-config.jam)

# TODO: Set threadapi:
# threadapi=win32
string(CONFIGURE 
"using ${B2_TOOLCHAIN_TYPE} : ${B2_TOOLCHAIN_VERSION} : \"${B2_COMPILER}\" : 
<rc>${CMAKE_RC_COMPILER}
<archiver>${CMAKE_AR}
<ranlib>${CMAKE_RANLIB}
<address-model>${B2_ADDRESS_MODEL}
<link>${B2_LINK}
<variant>${B2_VARIANT}
<cxxflags>${CMAKE_CXX_FLAGS}
<cflags>${CMAKE_C_FLAGS}
<linkflags>${B2_LINK_FLAGS} 
\;
"
B2_CONFIG_CONTENT)
message("${B2_CONFIG_CONTENT}")

file(WRITE ${B2_CONFIG} ${B2_CONFIG_CONTENT})

find_program(B2_EXE b2)
if(NOT ${B2_EXE})
    # TODO: Check for windows host not target
    if(CMAKE_HOST_WIN32)
        add_custom_target(bootstrap
            COMMAND cmd /c ${CMAKE_CURRENT_SOURCE_DIR}/tools/build/bootstrap.bat
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/tools/build/
        )
    else()
        add_custom_target(bootstrap
            COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/tools/build/bootstrap.sh
            WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/tools/build/
        )
    endif()
    set(B2_EXE "${CMAKE_CURRENT_SOURCE_DIR}/tools/build/b2${CMAKE_EXECUTABLE_SUFFIX}")
    install(PROGRAMS ${B2_EXE} DESTINATION bin)
endif()

set(BOOST_LIBS)
get_cmake_property(_variableNames VARIABLES)
foreach (VAR ${_variableNames})
    if(VAR MATCHES "BOOST_WITH")
        string(TOLOWER ${VAR} LIB_FLAG)
        string(REPLACE "_" "-" LIB_FLAG ${LIB_FLAG})
        string(REPLACE "boost" "-" LIB_FLAG ${LIB_FLAG})
        list(APPEND BOOST_LIBS ${LIB_FLAG})
    endif()
endforeach()

set(BUILD_FLAGS
    -q
    -j ${B2_JOBS}
    --ignore-site-config
    --user-config=${B2_CONFIG}
    address-model=${B2_ADDRESS_MODEL}
    link=${B2_LINK}
    threading=multi
    toolset=${B2_TOOLCHAIN_TYPE}-${B2_TOOLCHAIN_VERSION}
    target-os=${B2_TARGET}
    --layout=tagged
    --disable-icu
    ${BOOST_LIBS}
    --prefix=${CMAKE_INSTALL_PREFIX}
    --exec-prefix=${CMAKE_INSTALL_PREFIX}/bin
    --libdir=${CMAKE_INSTALL_PREFIX}/lib
    --includedir=${CMAKE_INSTALL_PREFIX}/include
)

add_custom_target(boost ALL
    COMMAND ${B2_EXE}
    ${BUILD_FLAGS}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

if(NOT ${B2_EXE})
    add_dependencies(boost bootstrap)
endif()

install(CODE "
execute_process(
    COMMAND ${B2_EXE} 
    ${BUILD_FLAGS}
    install
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)
")
