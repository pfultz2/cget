import pytest

import os, tarfile, cget.util

from six.moves import shlex_quote

__test_dir__ = os.path.dirname(os.path.realpath(__file__))

__cget_exe__ = cget.util.which('cget')

__has_pkg_config__ = cget.util.can(lambda: cget.util.which('pkg-config'))

def get_path(*ps):
    return os.path.join(__test_dir__, *ps)

def get_exists_path(*ps):
    result = get_path(*ps)
    assert os.path.exists(result)
    return result

def get_toolchain(*ps):
    return get_exists_path('toolchains', *ps)

def basename(p):
    d, b = os.path.split(p)
    if len(b) > 0: return b
    else: return basename(d)

def create_ar(archive, src):
    with tarfile.open(archive, mode='w:gz') as f:
        name = basename(src)
        f.add(src, arcname=name)

class DirForTests:
    def __init__(self, tmp_dir):
        self.tmp_dir = tmp_dir

    def dir(self, *args):
        return DirForTests(os.path.join(self.tmp_dir, *args))

    def mkdir(self, *args):
        p = os.path.join(self.tmp_dir, *args)
        cget.util.mkdir(p)
        return DirForTests(p)

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

    def get_path(self, *ps):
        return os.path.join(self.tmp_dir, *ps)

@pytest.fixture
def d(tmpdir):
    return DirForTests(tmpdir.strpath)

def remove_empty_elements(xs):
    for x in xs:
        if x is not None:
            s = str(x)
            if len(s) > 0: yield s

class CGetCmd:
    def __init__(self, prefix=None, build_path=None):
        self.prefix = prefix
        self.build_path = build_path

    def __call__(self, *args):
        p = [__cget_exe__]
        if self.prefix is not None: p.append('--prefix {}'.format(self.prefix))
        if self.build_path is not None: p.append('--build-path {}'.format(self.build_path))
        return ' '.join(p+list(remove_empty_elements(args)))

def cget_cmd(*args):
    return CGetCmd()(*args)

def install_cmds(url, lib=None, alias=None, init=None, remove='remove', list_='list', size=1, recipes=None, prefix=None, build_path=None, variants=None):
    cg = CGetCmd(prefix=prefix, build_path=build_path)
    base_size = 0
    if recipes: base_size = 1
    n = str(size + base_size)
    yield cg('init', init)
    for variant in variants or ['--debug', '--release', '']:
        yield cg(list_)
        yield cg('clean', '-y')
        yield cg('init', init)
        yield cg(list_)
        yield cg('size', '0')
        if recipes: yield cg('install', recipes)
        yield cg('install', '--verbose --test', variant, url)
        yield cg('size', n)
        yield cg(list_)
        if __has_pkg_config__ and lib is not None:
            yield cg('pkg-config', '--list-all')
            yield cg('pkg-config', '--exists', lib)
            yield cg('pkg-config', '--cflags --libs', lib)
        if alias is None: yield cg(remove, '--verbose -y', url)
        else: yield cg(remove, '--verbose -y', alias)
        yield cg('size', str(base_size))
        yield cg(list_)
        yield cg('install', '--verbose --test', variant, url)
        yield cg(list_)
        yield cg('size', n)
        yield cg('clean', '-y')
        yield cg(list_)
        yield cg('size', '0')

def build_cmds(url=None, init=None, size=0, defines=None, prefix=None, build_path=None):
    cg = CGetCmd(prefix=prefix, build_path=build_path)
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

def test_tar(d):
    ar = d.get_path('libsimple.tar.gz')
    create_ar(archive=ar, src=get_exists_path('libsimple'))
    d.cmds(install_cmds(url=ar, lib='simple'))

def test_tar_alias(d):
    ar = d.get_path('libsimple.tar.gz')
    create_ar(archive=ar, src=get_exists_path('libsimple'))
    d.cmds(install_cmds(url='simple,'+ar, lib='simple', alias='simple'))

def test_dir(d):
    d.cmds(install_cmds(url=get_exists_path('libsimple'), lib='simple'))

