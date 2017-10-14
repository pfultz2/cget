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

set(AUTOTOOLS_SYSTEM_PATH)
foreach(P ${CMAKE_PREFIX_PATH} ${CMAKE_SYSTEM_PREFIX_PATH})
    list(APPEND AUTOTOOLS_SYSTEM_PATH ${P}/bin)
endforeach()
macro(adjust_path PATH_LIST)
    string(REPLACE ";" ":" ${PATH_LIST} "${${PATH_LIST}}")
endmacro()
adjust_path(AUTOTOOLS_SYSTEM_PATH)


get_directory_property(AUTOTOOLS_COMPILE_OPTIONS COMPILE_OPTIONS)
string(REPLACE ";" " " AUTOTOOLS_FLAGS "${AUTOTOOLS_COMPILE_OPTIONS}")
get_directory_property(AUTOTOOLS_INCLUDE_DIRECTORIES INCLUDE_DIRECTORIES)
foreach(DIR ${AUTOTOOLS_INCLUDE_DIRECTORIES})
    if(MSVC)
        set(AUTOTOOLS_FLAGS "/I ${DIR}")
    else()
        set(AUTOTOOLS_FLAGS "-I${DIR}")
    endif()
endforeach()
get_directory_property(AUTOTOOLS_COMPILE_DEFINITIONS COMPILE_DEFINITIONS)
foreach(DEF ${AUTOTOOLS_COMPILE_DEFINITIONS})
    if(MSVC)
        set(AUTOTOOLS_FLAGS "/D ${DEF}")
    else()
        set(AUTOTOOLS_FLAGS "-D${DEF}")
    endif()
endforeach()

set(AUTOTOOLS_LINK "static")
if(BUILD_SHARED_LIBS)
    set(AUTOTOOLS_LINK "shared")
endif()

set(AUTOTOOLS_PIC_FLAG)
if(CMAKE_POSITION_INDEPENDENT_CODE AND NOT WIN32)
    set(AUTOTOOLS_PIC_FLAG "-fPIC")
endif()
set(AUTOTOOLS_LINK_FLAGS ${CMAKE_STATIC_LINKER_FLAGS})
if(BUILD_SHARED_LIBS)
    set(AUTOTOOLS_LINK_FLAGS ${CMAKE_SHARED_LINKER_FLAGS})
endif()
set(AUTOTOOLS_C_FLAGS "${CMAKE_C_FLAGS} ${AUTOTOOLS_FLAGS} ${AUTOTOOLS_PIC_FLAG}")
set(AUTOTOOLS_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${AUTOTOOLS_FLAGS} ${AUTOTOOLS_PIC_FLAG}")

string(TOLOWER "${CMAKE_BUILD_TYPE}" BUILD_TYPE)
if(BUILD_TYPE STREQUAL "debug")
    set(AUTOTOOLS_VARIANT "debug")
else()
    set(AUTOTOOLS_VARIANT "release")
endif()

set(BUILD_DIR ${CMAKE_CURRENT_BINARY_DIR}/build)
file(MAKE_DIRECTORY ${BUILD_DIR})

file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/autotools.cmake "
set(ENV{CC} ${CMAKE_C_COMPILER})
set(ENV{CXX} ${CMAKE_CXX_COMPILER})

set(ENV{CFLAGS} ${AUTOTOOLS_C_FLAGS})
set(ENV{CXXFLAGS} ${AUTOTOOLS_CXX_FLAGS})
set(ENV{LDFLAGS} ${AUTOTOOLS_LINK_FLAGS})

set(ENV{PATH} \"${AUTOTOOLS_SYSTEM_PATH}:\$ENV{PATH}\")

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
