#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd $DIR

# Run test for simple lib
tar -cvf testlib/libsimple.tar.gz libsimple/
cd testlib
bash run
cd $DIR
rm testlib/libsimple.tar.gz
