=================
Requirements file
=================

.. program:: requirements.txt

``cget`` will install all packages listed in the top-level ``requirements.txt`` file in the package. Each requirement is listed on a new line.

.. option:: <package-source>

This specifies the package source (see :ref:`pkg-src`) that will be installed.

.. option::  -H, --hash

    This specifies a hash checksum that should checked before installing the packaging. The type of hash needs to be specified with a colon first, and then the hash. So for md5, it would be something like ``md5:6fc67d80e915e63aacb39bc7f7da0f6c``.

.. option::  -b, --build             

    This is a dependency that is only needed for building the package. It is not installed as a dependent of the package, as such, it can be removed after the package has been installed. 

.. option::  -t, --test             

    ``cget`` will only install the dependency if the tests are going to be run. This dependency is also treated as a build dependency so the it can be removed after the package has been installed.

.. option::  -D, --define VAR=VALUE      

    Extra configuration variables to pass to CMake.

.. option::  -X, --cmake

    This specifies an alternative cmake file to be used to build the library. This is useful for packages that don't have a cmake file.