def test_relative_dir(d):
    p = os.path.relpath(get_exists_path('libsimple'), d.get_path())
    d.cmds(install_cmds(url=p, lib='simple'))

@pytest.mark.xfail(strict=True)
def test_debug_dir_fail(d):
    d.cmds(install_cmds(url=get_exists_path('libsimpledebug'), lib='simple', variants=['--debug']))

def test_debug_dir_pass(d):
    d.cmds(install_cmds(url=get_exists_path('libsimpledebug'), lib='simple', variants=['--release', '']))

if cget.util.USE_SYMLINKS:
    def test_local_dir(d):
        cget.util.copy_to(get_exists_path('libsimple'), d.tmp_dir)
        d.cmds(install_cmds(url='.', lib='simple'), cwd=d.get_path('libsimple'))

def test_dir_custom_build_path(d):
    d.cmds(install_cmds(url=get_exists_path('libsimple'), lib='simple', build_path=d.get_path('my_build')))

def test_recipe_simple(d):
    recipes=get_exists_path('basicrecipes') + ' -DCGET_TEST_DIR="' + __test_dir__ + '"'
    d.cmds(install_cmds(url='simple', lib='simple', recipes=recipes))

def test_recipe_simple_branch(d):
    recipes=get_exists_path('basicrecipes') + ' -DCGET_TEST_DIR="' + __test_dir__ + '"'
    d.cmds(install_cmds(url='simple@master', lib='simple', recipes=recipes))

@pytest.mark.xfail(strict=True)
def test_recipe_simple_branch_fail(d):
    recipes=get_exists_path('basicrecipes') + ' -DCGET_TEST_DIR="' + __test_dir__ + '"'
    d.cmds(install_cmds(url='simple@nonexistent', lib='simple', recipes=recipes))

def test_recipe_simpleflag(d):
    recipes=get_exists_path('basicrecipes') + ' -DCGET_TEST_DIR="' + __test_dir__ + '"'
    d.cmds(install_cmds(url='simpleflag', recipes=recipes))

def test_recipe_simplemultiflag(d):
    recipes=get_exists_path('basicrecipes') + ' -DCGET_TEST_DIR="' + __test_dir__ + '"'
    d.cmds(install_cmds(url='simplemultiflag', recipes=recipes))

def test_recipe_basicapp(d):
    recipes=get_exists_path('basicrecipes') + ' -DCGET_TEST_DIR="' + __test_dir__ + '"'
    d.cmds(install_cmds(url='basicapp', lib='simple', alias='simple', size=2, recipes=recipes))

def test_recipe_basicappnoreq(d):
    recipes=get_exists_path('basicrecipes') + ' -DCGET_TEST_DIR="' + __test_dir__ + '"'
    d.cmds(install_cmds(url='basicappnoreq', lib='simple', alias='simple', size=2, recipes=recipes))

def test_recipe_simple_x(d):
    recipes=get_exists_path('basicrecipes') + ' -DCGET_TEST_DIR="' + __test_dir__ + '"'
    d.cmds(install_cmds(url='simpleheader', recipes=recipes))

def test_symlink_in_prefix(d):
    p = d.get_path('usr')
    if cget.util.USE_SYMLINKS:
        cget.util.mkdir(os.path.join(p, 'share', 'man'))
        os.symlink(os.path.join(p, 'share', 'man'), os.path.join(p, 'man'))
    d.cmds(install_cmds(url=get_exists_path('libsimple'), lib='simple', prefix=p))

def test_prefix(d):
    d.cmds(install_cmds(url=get_exists_path('libsimple'), lib='simple', prefix=d.get_path('usr')))

def test_relative_prefix(d):
    d.cmds(install_cmds(url=get_exists_path('libsimple'), lib='simple', prefix='usr'))

def test_recipe_prefix(d):
    recipes=get_exists_path('basicrecipes') + ' -DCGET_TEST_DIR="' + __test_dir__ + '"'
    d.cmds(install_cmds(url='simple', lib='simple', recipes=recipes, prefix=d.get_path('usr')))

