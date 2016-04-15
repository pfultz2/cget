import os, tarfile, shutil, cget.util, multiprocessing

from six.moves import shlex_quote

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
        if 'cwd' not in kwargs: kwargs['cwd'] = self.tmp_dir
        cget.util.cmd(*args, shell=True, **kwargs)

    def cmds(self, g, **kwargs):
        for x in g:
            print(x)
            self.cmd(x, **kwargs)

    def write_to(self, f, content):
        p = self.get_path(f)
        cget.util.write_to(p, content)
        return p

    def get_path(self, p):
        return os.path.join(self.tmp_dir, p)

def print_banner(s):
    print('********************************************************************************')
    print('* {}'.format(s))
    print('********************************************************************************')

def run_test(f):
    print_banner('Running test: {}'.format(f.__name__))
    try:
        with TestDir(get_path('tmp-' + f.__name__)) as d:
            f(d)
    except:
        print_banner('Failed test: {}'.format(f.__name__))
        raise
    print_banner('Completed test: {}'.format(f.__name__))


tests = []

def test(f):
    tests.append(f)
    return f

def run_tests():
    # for t in tests: run_test(t)
    p = multiprocessing.Pool()
    r = p.map_async(run_test, tests)
    r.wait()
    p.close()
    p.join()
    if not r.successful(): raise TestError()

def remove_empty_elements(xs):
    for x in xs:
        if x is not None:
            s = str(x)
            if len(s) > 0: yield s

class CGetCmd:
    def __init__(self, prefix=None):
        self.prefix = prefix

    def __call__(self, arg, *args):
        p = [__cget_exe__, arg]
        if self.prefix is not None: p.append('--prefix {}'.format(self.prefix))
        return ' '.join(p+list(remove_empty_elements(args)))

def cget_cmd(*args):
    return CGetCmd()(*args)

def test_install(url, lib=None, alias=None, init=None, remove='remove', list_='list', size=1, prefix=None):
    cg = CGetCmd(prefix=prefix)
    yield cg('init', init)
    yield cg(list_)
    yield cg('clean', '-y')
    yield cg('init', init)
    yield cg(list_)
    yield cg('size', '0')
    yield cg('install', '--verbose --test', url)
    yield cg('size', str(size))
    yield cg(list_)
    if __has_pkg_config__ and lib is not None:
        yield cg('pkg-config', '--list-all')
        yield cg('pkg-config', '--exists', lib)
        yield cg('pkg-config', '--cflags --libs', lib)
    if alias is None: yield cg(remove, '--verbose -y', url)
    else: yield cg(remove, '--verbose -y', alias)
    yield cg('size', '0')
    yield cg(list_)
    yield cg('install', '--verbose --test', url)
    yield cg(list_)
    yield cg('size', str(size))
    yield cg('clean', '-y')
    yield cg(list_)
    yield cg('size', '0')

def test_build(url=None, init=None, size=0, defines=None, prefix=None):
    cg = CGetCmd(prefix=prefix)
    yield cg('init', init)
    yield cg('size', '0')
    yield cg('build', '--verbose -C -y', url)
    yield cg('size', '0')
    yield cg('build', '--verbose --test', defines, url)
    yield cg('size', str(size))
    yield cg('build', '--verbose --test', defines, url)
    yield cg('size', str(size))
    yield cg('build', '--verbose --path', url)
    yield cg('build', '--verbose --test -C -y', defines, url)
    yield cg('size', str(size))
    yield cg('build', '--verbose --test', defines, url)
    yield cg('size', str(size))

@test
def test_tar(d):
    ar = d.get_path('libsimple.tar.gz')
    create_ar(archive=ar, src=get_path('libsimple'))
    d.cmds(test_install(url=ar, lib='simple'))

@test
def test_tar_alias(d):
    ar = d.get_path('libsimple.tar.gz')
    create_ar(archive=ar, src=get_path('libsimple'))
    d.cmds(test_install(url='simple:'+ar, lib='simple', alias='simple'))

@test
def test_dir(d):
    d.cmds(test_install(url=get_path('libsimple'), lib='simple'))

@test
def test_prefix(d):
    d.cmds(test_install(url=get_path('libsimple'), lib='simple', prefix=d.get_path('usr')))

@test
def test_rm(d):
    d.cmds(test_install(url=get_path('libsimple'), lib='simple', remove='rm'))

@test
def test_ls(d):
    d.cmds(test_install(url=get_path('libsimple'), lib='simple', list_='ls'))

@test
def test_update(d):
    d.cmds([
        cget_cmd('install', '--verbose --test', 'app:'+get_path('simpleapp')),
        cget_cmd('size', '1'),
        cget_cmd('install', '--verbose --test --update', 'app:'+get_path('simpleapp')),
        cget_cmd('size', '1'),
        cget_cmd('rm', '--verbose -y', 'app'),
        cget_cmd('size', '0')
    ])

