
file(MAKE_DIRECTORY ${CMAKE_INSTALL_PREFIX}/sdir)
file(WRITE ${CMAKE_INSTALL_PREFIX}/sdir/file.txt "*")
file(MAKE_DIRECTORY ${CMAKE_INSTALL_PREFIX}/data)
message(STATUS "symlink: ${CMAKE_INSTALL_PREFIX}/data/sdir -> ${CMAKE_INSTALL_PREFIX}/sdir")
execute_process(COMMAND ln -sf ${CMAKE_INSTALL_PREFIX}/sdir ${CMAKE_INSTALL_PREFIX}/data/sdir)
