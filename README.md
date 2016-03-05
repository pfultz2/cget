cget
====

Cmake package retrieval. This can be used to download and install cmake packages.

Getting cget
------------

`cget` can be simply installed using `pip`:

    pip install cget

Or installed directly with python:

    python setup.py install

Installing packages
-------------------

Package can be installed using the `install` command. There are several different sources packages can be installed from. When a packages is installed it configures a build directoy with cmake, and then builds the `all` target and the `install` target.

### Directory

This will install the package that is located at the directory:

    cget install ~/mylibrary/

There must be a CMakeLists.txt in the directory.

### File

An archived file of the package:

    cget install zlib-1.2.8.tar.gz

The archive will be unpacked and installed.

### URL

An url to the package:

   cget install http://zlib.net/zlib-1.2.8.tar.gz

### Github

A package can be installed directly from github using just the namespace and repo name. For example, John MacFarlane's implementation of Common Markdown can be installed like this:

    cget install jgm/cmark

A tag or branch can specified using the `@` symbol:

    cget install jgm/cmark@0.24.1

Aliasing
--------

Aliasing lets you pick a different name for the package. So when we are installing `zlib`, we could alias it as `zlib`:

    cget install zlib:http://zlib.net/zlib-1.2.8.tar.gz

This way the package can be referred to as `zlib` instead of `zlib.net/zlib-1.2.8.tar.gz`.

Removing a package
------------------

A package can be removed by using the same source name that was used to install the package:

    cget install http://zlib.net/zlib-1.2.8.tar.gz
    cget remove http://zlib.net/zlib-1.2.8.tar.gz

If an alias was specified, then that name needs to be used instead:

    cget install zlib:http://zlib.net/zlib-1.2.8.tar.gz
    cget remove zlib

Testing packages
----------------

The test suite for a package can be ran by using the `--test` flag. This will either build the `check` target or the `test` target. So if we want to run the tests for zlib we can do this:

    cget install --test http://zlib.net/zlib-1.2.8.tar.gz


Setting the prefix
------------------

By default, the packages are installed in the local directory `cget`. This can be changed by using the `--prefix` flag:

    cget install --prefix /usr/local zlib:http://zlib.net/zlib-1.2.8.tar.gz

The prefix can also be set with the `CGET_PREFIX` environment variable.

Integration with cmake
----------------------

By default, cget creates a cmake toolchain file with the settings necesary to build and find the libraries in the cget prefix. The toolchain file is at `$CGET_PREFIX/cget.cmake`. If another toolchain needs to be used, it can be specified with the `init` command:

    cget init --toolchain my_cmake_toolchain.cmake

Future work
-----------

* Windows support - Currently cget uses symlinks to manage installing and removing packages. On windows, an alternative may need to be necessary.
* Install a list packages from a file
* When installing a package, automatically install the packages from the requirements.txt file.
* Channels to better support versioning 

