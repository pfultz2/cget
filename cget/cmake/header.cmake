cmake_minimum_required (VERSION 2.8)

set(INCLUDE_DIR include CACHE STRING "Include directory")
message(STATUS "Include directory: ${INCLUDE_DIR}")
set(_INCLUDE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/${INCLUDE_DIR})
set(HEADER_DIR ${_INCLUDE_DIR} CACHE STRING "Directory of headers to be installed")
set(_HEADER_DIR ${CMAKE_CURRENT_SOURCE_DIR}/${HEADER_DIR})

if(NOT EXISTS ${_INCLUDE_DIR})
    if(EXISTS ${_HEADER_DIR})
        install(DIRECTORY ${_HEADER_DIR} DESTINATION include
            FILES_MATCHING 
            PATTERN "*.h"
            PATTERN "*.hpp"
            PATTERN "*.hh"
            PATTERN "*.hxx"
            PATTERN "*.ipp"
            PATTERN "*.tcc"
        )
    else()

        file(GLOB HEADER_FILES 
            *.h
            *.hpp
            *.hh
            *.hxx
            *.ipp
            *.tcc)
        install(FILES ${HEADER_FILES} DESTINATION include)
    endif()

else()
    install(DIRECTORY ${_INCLUDE_DIR}/ DESTINATION include
        FILES_MATCHING 
        PATTERN "*.h"
        PATTERN "*.hpp"
        PATTERN "*.hh"
        PATTERN "*.hxx"
        PATTERN "*.ipp"
        PATTERN "*.tcc"
    )

endif()
include(CTest)
