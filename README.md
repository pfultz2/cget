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

On windows, you may want to install pkgconfig-lite to support packages that use pkgconfig. This can be installed with `cget` as well:

    cget install pfultz2/pkgconfig

Quickstart
----------

We can also install cmake packages directly from source files, for example zlib:

    cget install http://zlib.net/zlib-1.2.11.tar.gz

However, its much easier to install recipes so we don't have to remember urls:

    cget install pfultz2/cget-recipes

Then we can install packages such as boost:

    cget install boost

Or curl:

    cget install curl

Documentation
-------------

See [here](http://cget.readthedocs.io/) for the latest documentation.


Supported platforms
-------------------

This is supported on python 2.7, 3.4, and 3.5. 


