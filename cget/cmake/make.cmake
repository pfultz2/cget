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