def test_recipe_relative_prefix(d):
    recipes=get_exists_path('basicrecipes') + ' -DCGET_TEST_DIR="' + __test_dir__ + '"'
    d.cmds(install_cmds(url='simple', lib='simple', recipes=recipes, prefix='usr'))

@pytest.mark.xfail(strict=True)
def test_xcmake_fail(d):
    d.cmds(install_cmds(url=get_exists_path('libsimplebare'), lib='simple'))

def test_xcmake(d):
    url = get_exists_path('libsimplebare') + ' --cmake ' + get_exists_path('libsimple', 'CMakeLists.txt')
    d.cmds(install_cmds(url=url, lib='simple', alias=get_exists_path('libsimplebare')))

def test_xcmake_s(d):
    url = get_exists_path('libsimplebare') + ' -X ' + get_exists_path('libsimple', 'CMakeLists.txt')
    d.cmds(install_cmds(url=url, lib='simple', alias=get_exists_path('libsimplebare')))

@pytest.mark.xfail(strict=True)
def test_header_xcmake_fail(d):
    d.cmds(install_cmds(url=get_exists_path('simpleinclude')))

def test_header_xcmake(d):
    url = get_exists_path('simpleinclude') + ' --cmake header'
    d.cmds(install_cmds(url=url, alias=get_exists_path('simpleinclude')))

def test_binary_xcmake(d):
    url = get_exists_path('simpleinclude') + ' --cmake binary'
    d.cmds(install_cmds(url=url, lib='simple', alias=get_exists_path('simpleinclude')))

def test_header_xcmake_dir(d):
    url = get_exists_path('simpleinclude') + ' --cmake ' + get_exists_path('cmake', 'header_cmake_dir.cmake')
    d.cmds(install_cmds(url=url, alias=get_exists_path('simpleinclude')))

def test_xcmake_ref_original(d):
    url = get_exists_path('libsimple') + ' --cmake ' + get_exists_path('cmake', 'use_original_cmake.cmake')
    d.cmds(install_cmds(url=url, lib='simple', alias=get_exists_path('libsimple')))

@pytest.mark.xfail(strict=True)
def test_xcmake_ref_original_fail(d):
    url = get_exists_path('libsimplebare') + ' --cmake ' + get_exists_path('cmake', 'use_original_cmake.cmake')
    d.cmds(install_cmds(url=url, lib='simple', alias=get_exists_path('libsimplebare')))

def test_rm(d):
    d.cmds(install_cmds(url=get_exists_path('libsimple'), lib='simple', remove='rm'))


def test_ls(d):
    d.cmds(install_cmds(url=get_exists_path('libsimple'), lib='simple', list_='ls'))

def test_update(d):
    d.cmds([
        cget_cmd('install', '--verbose --test', 'app,'+get_exists_path('simpleapp')),
        cget_cmd('size', '1'),
        cget_cmd('install', '--verbose --test --update', 'app,'+get_exists_path('simpleapp')),
        cget_cmd('size', '1'),
        cget_cmd('rm', '--verbose -y', 'app'),
        cget_cmd('size', '0')
    ])

def test_update_reqs(d):
    d.cmds([
        cget_cmd('install', '--verbose --test', 'app,'+get_exists_path('simpleapp')),
        cget_cmd('size', '1'),
        cget_cmd('install', '--verbose --test --update', 'app,'+get_exists_path('basicapp')),
        cget_cmd('size', '2'),
        cget_cmd('rm', '--verbose -y', 'app'),
        cget_cmd('size', '1')
    ])

