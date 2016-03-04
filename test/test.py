import os, tarfile, shutil, cget.util


def is_string(obj):
    return isinstance(obj, basestring)

test_dir = os.path.dirname(os.path.realpath(__file__))

def get_path(p):
    return os.path.join(test_dir, p)

class TestError(Exception):
    def __init__(self, msg=None):
        self.msg = msg
    def __str__(self):
        if None: return "Test failed"
        else: return self.msg

def require(b):
    if not b: raise TestError()

def cmds(g, cwd):
    for x in g:
        print(x)
        require(cget.util.cmd(x, cwd=cwd))

def basename(p):
    d, b = os.path.split(p)
    if len(b) > 0: return b
    else: return basename(d)

def create_ar(archive, src):
    with tarfile.open(archive, mode='w:gz') as f:
        name = basename(src)
        f.add(src, arcname=name)

class TmpDir:
    def __init__(self, tmp_dir):
        self.tmp_dir = tmp_dir
    def __enter__(self):
        os.makedirs(self.tmp_dir)
        return self.tmp_dir
    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.tmp_dir)

def run_test(f):
    # TODO: Use test name
    with TmpDir(get_path('tmp')) as tmp_dir:
        f(tmp_dir)

def test_install(url, lib, alias=None):
    yield 'cget list'
    yield 'cget clean'
    yield 'cget list'
    yield 'cget install --verbose {0}'.format(url)
    yield 'cget list'
    yield 'cget pkg-config --list-all'
    yield 'cget pkg-config --exists {0}'.format(lib)
    yield 'cget pkg-config --cflags --libs {0}'.format(lib)
    if alias is None: yield 'cget remove {0}'.format(url)
    else: yield 'cget remove {0}'.format(alias)
    yield 'cget list'
    yield 'cget clean'
    yield 'cget list'

@run_test
def test_tar(d):
    ar = os.path.join(d, 'libsimple.tar.gz')
    create_ar(archive=ar, src=get_path('libsimple'))
    cmds(test_install(url=ar, lib='simple'), cwd=d)

# @run_test
def test_dir(d):
    cmds(test_install(url=get_path('libsimple'), lib='simple'), cwd=d)


