import os, tarfile, shutil, cget.util


def is_string(obj):
    return isinstance(obj, basestring)

__test_dir__ = os.path.dirname(os.path.realpath(__file__))

__cget_exe__ = cget.util.which('cget')

def get_path(p):
    return os.path.join(__test_dir__, p)

class TestError(Exception):
    def __init__(self, msg=None):
        self.msg = msg
    def __str__(self):
        if None: return "Test failed"
        else: return self.msg

def require(b):
    if not b: raise TestError()

def basename(p):
    d, b = os.path.split(p)
    if len(b) > 0: return b
    else: return basename(d)

def create_ar(archive, src):
    with tarfile.open(archive, mode='w:gz') as f:
        name = basename(src)
        f.add(src, arcname=name)

class TestDir:
    def __init__(self, tmp_dir):
        self.tmp_dir = tmp_dir
    def __enter__(self):
        os.makedirs(self.tmp_dir)
        return self
    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.tmp_dir)

    def cmd(self, *args, **kwargs):
        cget.util.cmd(*args, shell=True, cwd=self.tmp_dir, **kwargs)

    def cmds(self, g):
        for x in g:
            if x.startswith('cget'):
                x = __cget_exe__ + x[4:]
            print(x)
            self.cmd(x)

    def get_path(self, p):
        return os.path.join(self.tmp_dir, p)

def run_test(f):
    # TODO: Use test name
    with TestDir(get_path('tmp')) as d:
        f(d)

def test_install(url, lib, alias=None):
    yield 'cget list'
    yield 'cget clean'
    yield 'cget list'
    yield 'cget install --verbose --test {0}'.format(url)
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
    ar = d.get_path('libsimple.tar.gz')
    create_ar(archive=ar, src=get_path('libsimple'))
    d.cmds(test_install(url=ar, lib='simple'))

@run_test
def test_tar_alias(d):
    ar = d.get_path('libsimple.tar.gz')
    create_ar(archive=ar, src=get_path('libsimple'))
    d.cmds(test_install(url='simple:'+ar, lib='simple', alias='simple'))

@run_test
def test_dir(d):
    d.cmds(test_install(url=get_path('libsimple'), lib='simple'))

@run_test
def test_dir_alias(d):
    d.cmds(test_install(url='simple:'+get_path('libsimple'), lib='simple', alias='simple'))