def test_rm_with_symlink(d):
    p = d.get_path('usr')
    share = os.path.join(p, 'share')
    cget.util.mkfile(share, 'data.txt', 'data')
    if cget.util.USE_SYMLINKS:
        os.symlink(os.path.join(share, 'data.txt'), os.path.join(share, 'data.sym'))
    else:
        cget.util.mkfile(share, 'data.sym', 'data')
    os.remove(os.path.join(share, 'data.txt'))
    cg = CGetCmd(prefix=p)
    d.cmds([
        cg('install', '--verbose --test', 'simple,'+get_exists_path('libsimple')),
        cg('size', '1'),
        cg('rm', '--verbose -y', 'simple'),
        cg('size', '0')
    ])
    assert os.path.exists(os.path.join(share))
    assert not os.path.exists(os.path.join(share, 'data.txt'))
    assert os.path.lexists(os.path.join(share, 'data.sym'))

def test_rm_all(d):
    d.cmds([
        cget_cmd('install', '--verbose --test --update', 'app,'+get_exists_path('basicapp')),
        cget_cmd('size', '2'),
        cget_cmd('rm', '--verbose -y --all'),
        cget_cmd('size', '0')
    ])

def test_unlink1(d):
    d.cmds([
        cget_cmd('install', '--verbose --test', 'simple,'+get_exists_path('libsimple')),
        cget_cmd('size', '1'),
        cget_cmd('rm', '--verbose -y --unlink', 'simple'),
        cget_cmd('size', '0'),
        cget_cmd('install', '--verbose --test', 'app,'+get_exists_path('basicapp')),
        cget_cmd('size', '2'),
        cget_cmd('rm', '--verbose -y', 'app'),
        cget_cmd('size', '1'),
        cget_cmd('install', '--verbose --test', 'app,'+get_exists_path('basicapp')),
        cget_cmd('size', '2')
    ])

def test_unlink2(d):
    d.cmds([
        cget_cmd('install', '--verbose --test', 'app,'+get_exists_path('basicapp')),
        cget_cmd('size', '2'),
        cget_cmd('rm', '--verbose -y --unlink', 'simple'),
        cget_cmd('size', '0'),
        cget_cmd('install', '--verbose --test', 'app,'+get_exists_path('basicapp')),
        cget_cmd('size', '2'),
        cget_cmd('rm', '--verbose -y', 'app'),
        cget_cmd('size', '1'),
        cget_cmd('install', '--verbose --test', 'app,'+get_exists_path('basicapp')),
        cget_cmd('size', '2')
    ])

def test_unlink3(d):
    d.cmds([
        cget_cmd('install', '--verbose --test', 'app,'+get_exists_path('basicapp')),
        cget_cmd('size', '2'),
        cget_cmd('rm', '--verbose -y --unlink', 'app'),
        cget_cmd('size', '1'),
        cget_cmd('install', '--verbose --test', 'app,'+get_exists_path('basicapp')),
        cget_cmd('size', '2'),
        cget_cmd('rm', '--verbose -y', 'app'),
        cget_cmd('size', '1'),
        cget_cmd('install', '--verbose --test', 'app,'+get_exists_path('basicapp')),
        cget_cmd('size', '2')
    ])

def test_unlink4(d):
    d.cmds([
        cget_cmd('install', '--verbose --test', 'simple,'+get_exists_path('libsimple')),
        cget_cmd('size', '1'),
        cget_cmd('rm', '--verbose -y --unlink', 'simple'),
        cget_cmd('size', '0'),
        cget_cmd('install', '--verbose --test', 'app,'+get_exists_path('basicapp')),
        cget_cmd('size', '2'),
        cget_cmd('rm', '--verbose -y', 'simple'),
        cget_cmd('size', '0'),
        cget_cmd('install', '--verbose --test', 'app,'+get_exists_path('basicapp')),
        cget_cmd('size', '2')
    ])

def test_unlink_update(d):
    d.cmds([
        cget_cmd('install', '--verbose --test', 'app,'+get_exists_path('simpleapp')),
        cget_cmd('size', '1'),
        cget_cmd('rm', '--verbose -y --unlink', 'app'),
        cget_cmd('install', '--verbose --test --update', 'app,'+get_exists_path('basicapp')),
        cget_cmd('size', '2'),
        cget_cmd('rm', '--verbose -y', 'app'),
        cget_cmd('size', '1')
    ])

