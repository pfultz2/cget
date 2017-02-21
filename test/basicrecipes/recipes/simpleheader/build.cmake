cmake_minimum_required (VERSION 2.8)

set(INCLUDE_DIR include CACHE PATH "Include directory")

install(DIRECTORY ${INCLUDE_DIR}/ DESTINATION include
    FILES_MATCHING 
    PATTERN "*.h"
    PATTERN "*.hpp"
    PATTERN "*.hh"
    PATTERN "*.hxx"
)

include(CTest)
