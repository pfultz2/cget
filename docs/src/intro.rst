============
Introduction
============

Cmake package retrieval. This can be used to download and install cmake packages. The advantages of using ``cget`` are:

* Non-intrusive: There is no need to write special hooks in cmake to use ``cget``. One cmake file is written and can be used to install a package with ``cget`` or standalone.
* Works out of the box: Since it uses the standard build and install of cmake, it already works with almost all cmake packages. There is no need to wait for packages to convert over to support ``cget``. Standard cmake packages can be already installed immediately.
* Decentralized: Packages can be installed from anywhere, from github, urls, or local files.


---------------
Installing cget
---------------

``cget`` can be simply installed using ``pip`` (you can get pip from `here <https://pip.pypa.io/en/stable/installing/>`_)::

    pip install cget

Or installed directly with python::

    python setup.py install

On windows, you may want to install pkgconfig-lite to support packages that use pkgconfig. This can be installed with ``cget`` as well:

    cget install pfultz2/pkgconfig

----------
Quickstart
----------

""""""""""""""""""""
Installing a package
""""""""""""""""""""

Any library that uses cmake to build can be built and installed as a package with ``cget``. A source for package can be from many areas (see :ref:`pkg-src`). We can simply install ``zlib`` with its URL::

    cget install http://zlib.net/zlib-1.2.8.tar.gz

We can install the package from github as well, using a shorten form. For example, installing John MacFarlane's implementation of CommonMark in C called `cmark <https://github.com/jgm/cmark>`_::

    cget install jgm/cmark


""""""""""""""""""
Removing a package
""""""""""""""""""

A package can be removed by using the same source name that was used to install the package::

    cget install http://zlib.net/zlib-1.2.8.tar.gz
    cget remove http://zlib.net/zlib-1.2.8.tar.gz

If an alias was specified, then the name of the alias must be used instead::

    cget install zlib,http://zlib.net/zlib-1.2.8.tar.gz
    cget remove zlib

""""""""""""""""
Testing packages
""""""""""""""""

The test suite for a package can be ran before installing it, by using the ``--test`` flag. This will either build the ``check`` target or run ``ctest``. So if we want to run the tests for zlib we can do this::

    cget install --test http://zlib.net/zlib-1.2.8.tar.gz


""""""""""""""""""
Setting the prefix
""""""""""""""""""

By default, the packages are installed in the local directory ``cget``. This can be changed by using the ``--prefix`` flag::

    cget install --prefix /usr/local zlib:http://zlib.net/zlib-1.2.8.tar.gz

The prefix can also be set with the ``CGET_PREFIX`` environment variable.

""""""""""""""""""""""
Integration with cmake
""""""""""""""""""""""

By default, cget creates a cmake toolchain file with the settings necessary to build and find the libraries in the cget prefix. The toolchain file is at ``$CGET_PREFIX/cget.cmake``. If another toolchain needs to be used, it can be specified with the ``init`` command::

    cget init --toolchain my_cmake_toolchain.cmake

Also, the C++ version can be set for the toolchain as well::

    cget init --std=c++14

Which is necessary to use modern C++ on many compilers.

