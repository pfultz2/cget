cmake_minimum_required (VERSION 2.8)

macro(SUBDIRLIST result curdir)
    file(GLOB children RELATIVE ${curdir} ${curdir}/*)
    set(dirlist)
    foreach(child ${children})
        if(IS_DIRECTORY ${curdir}/${child})
            list(APPEND dirlist ${child})
        endif()
    endforeach()
    set(${result} ${dirlist})
endmacro()

subdirlist(DIRS ${CMAKE_CURRENT_SOURCE_DIR})

foreach(subdir ${DIRS})
    install(DIRECTORY ${subdir}/ DESTINATION ${subdir} USE_SOURCE_PERMISSIONS)
endforeach()

include(CTest)
