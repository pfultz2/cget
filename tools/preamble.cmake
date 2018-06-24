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
macro(preamble PREFIX)
    set(${PREFIX}_PATH ${CMAKE_PREFIX_PATH} ${CMAKE_SYSTEM_PREFIX_PATH})
    if(CMAKE_CROSSCOMPILING)
        set(${PREFIX}_PACKAGE_PATH ${CMAKE_FIND_ROOT_PATH})
    else()
        set(${PREFIX}_PACKAGE_PATH ${${PREFIX}_PATH})
    endif()
    set(${PREFIX}_SYSTEM_PATH)
    foreach(P ${${PREFIX}_PATH})
        list(APPEND ${PREFIX}_SYSTEM_PATH ${P}/bin)
    endforeach()
    adjust_path(${PREFIX}_SYSTEM_PATH)

    set(${PREFIX}_PKG_CONFIG_PATH)
    foreach(P ${${PREFIX}_PACKAGE_PATH})
        foreach(SUFFIX lib lib64 share)
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
    # TODO: Link libraries

    set(${PREFIX}_C_FLAGS "${CMAKE_C_FLAGS} ${${PREFIX}_COMPILE_FLAGS} ${${PREFIX}_PIC_FLAG}")
    set(${PREFIX}_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${${PREFIX}_COMPILE_FLAGS} ${${PREFIX}_PIC_FLAG}")

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

    # TODO: Set PKG_CONFIG_SYSROOT_DIR
    set(PKG_CONFIG_ENV "PKG_CONFIG_PATH=${${PREFIX}_PKG_CONFIG_PATH}")
    if(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE STREQUAL "ONLY")
        list(APPEND PKG_CONFIG_ENV "PKG_CONFIG_LIBDIR=${${PREFIX}_PKG_CONFIG_PATH}")
    endif()

    # TODO: Adjust pkgconfig path based on cross-compiling
    set(${PREFIX}_ENV_COMMAND ${CMAKE_COMMAND} -E env
        "CC=${CMAKE_C_COMPILER}"
        "CXX=${CMAKE_CXX_COMPILER}"
        "CFLAGS=${${PREFIX}_C_FLAGS}"
        "CXXFLAGS=${${PREFIX}_CXX_FLAGS}"
        "LDFLAGS=${${PREFIX}_LINK_FLAGS}"
        "PATH=${${PREFIX}_SYSTEM_PATH}${PATH_SEP}$ENV{PATH}"
        ${PKG_CONFIG_ENV}) 
endmacro()
# preamble