def test_build_dir(d):
    d.cmds(build_cmds(get_exists_path('libsimple')))

def test_build_relative_dir(d):
    p = os.path.relpath(get_exists_path('libsimple'), d.get_path())
    d.cmds(build_cmds(p))

def test_build_dir_custom_build_path(d):
    d.cmds(build_cmds(get_exists_path('libsimple'), build_path=d.get_path('my_build')))

def test_build_dir_custom_build_path2(d):
    d.cmds(build_cmds(get_exists_path('basicapp'), build_path=d.get_path('my_build'), size=1))

def test_build_relative_dir_custom_build_path(d):
    p = os.path.relpath(get_exists_path('libsimple'), d.get_path())
    d.cmds(build_cmds(p, build_path=d.get_path('my_build')))

def test_build_relative_dir_custom_build_path2(d):
    p = os.path.relpath(get_exists_path('basicapp'), d.get_path())
    d.cmds(build_cmds(p, build_path=d.get_path('my_build'), size=1))

def test_tmp_build_dir_custom_build_path(d):
    d.mkdir('tmp').cmds(build_cmds(get_exists_path('libsimple'), build_path=d.get_path('my_build')))

def test_tmp_build_dir_custom_build_path2(d):
    d.mkdir('tmp').cmds(build_cmds(get_exists_path('basicapp'), build_path=d.get_path('my_build'), size=1))

def test_tmp_relative_build_dir_custom_build_path(d):
    p = os.path.relpath(get_exists_path('libsimple'), d.get_path('tmp'))
    d.mkdir('tmp').cmds(build_cmds(p, build_path=d.get_path('my_build')))

def test_tmp_relative_build_dir_custom_build_path2(d):
    p = os.path.relpath(get_exists_path('basicapp'), d.get_path('tmp'))
    d.mkdir('tmp').cmds(build_cmds(p, build_path=d.get_path('my_build'), size=1))

def test_build_current_dir(d):
    cwd = get_exists_path('libsimple')
    d.cmds(build_cmds(prefix=d.get_path('cget')), cwd=cwd)

def test_build_target(d):
    d.cmds([
        cget_cmd('build', '--verbose', '--target simpleapp', get_exists_path('simpleapp')),
        cget_cmd('build', '--verbose', '--target simpleapptest', get_exists_path('simpleapp')),
        cget_cmd('size', '0')
    ])


@pytest.mark.xfail(strict=True)
def test_build_target_fail(d):
    d.cmds([cget_cmd('build', '--verbose', '--target xyz', get_exists_path('simpleapp'))])

def test_dir_deprecated_alias(d):
    d.cmds(install_cmds(url='simple,'+get_exists_path('libsimple'), lib='simple', alias='simple'))

def test_dir_alias(d):
    d.cmds(install_cmds(url='simple,'+get_exists_path('libsimple'), lib='simple', alias='simple'))

def test_init_cpp11(d):
    d.cmds([
        cget_cmd('init', '--std=c++0x'),
        cget_cmd('install', '--verbose --test', get_exists_path('libsimple11'))
    ])

def test_reqs_alias_file(d):
    reqs_file = d.write_to('reqs', [shlex_quote('simple,'+get_exists_path('libsimple'))])
    d.cmds(install_cmds(url='--file {}'.format(reqs_file), lib='simple', alias='simple'))

def test_reqs_file(d):
    reqs_file = d.write_to('reqs', [shlex_quote(get_exists_path('libsimple'))])
    d.cmds(install_cmds(url='--file {}'.format(reqs_file), lib='simple', alias=get_exists_path('libsimple')))

def test_reqs_alias_f(d):
    reqs_file = d.write_to('reqs', [shlex_quote('simple,'+get_exists_path('libsimple'))])
    d.cmds(install_cmds(url='-f {}'.format(reqs_file), lib='simple', alias='simple'))

def test_reqs_f(d):
    reqs_file = d.write_to('reqs', [shlex_quote(get_exists_path('libsimple'))])
    d.cmds(install_cmds(url='-f {}'.format(reqs_file), lib='simple', alias=get_exists_path('libsimple')))

