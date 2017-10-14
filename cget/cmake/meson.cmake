cmake_minimum_required (VERSION 2.8)

project(meson)
enable_language(C CXX)

include(CTest)

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

set(MESON_SYSTEM_PATH ${NINJA_PATH})
foreach(P ${CMAKE_PREFIX_PATH} ${CMAKE_SYSTEM_PREFIX_PATH})
    list(APPEND MESON_SYSTEM_PATH ${P}/bin)
endforeach()

get_directory_property(MESON_COMPILE_OPTIONS COMPILE_OPTIONS)
string(REPLACE ";" " " MESON_FLAGS "${MESON_COMPILE_OPTIONS}")
get_directory_property(MESON_INCLUDE_DIRECTORIES INCLUDE_DIRECTORIES)
foreach(DIR ${MESON_INCLUDE_DIRECTORIES})
    if(MSVC)
        set(MESON_FLAGS "/I ${DIR}")
    else()
        set(MESON_FLAGS "-I${DIR}")
    endif()
endforeach()
get_directory_property(MESON_COMPILE_DEFINITIONS COMPILE_DEFINITIONS)
foreach(DEF ${MESON_COMPILE_DEFINITIONS})
    if(MSVC)
        set(MESON_FLAGS "/D ${DEF}")
    else()
        set(MESON_FLAGS "-D${DEF}")
    endif()
endforeach()

set(MESON_LINK "static")
if(BUILD_SHARED_LIBS)
    set(MESON_LINK "shared")
endif()

set(MESON_PIC_FLAG)
if(CMAKE_POSITION_INDEPENDENT_CODE AND NOT WIN32)
    set(MESON_PIC_FLAG "-fPIC")
endif()
set(MESON_LINK_FLAGS ${CMAKE_STATIC_LINKER_FLAGS})
if(BUILD_SHARED_LIBS)
    set(MESON_LINK_FLAGS ${CMAKE_SHARED_LINKER_FLAGS})
endif()
set(MESON_C_FLAGS "${CMAKE_C_FLAGS} ${MESON_FLAGS} ${MESON_PIC_FLAG}")
set(MESON_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${MESON_FLAGS} ${MESON_PIC_FLAG}")

string(TOLOWER "${CMAKE_BUILD_TYPE}" BUILD_TYPE)
if(BUILD_TYPE STREQUAL "debug")
    set(MESON_VARIANT "debug")
else()
    set(MESON_VARIANT "release")
endif()

set(BUILD_DIR ${CMAKE_CURRENT_BINARY_DIR}/build)
file(MAKE_DIRECTORY ${BUILD_DIR})

set(PATH_SEP ":")
if(WIN32)
    set(PATH_SEP ";")
endif()
macro(adjust_path PATH_LIST)
    string(REPLACE ";" "${PATH_SEP}" ${PATH_LIST} "${${PATH_LIST}}")
endmacro()
adjust_path(MESON_SYSTEM_PATH)

set(MESON_CMD ${MESON_EXE} 
    ${CMAKE_CURRENT_SOURCE_DIR} 
    ${BUILD_DIR} 
    --prefix=${CMAKE_INSTALL_PREFIX}
    --buildtype=${MESON_VARIANT}
    --default-library=${MESON_LINK}
    ${MESON_OPTIONS})

string(REPLACE ";" " " MESON_COMMENT "${MESON_CMD}")

file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/meson.cmake "
set(ENV{CC} ${CMAKE_C_COMPILER})
set(ENV{CXX} ${CMAKE_CXX_COMPILER})

set(ENV{CFLAGS} ${MESON_C_FLAGS})
set(ENV{CXXFLAGS} ${MESON_CXX_FLAGS})
set(ENV{LDFLAGS} ${MESON_LINK_FLAGS})

set(ENV{PATH} \"${MESON_SYSTEM_PATH}${PATH_SEP}\$ENV{PATH}\")

execute_process(COMMAND ${MESON_CMD})

")

message("${MESON_COMMENT}")
execute_process(COMMAND ${CMAKE_COMMAND} -P ${CMAKE_CURRENT_BINARY_DIR}/meson.cmake)

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
