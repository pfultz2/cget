cget
====

Cmake package retrieval. This can be used to download and install cmake packages. The advantages of using `cget` are:

* Non-intrusive: There is no need to write special hooks in cmake to use `cget`. One cmake file is written and can be used to install a package with `cget` or standalone.
* Works out of the box: Since it uses the standard build and install of cmake, it already works with almost all cmake packages. There is no need to wait for packages to convert over to support `cget`. Standard cmake packages can be already installed immediately.
* Decentralized: Packages can be installed from anywhere, from github, urls, or local files.

Getting cget
------------

`cget` can be simply installed using `pip`(you can get pip from [here](https://pip.pypa.io/en/stable/installing/)):

    pip install cget

Or installed directly with python:

    python setup.py install

On windows, you may want to install pkgconfig-lite to support packages that use pkgconfig.

Installing packages
-------------------

A package can be installed using the `install` command. When a package is installed, `cget` configures a build directory with cmake, and then builds the `all` target and the `install` target. So, essentially, `cget` will run the equivalent of these commands on the package to install it:

    mkdir build
    cd build
    cmake ..
    cmake --build .
    cmake --build . --target install

However, `cget` will always create the build directory out of source. It will also setup cmake to point to the correct prefix and install directories.

There are several different sources where a packages can be installed from.

### Directory

This will install the package that is located at the directory:

    cget install ~/mylibrary/

There must be a `CMakeLists.txt` in the directory.

### File

An archived file of the package:

    cget install zlib-1.2.8.tar.gz

The archive will be unpacked and installed.

### URL

An url to the package:

    cget install http://zlib.net/zlib-1.2.8.tar.gz

The file will be downloaded, unpacked, and installed.

### Github

A package can be installed directly from github using just the namespace and repo name. For example, John MacFarlane's implementation of CommonMark in C called [cmark](https://github.com/jgm/cmark) can be installed like this:

    cget install jgm/cmark

A tag or branch can specified using the `@` symbol:

    cget install jgm/cmark@0.24.1

Installing dependencies
-----------------------

All dependencies listed in the `requirements.txt` will be installed with the package as well.


Aliasing
--------

Aliasing lets you pick a different name for the package. So when we are installing `zlib`, we could alias it as `zlib`:

    cget install zlib,http://zlib.net/zlib-1.2.8.tar.gz

This way the package can be referred to as `zlib` instead of `http://zlib.net/zlib-1.2.8.tar.gz`.

Removing a package
------------------

A package can be removed by using the same source name that was used to install the package:

    cget install http://zlib.net/zlib-1.2.8.tar.gz
    cget remove http://zlib.net/zlib-1.2.8.tar.gz

If an alias was specified, then the name of the alias must be used instead:

    cget install zlib,http://zlib.net/zlib-1.2.8.tar.gz
    cget remove zlib

Testing packages
----------------

The test suite for a package can be ran before installing it, by using the `--test` flag. This will either build the `check` target or run `ctest`. So if we want to run the tests for zlib we can do this:

    cget install --test http://zlib.net/zlib-1.2.8.tar.gz


Setting the prefix
------------------

By default, the packages are installed in the local directory `cget`. This can be changed by using the `--prefix` flag:

    cget install --prefix /usr/local zlib:http://zlib.net/zlib-1.2.8.tar.gz

The prefix can also be set with the `CGET_PREFIX` environment variable.

Integration with cmake
----------------------

By default, cget creates a cmake toolchain file with the settings necessary to build and find the libraries in the cget prefix. The toolchain file is at `$CGET_PREFIX/cget.cmake`. If another toolchain needs to be used, it can be specified with the `init` command:

    cget init --toolchain my_cmake_toolchain.cmake

Also, the C++ version can be set for the toolchain as well:

    cget init --std=c++14

Which is necessary to use modern C++ on many compilers.


Supported platforms
-------------------

This is supported on python 2.7, 3.4, and 3.5. However, windows is only supported using python 3. 

Future work
-----------

* Channels to better support versioning 