def test_reqs_f2(d):
    reqs_file = get_exists_path('basicapp', 'requirements.txt')
    d.cmds(install_cmds(url='-f {}'.format(reqs_file), lib='simple', alias='simple'))

def test_reqs_hash(d):
    ar = d.get_path('libsimple.tar.gz')
    create_ar(archive=ar, src=get_exists_path('libsimple'))
    h = cget.util.hash_file(ar, 'sha1')
    reqs_file = d.write_to('reqs', ["{0} --hash=sha1:{1}".format(shlex_quote(ar), h)])
    d.cmds(install_cmds(url='--file {}'.format(reqs_file), lib='simple', alias=ar))

@pytest.mark.xfail(strict=True)
def test_reqs_hash_fail(d):
    ar = d.get_path('libsimple.tar.gz')
    create_ar(archive=ar, src=get_exists_path('libsimple'))
    h = 'xxx'
    reqs_file = d.write_to('reqs', ["{0} --hash=sha1:{1}".format(shlex_quote(ar), h)])
    d.cmds(install_cmds(url='--file {}'.format(reqs_file), lib='simple', alias=ar))

def test_app_include_dir(d):
    d.cmds(install_cmds(url=get_exists_path('basicapp-include'), lib='simple', alias='simple', size=2))

def test_app_header_dep(d):
    d.cmds(install_cmds(url=get_exists_path('basicapp-simpleinclude'), alias='simple', size=2))

# Basic app needs pkg-config
if __has_pkg_config__:

    def test_app_dir(d):
        d.cmds(install_cmds(url=get_exists_path('basicapp'), lib='simple', alias='simple', size=2))

    def test_xapp_dir(d):
        d.cmds(install_cmds(url=get_exists_path('basicappx'), lib='simple', alias='simple', size=2))

    def test_appdebug_dir_pass(d):
        d.cmds(install_cmds(url=get_exists_path('basicappdebug'), lib='simple', alias='simple', size=2, variants=['--release', '']))

    @pytest.mark.xfail(strict=True)
    def test_appdebug_dir_fail(d):
        d.cmds(install_cmds(url=get_exists_path('basicappdebug'), lib='simple', alias='simple', size=2, variants=['--debug']))

    def test_build_flag_child(d):
        d.cmds([
            cget_cmd('install', '--verbose', get_exists_path('basicappbuild')),
            cget_cmd('list'),
            cget_cmd('size', '2'),
            cget_cmd('remove', '-y simple'),
            cget_cmd('list'),
            cget_cmd('size', '1')
        ])

    def test_build_flag_parent(d):
        d.cmds([
            cget_cmd('install', '--verbose', get_exists_path('basicappbuild')),
            cget_cmd('list'),
            cget_cmd('size', '2'),
            cget_cmd('remove', '-y', get_exists_path('basicappbuild')),
            cget_cmd('list'),
            cget_cmd('size', '1')
        ])


    def test_build_app_dir(d):
        d.cmds(build_cmds(get_exists_path('basicapp'), size=1))

def test_install_simple_app_test_with_test(d):
    d.cmds([
        cget_cmd('install', '--verbose --test', get_exists_path('simpleapptest')),
        cget_cmd('list'),
        cget_cmd('size', '2'),
        cget_cmd('remove', '-y simple'),
        cget_cmd('list'),
        cget_cmd('size', '1')
    ])

def test_install_simple_app_test_with_test_all(d):
    d.cmds([
        cget_cmd('install', '--verbose --test-all', get_exists_path('simpleapptest')),
        cget_cmd('list'),
        cget_cmd('size', '2'),
        cget_cmd('remove', '-y simple'),
        cget_cmd('list'),
        cget_cmd('size', '1')
    ])

