==========
Using cget
==========

-------------------------
Installing cmake packages
-------------------------

When package is installed from one of the package sources(see :ref:`pkg-src`) using the :ref:`install` command, ``cget`` will run the equivalent cmake commands to install it::

    mkdir build
    cd build
    cmake -DCMAKE_TOOLCHAIN_FILE=$CGET_PREFIX/cget/cget.cmake -DCMAKE_INSTALL_PREFIX=$CGET_PREFIX ..
    cmake --build .
    cmake --build . --target install

However, ``cget`` will always create the build directory out of source. The ``cget.cmake`` is a toolchain file that is setup by ``cget``, so that cmake can find the installed packages. Other settings can be added about the toolchain as well(see :ref:`init`).

The ``cget.cmake`` toolchain file can be useful for cmake projects to use. This will enable cmake to find the dependencies installed by ``cget`` as well::

    cmake -DCMAKE_TOOLCHAIN_FILE=$CGET_PREFIX/cget/cget.cmake ..

Instead of passing in the toolchain, ``cget`` provides a build command to take of this already(see :ref:`build`). This will configure cmake with ``cget.cmake`` toolchain file and build the project::

    cget build

By default, it will build the ``all`` target, but a target can be specified as well::

    cget build --target some_target

For projects that don't use cmake, then its matter of searching for the dependencies in ``CGET_PREFIX``. Also, it is quite common for packages to provide ``pkg-config`` files for managing dependencies. So, ``cget`` provides a ``pkg-config`` command that will search for the dependencies that ``cget`` has installed. For example, ``cget pkg-config`` can be used to link in the dependencies for zlib without needing cmake::

    cget install zlib,http://zlib.net/zlib-1.2.8.tar.gz
    g++ src.cpp `cget pkg-config zlib --cflags --libs`


-----------------------------
Installing non-cmake packages
-----------------------------

""""""""""""""""""
Using custom cmake
""""""""""""""""""

For packages that don't support building with cmake. A cmake file can be provided to build the package. This can either build the sources or bootstrap the build system for the package::

    cget install SomePackage --cmake mycmake.cmake

"""""""""""""""""""""
Header-only libraries
"""""""""""""""""""""

For libraries that are header-only, ``cget`` provides a cmake file ``header`` to install the headers. For example, Boost.Preprocessor library can be installed like this::

    cget install boostorg/preprocessor --cmake header

By default, it installs the headers in the 'include' directory, but this can be changed by setting the ``INCLUDE_DIR`` cmake variable::

    cget install boostorg/preprocessor --cmake header -DINCLUDE_DIR=include

""""""""
Binaries
""""""""

For binaries, ``cget`` provides a cmake file ``binary`` which will install all the files in the package without building any source files. For example, the clang binaries for ubuntu can be installed like this::

    cget install clang,http://llvm.org/releases/3.9.0/clang+llvm-3.9.0-x86_64-linux-gnu-ubuntu-16.04.tar.xz  --cmake binary