@test
def test_update_reqs(d):
    d.cmds([
        cget_cmd('install', '--verbose --test', 'app:'+get_path('simpleapp')),
        cget_cmd('size', '1'),
        cget_cmd('install', '--verbose --test --update', 'app:'+get_path('basicapp')),
        cget_cmd('size', '2'),
        cget_cmd('rm', '--verbose -y', 'app'),
        cget_cmd('size', '1')
    ])

@test
def test_build_dir(d):
    d.cmds(test_build(get_path('libsimple')))

@test
def test_build_current_dir(d):
    cwd = get_path('libsimple')
    d.cmds(test_build(prefix=d.get_path('cget')), cwd=cwd)

@test
def test_dir_alias(d):
    d.cmds(test_install(url='simple:'+get_path('libsimple'), lib='simple', alias='simple'))

@test
def test_init_cpp11(d):
    d.cmds([
        cget_cmd('init', '--std=c++0x'),
        cget_cmd('install', '--verbose --test', get_path('libsimple11'))
    ])

@test
def test_reqs_alias_file(d):
    reqs_file = d.write_to('reqs', [shlex_quote('simple:'+get_path('libsimple'))])
    d.cmds(test_install(url='--file {}'.format(reqs_file), lib='simple', alias='simple'))

@test
def test_reqs_file(d):
    reqs_file = d.write_to('reqs', [shlex_quote(get_path('libsimple'))])
    d.cmds(test_install(url='--file {}'.format(reqs_file), lib='simple', alias=get_path('libsimple')))

@test
def test_reqs_alias_f(d):
    reqs_file = d.write_to('reqs', [shlex_quote('simple:'+get_path('libsimple'))])
    d.cmds(test_install(url='-f {}'.format(reqs_file), lib='simple', alias='simple'))

@test
def test_reqs_f(d):
    reqs_file = d.write_to('reqs', [shlex_quote(get_path('libsimple'))])
    d.cmds(test_install(url='-f {}'.format(reqs_file), lib='simple', alias=get_path('libsimple')))

@test
def test_app_include_dir(d):
    d.cmds(test_install(url=get_path('basicapp-include'), lib='simple', alias='simple', size=2))

# Basic app needs pkg-config
if __has_pkg_config__:
    @test
    def test_app_dir(d):
        d.cmds(test_install(url=get_path('basicapp'), lib='simple', alias='simple', size=2))

    @test
    def test_build_app_dir(d):
        d.cmds(test_build(get_path('basicapp'), size=1))

@test
def test_install_simple_app_test_with_test(d):
    d.cmds([
        cget_cmd('install', '--verbose --test', get_path('simpleapptest')),
        cget_cmd('list'),
        cget_cmd('size', '2'),
        cget_cmd('remove', '-y simple'),
        cget_cmd('list'),
        cget_cmd('size', '1')
    ])

@test
def test_install_simple_app_test_with_test_all(d):
    d.cmds([
        cget_cmd('install', '--verbose --test-all', get_path('simpleapptest')),
        cget_cmd('list'),
        cget_cmd('size', '2'),
        cget_cmd('remove', '-y simple'),
        cget_cmd('list'),
        cget_cmd('size', '1')
    ])

@test
def test_install_simple_app_test_all_with_test_with_all(d):
    d.cmds([
        cget_cmd('install', '--verbose --test-all', get_path('simpleapptestall')),
        cget_cmd('list'),
        cget_cmd('size', '3'),
        cget_cmd('remove', '-y simple'),
        cget_cmd('list'),
        cget_cmd('size', '2')
    ])

@test
def test_install_simple_app_test_all_with_test(d):
    d.cmds([
        cget_cmd('install', '--verbose --test', get_path('simpleapptestall')),
        cget_cmd('list'),
        cget_cmd('size', '2'),
        cget_cmd('remove', '-y simpleapptest'),
        cget_cmd('list'),
        cget_cmd('size', '1')
    ])

@test
def test_install_simple_app_test_all_without_test(d):
    d.cmds([
        cget_cmd('install', '--verbose', get_path('simpleapptestall')),
        cget_cmd('list'),
        cget_cmd('size', '1'),
        cget_cmd('remove', '-y', get_path('simpleapptestall')),
        cget_cmd('list'),
        cget_cmd('size', '0')
    ])

@test
def test_install_simple_app_test_without_test(d):
    d.cmds([
        cget_cmd('install', '--verbose', get_path('simpleapptest')),
        cget_cmd('list'),
        cget_cmd('size', '1')
    ])

@test
def test_build_simple_app_test_with_test(d):
    d.cmds(test_build(get_path('simpleapptest'), size=1))

@test
def test_build_simple_app_test_without_test(d):
    d.cmds([
        cget_cmd('build', '--verbose', get_path('simpleapptest')),
        cget_cmd('size', '0')
    ])