def test_install_simple_app_test_all_with_test_with_all(d):
    d.cmds([
        cget_cmd('install', '--verbose --test-all', get_exists_path('simpleapptestall')),
        cget_cmd('list'),
        cget_cmd('size', '3'),
        cget_cmd('remove', '-y simple'),
        cget_cmd('list'),
        cget_cmd('size', '2')
    ])

def test_install_simple_app_test_all_with_test(d):
    d.cmds([
        cget_cmd('install', '--verbose --test', get_exists_path('simpleapptestall')),
        cget_cmd('list'),
        cget_cmd('size', '2'),
        cget_cmd('remove', '-y simpleapptest'),
        cget_cmd('list'),
        cget_cmd('size', '1')
    ])

def test_install_simple_app_test_all_without_test(d):
    d.cmds([
        cget_cmd('install', '--verbose', get_exists_path('simpleapptestall')),
        cget_cmd('list'),
        cget_cmd('size', '1'),
        cget_cmd('remove', '-y', get_exists_path('simpleapptestall')),
        cget_cmd('list'),
        cget_cmd('size', '0')
    ])

def test_install_simple_app_test_without_test(d):
    d.cmds([
        cget_cmd('install', '--verbose', get_exists_path('simpleapptest')),
        cget_cmd('list'),
        cget_cmd('size', '1')
    ])

def test_build_simple_app_test_with_test(d):
    d.cmds(build_cmds(get_exists_path('simpleapptest'), size=1))

def test_build_simple_app_test_without_test(d):
    d.cmds([
        cget_cmd('build', '--verbose', get_exists_path('simpleapptest')),
        cget_cmd('size', '0')
    ])

def test_install_simple_basic_app_test_with_test_all(d):
    d.cmds([
        cget_cmd('install', '--verbose --test-all', get_exists_path('simplebasicapptest')),
        cget_cmd('list'),
        cget_cmd('size', '3'),
        cget_cmd('remove', '-y simple'),
        cget_cmd('list'),
        cget_cmd('size', '1')
    ])

def test_install_simple_basic_app_test_with_test(d):
    d.cmds([
        cget_cmd('install', '--verbose --test', get_exists_path('simplebasicapptest')),
        cget_cmd('list'),
        cget_cmd('size', '3'),
        cget_cmd('remove', '-y simple'),
        cget_cmd('list'),
        cget_cmd('size', '1')
    ])

def test_install_simple_basic_app_test_without_test(d):
    d.cmds([
        cget_cmd('install', '--verbose ', get_exists_path('simplebasicapptest')),
        cget_cmd('list'),
        cget_cmd('size', '1'),
        cget_cmd('remove', '-y', get_exists_path('simplebasicapptest')),
        cget_cmd('list'),
        cget_cmd('size', '0')
    ])


def test_install_simple_basic_app2_test_with_test_all(d):
    d.cmds([
        cget_cmd('install', '--verbose --test-all', get_exists_path('simplebasicapp')),
        cget_cmd('list'),
        cget_cmd('size', '4'),
        cget_cmd('remove', '-y simple'),
        cget_cmd('list'),
        cget_cmd('size', '2')
    ])

def test_install_simple_basic_app2_test_with_test(d):
    d.cmds([
        cget_cmd('install', '--verbose --test', get_exists_path('simplebasicapp')),
        cget_cmd('list'),
        cget_cmd('size', '2'),
        cget_cmd('remove', '-y simplebasicapptest'),
        cget_cmd('list'),
        cget_cmd('size', '1')
    ])

def test_install_simple_basic_app2_test_without_test(d):
    d.cmds([
        cget_cmd('install', '--verbose ', get_exists_path('simplebasicapp')),
        cget_cmd('list'),
        cget_cmd('size', '1'),
        cget_cmd('remove', '-y', get_exists_path('simplebasicapp')),
        cget_cmd('list'),
        cget_cmd('size', '0')
    ])

@pytest.mark.xfail(strict=True)
def test_flags_fail(d):
    d.cmds([cget_cmd('install', '--verbose --test -DCGET_FLAG=Off', get_path('libsimpleflag'))])

