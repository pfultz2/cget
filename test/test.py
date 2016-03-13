import os, tarfile, shutil, cget.util

try:
    from shlex import quote as quote
except ImportError:
    from pipes import quote as quote

__test_dir__ = os.path.dirname(os.path.realpath(__file__))

__cget_exe__ = cget.util.which('cget')

__has_pkg_config__ = cget.util.can(lambda: cget.util.which('pkg-config'))

def get_path(p):
    return os.path.join(__test_dir__, p)

def get_toolchain(p):
    return os.path.join(get_path('toolchains'), p)

class TestError(Exception):
    def __init__(self, msg=None):
        self.msg = msg
    def __str__(self):
        if None: return "Test failed"
        else: return self.msg

def require(b):
    if not b: raise TestError()

def should_fail(b):
    try:
        b()
        raise TestError()
    except:
        pass

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
        print(args)
        cget.util.cmd(*args, shell=True, cwd=self.tmp_dir, **kwargs)

    def cmds(self, g):
        for x in g:
            # if x.startswith('cget'):
            #     x = __cget_exe__ + x[4:]
            print(x)
            self.cmd(x)

    def write_to(self, f, content):
        p = self.get_path(f)
        cget.util.write_to(p, content)
        return p

    def get_path(self, p):
        return os.path.join(self.tmp_dir, p)

def run_test(f):
    # TODO: Use test name
    print('*****************************************')
    print('* Running test: {}'.format(f.__name__))
    print('*****************************************')
    with TestDir(get_path('tmp')) as d:
        f(d)
    print('*****************************************')
    print('* Completed test: {}'.format(f.__name__))
    print('*****************************************')

class CGetCmd:
    def __init__(self, prefix=None):
        self.prefix = prefix

    def __call__(self, arg, *args):
        p = [__cget_exe__, arg]
        if self.prefix is not None: p.append('--prefix {}'.format(self.prefix))
        return ' '.join(p+list(args))

def cget_cmd(*args):
    return CGetCmd()(*args)

# TODO: Test app by running it
def test_install(url, lib=None, alias=None, remove='remove', size=1, prefix=None):
    cg = CGetCmd(prefix=prefix)
    yield cg('init')
    yield cg('list')
    yield cg('clean')
    yield cg('list')
    yield cg('size', '0')
    yield cg('install', '--verbose --test', url)
    yield cg('size', str(size))
    yield cg('list')
    if __has_pkg_config__ and lib is not None:
        yield cg('pkg-config', '--list-all')
        yield cg('pkg-config', '--exists', lib)
        yield cg('pkg-config', '--cflags --libs', lib)
    if alias is None: yield cg(remove, '--verbose -y', url)
    else: yield cg(remove, '--verbose -y', alias)
    yield cg('size', '0')
    yield 'cget size 0'
    yield cg('list')
    yield cg('clean')
    yield cg('list')

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
def test_prefix(d):
    d.cmds(test_install(url=get_path('libsimple'), lib='simple', prefix=d.get_path('usr')))

@run_test
def test_rm(d):
    d.cmds(test_install(url=get_path('libsimple'), lib='simple', remove='rm'))

@run_test
def test_dir_alias(d):
    d.cmds(test_install(url='simple:'+get_path('libsimple'), lib='simple', alias='simple'))

@run_test
def test_reqs_alias_file(d):
    reqs_file = d.write_to('reqs', [quote('simple:'+get_path('libsimple'))])
    d.cmds(test_install(url='--file {}'.format(reqs_file), lib='simple', alias='simple'))

@run_test
def test_reqs_file(d):
    reqs_file = d.write_to('reqs', [quote(get_path('libsimple'))])
    d.cmds(test_install(url='--file {}'.format(reqs_file), lib='simple', alias=get_path('libsimple')))

@run_test
def test_reqs_alias_f(d):
    reqs_file = d.write_to('reqs', [quote('simple:'+get_path('libsimple'))])
    d.cmds(test_install(url='-f {}'.format(reqs_file), lib='simple', alias='simple'))

@run_test
def test_reqs_f(d):
    reqs_file = d.write_to('reqs', [quote(get_path('libsimple'))])
    d.cmds(test_install(url='-f {}'.format(reqs_file), lib='simple', alias=get_path('libsimple')))


# Basic app needs pkg-config
if __has_pkg_config__:
    @run_test
    def test_app_dir(d):
        d.cmds(test_install(url=get_path('basicapp'), lib='simple', alias='simple', size=2))

@run_test
def test_flags_fail(d):
    should_fail(lambda: d.cmds([cget_cmd('install', '--verbose --test -DCGET_FLAG=Off', get_path('libsimpleflag'))]))

@run_test
def test_flags(d):
    p = get_path('libsimpleflag')
    d.cmds(test_install(url='-DCGET_FLAG=On {}'.format(p), alias=p))

@run_test
def test_flags_fail_int(d):
    should_fail(lambda: d.cmds([cget_cmd('install --verbose --test -DCGET_FLAG=0', get_path('libsimpleflag'))]))

@run_test
def test_flags_int(d):
    p = get_path('libsimpleflag')
    d.cmds(test_install(url='-DCGET_FLAG=1 {}'.format(p), alias=p))

@run_test
def test_flags_fail_define(d):
    should_fail(lambda: d.cmds([cget_cmd('install', '--verbose --test --define CGET_FLAG=Off', get_path('libsimpleflag'))]))

@run_test
def test_flags_define(d):
    d.cmds([cget_cmd('install', '--verbose --test --define CGET_FLAG=On', get_path('libsimpleflag'))])

@run_test
def test_flags_toolchain(d):
    d.cmds([
        cget_cmd('init', '--toolchain', get_toolchain('toolchainflag.cmake')),
        cget_cmd('install', '--verbose --test', get_path('libsimpleflag'))
    ])

@run_test
def test_flags_toolchain_prefix(d):
    cg = CGetCmd(d.get_path('usr'))
    d.cmds([
        cg('init', '--toolchain', get_toolchain('toolchainflag.cmake')),
        cg('install', '--verbose --test', get_path('libsimpleflag'))
    ])

@run_test
def test_flags_reqs_f(d):
    p = get_path('libsimpleflag')
    reqs_file = d.write_to('reqs', [quote(p) + ' -DCGET_FLAG=On'])
    d.cmds(test_install(url='-f {}'.format(reqs_file), alias=p))

@run_test
def test_comments_reqs_f(d):
    p = get_path('libsimple')
    reqs_file = d.write_to('reqs', [quote(p) + ' #A comment', '# Another comment'])
    d.cmds(test_install(url='-f {}'.format(reqs_file), alias=p))


