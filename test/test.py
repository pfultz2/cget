import os, sys, tarfile, shutil

if os.name == 'posix' and sys.version_info[0] < 3:
    import subprocess32 as subprocess
else:
    import subprocess

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

def join_args(args):
    if is_string(args): return args
    else: return ' '.join(args)

def as_shell(args):
    if os.name == 'posix': return ['/bin/sh', '-c', join_args(args)]
    else: return args

def cmd(args, **kwargs):
    c = as_shell(args)
    print(c)
    child = subprocess.Popen(as_shell(args), **kwargs)
    child.communicate()
    if child.returncode != 0: raise TestError()

def cmds(g, cwd):
    for x in g:
        cmd(x, cwd=cwd)

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
        # pass
        shutil.rmtree(self.tmp_dir)

def run_test(f):
    # TODO: Use test name
    with TmpDir(get_path('tmp')) as tmp_dir:
        f(tmp_dir)

def test_install(url, lib):
    yield 'cget list'
    yield 'cget clean'
    yield 'cget list'
    yield 'cget install --verbose {0}'.format(url)
    yield 'cget list'
    yield 'cget pkg-config --list-all'
    yield 'cget pkg-config --exists {0}'.format(lib)
    yield 'cget pkg-config --cflags --libs {0}'.format(lib)
    yield 'cget remove {0}'.format(url)
    yield 'cget list'
    yield 'cget clean'
    yield 'cget list'

@run_test
def test_tar(d):
    ar = os.path.join(d, 'libsimple.tar.gz')
    create_ar(archive=ar, src=get_path('libsimple'))
    cmds(test_install(url=ar, lib='simple'), cwd=d)