def test_flags(d):
    p = get_exists_path('libsimpleflag')
    d.cmds(install_cmds(url='-DCGET_FLAG=On {}'.format(p), alias=p))

def test_flags_init(d):
    d.cmds(install_cmds(init='-DCGET_FLAG=On', url=get_exists_path('libsimpleflag')))

def test_build_flags(d):
    d.cmds(build_cmds(get_exists_path('libsimpleflag'), defines='-DCGET_FLAG=On'))

def test_build_flags_init(d):
    d.cmds(build_cmds(init='-DCGET_FLAG=On', url=get_exists_path('libsimpleflag')))

def test_flags_init_integer(d):
    d.cmds(install_cmds(init='-DCGET_FLAG=1', url=get_exists_path('libsimpleflag')))

@pytest.mark.xfail(strict=True)
def test_flags_fail_integer(d):
    d.cmds([cget_cmd('install --verbose --test -DCGET_FLAG=0', get_path('libsimpleflag'))])

def test_flags_integer(d):
    p = get_exists_path('libsimpleflag')
    d.cmds(install_cmds(url='-DCGET_FLAG=1 {}'.format(p), alias=p))

@pytest.mark.xfail(strict=True)
def test_flags_fail_define(d):
    d.cmds([cget_cmd('install', '--verbose --test --define CGET_FLAG=Off', get_path('libsimpleflag'))])

def test_flags_define(d):
    d.cmds([cget_cmd('install', '--verbose --test --define CGET_FLAG=On', get_exists_path('libsimpleflag'))])

def test_flags_toolchain(d):
    d.cmds([
        cget_cmd('init', '--toolchain', get_toolchain('toolchainflag.cmake')),
        cget_cmd('install', '--verbose --test', get_exists_path('libsimpleflag'))
    ])

def test_flags_toolchain_prefix(d):
    cg = CGetCmd(d.get_path('usr'))
    d.cmds([
        cg('init', '--toolchain', get_toolchain('toolchainflag.cmake')),
        cg('install', '--verbose --test', get_exists_path('libsimpleflag'))
    ])

def test_flags_reqs_f(d):
    p = get_exists_path('libsimpleflag')
    reqs_file = d.write_to('reqs', [shlex_quote(p) + ' -DCGET_FLAG=On'])
    d.cmds(install_cmds(url='-f {}'.format(reqs_file), alias=p))

def test_multiflags(d):
    p = get_exists_path('libsimplemultiflag')
    d.cmds(install_cmds(url='-DCGET_FLAG1=On -DCGET_FLAG2=On {}'.format(p), alias=p))

@pytest.mark.xfail(strict=True)
def test_multiflags_fail1(d):
    d.cmds([cget_cmd('install', '--verbose --test -DCGET_FLAG1=Off -DCGET_FLAG2=Off', get_path('libsimplemultiflag'))])

@pytest.mark.xfail(strict=True)
def test_multiflags_fail2(d):
    d.cmds([cget_cmd('install', '--verbose --test -DCGET_FLAG1=Off -DCGET_FLAG2=On', get_path('libsimplemultiflag'))])

@pytest.mark.xfail(strict=True)
def test_multiflags_fail3(d):
    d.cmds([cget_cmd('install', '--verbose --test -DCGET_FLAG1=On', get_path('libsimplemultiflag'))])

def test_comments_reqs_f(d):
    p = get_exists_path('libsimple')
    reqs_file = d.write_to('reqs', [shlex_quote(p) + ' #A comment', '# Another comment'])
    d.cmds(install_cmds(url='-f {}'.format(reqs_file), alias=p))

def test_shared_init(d):
    d.cmds(install_cmds(init='--shared', url=get_exists_path('libsimple'), lib='simple'))

def test_static_init(d):
    d.cmds(install_cmds(init='--static', url=get_exists_path('libsimple'), lib='simple'))

@pytest.mark.xfail(strict=True)
def test_shared_static_init(d):
    d.cmds(install_cmds(init='--shared --static', url=get_exists_path('libsimple'), lib='simple'))
