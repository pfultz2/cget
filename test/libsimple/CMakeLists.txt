
install (DIRECTORY include DESTINATION include)
configure_file(simple.pc.in simple.pc)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/simple.pc DESTINATION lib/pkgconfig)

add_executable (simpletest test.cpp)
if(WIN32)
    add_test(NAME simpletest WORKING_DIRECTORY ${LIBRARY_OUTPUT_PATH} COMMAND simpletest${CMAKE_EXECUTABLE_SUFFIX})
else()
    add_test(NAME simpletest COMMAND simpletest)
endif()

include_directories(include)