@test
def test_install_simple_basic_app_test_with_test_all(d):
    d.cmds([
        cget_cmd('install', '--verbose --test-all', get_path('simplebasicapptest')),
        cget_cmd('list'),
        cget_cmd('size', '3'),
        cget_cmd('remove', '-y simple'),
        cget_cmd('list'),
        cget_cmd('size', '1')
    ])

@test
def test_install_simple_basic_app_test_with_test(d):
    d.cmds([
        cget_cmd('install', '--verbose --test', get_path('simplebasicapptest')),
        cget_cmd('list'),
        cget_cmd('size', '3'),
        cget_cmd('remove', '-y simple'),
        cget_cmd('list'),
        cget_cmd('size', '1')
    ])

@test
def test_install_simple_basic_app_test_without_test(d):
    d.cmds([
        cget_cmd('install', '--verbose ', get_path('simplebasicapptest')),
        cget_cmd('list'),
        cget_cmd('size', '1'),
        cget_cmd('remove', '-y', get_path('simplebasicapptest')),
        cget_cmd('list'),
        cget_cmd('size', '0')
    ])


@test
def test_install_simple_basic_app2_test_with_test_all(d):
    d.cmds([
        cget_cmd('install', '--verbose --test-all', get_path('simplebasicapp')),
        cget_cmd('list'),
        cget_cmd('size', '4'),
        cget_cmd('remove', '-y simple'),
        cget_cmd('list'),
        cget_cmd('size', '2')
    ])

@test
def test_install_simple_basic_app2_test_with_test(d):
    d.cmds([
        cget_cmd('install', '--verbose --test', get_path('simplebasicapp')),
        cget_cmd('list'),
        cget_cmd('size', '2'),
        cget_cmd('remove', '-y simplebasicapptest'),
        cget_cmd('list'),
        cget_cmd('size', '1')
    ])

@test
def test_install_simple_basic_app2_test_without_test(d):
    d.cmds([
        cget_cmd('install', '--verbose ', get_path('simplebasicapp')),
        cget_cmd('list'),
        cget_cmd('size', '1'),
        cget_cmd('remove', '-y', get_path('simplebasicapp')),
        cget_cmd('list'),
        cget_cmd('size', '0')
    ])

@test
def test_flags_fail(d):
    should_fail(lambda: d.cmds([cget_cmd('install', '--verbose --test -DCGET_FLAG=Off', get_path('libsimpleflag'))]))

@test
def test_flags(d):
    p = get_path('libsimpleflag')
    d.cmds(test_install(url='-DCGET_FLAG=On {}'.format(p), alias=p))

@test
def test_flags_init(d):
    d.cmds(test_install(init='-DCGET_FLAG=On', url=get_path('libsimpleflag')))

@test
def test_build_flags(d):
    d.cmds(test_build(get_path('libsimpleflag'), defines='-DCGET_FLAG=On'))

@test
def test_build_flags_init(d):
    d.cmds(test_build(init='-DCGET_FLAG=On', url=get_path('libsimpleflag')))

@test
def test_flags_init_integer(d):
    d.cmds(test_install(init='-DCGET_FLAG=1', url=get_path('libsimpleflag')))

@test
def test_flags_fail_integer(d):
    should_fail(lambda: d.cmds([cget_cmd('install --verbose --test -DCGET_FLAG=0', get_path('libsimpleflag'))]))

@test
def test_flags_integer(d):
    p = get_path('libsimpleflag')
    d.cmds(test_install(url='-DCGET_FLAG=1 {}'.format(p), alias=p))

@test
def test_flags_fail_define(d):
    should_fail(lambda: d.cmds([cget_cmd('install', '--verbose --test --define CGET_FLAG=Off', get_path('libsimpleflag'))]))

@test
def test_flags_define(d):
    d.cmds([cget_cmd('install', '--verbose --test --define CGET_FLAG=On', get_path('libsimpleflag'))])

@test
def test_flags_toolchain(d):
    d.cmds([
        cget_cmd('init', '--toolchain', get_toolchain('toolchainflag.cmake')),
        cget_cmd('install', '--verbose --test', get_path('libsimpleflag'))
    ])

@test
def test_flags_toolchain_prefix(d):
    cg = CGetCmd(d.get_path('usr'))
    d.cmds([
        cg('init', '--toolchain', get_toolchain('toolchainflag.cmake')),
        cg('install', '--verbose --test', get_path('libsimpleflag'))
    ])

@test
def test_flags_reqs_f(d):
    p = get_path('libsimpleflag')
    reqs_file = d.write_to('reqs', [shlex_quote(p) + ' -DCGET_FLAG=On'])
    d.cmds(test_install(url='-f {}'.format(reqs_file), alias=p))

@test
def test_comments_reqs_f(d):
    p = get_path('libsimple')
    reqs_file = d.write_to('reqs', [shlex_quote(p) + ' #A comment', '# Another comment'])
    d.cmds(test_install(url='-f {}'.format(reqs_file), alias=p))


if __name__ == '__main__': run_tests()
