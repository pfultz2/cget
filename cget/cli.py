import click, os, shutil, base64, multiprocessing

from cget import __version__
import cget.util as util

class Builder:
    def __init__(self, prefix, tmp_dir, verbose=False):
        self.prefix = prefix
        self.tmp_dir = tmp_dir
        self.build_dir = os.path.join(tmp_dir, 'build')
        self.is_make_generator = False
        self.verbose = verbose
    def __enter__(self):
        util.mkdir(self.tmp_dir)
        return self
    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.tmp_dir)

    def log(self, *args):
        if self.verbose: click.secho(' '.join([str(arg) for arg in args]), bold=True)

    def pkg_config_env(self):
        return {'PKG_CONFIG_PATH': self.prefix.pkg_config_path() }

    def cmake(self, args, cwd=None, toolchain=None):
        self.log("cmake: ", args)
        return util.cmake(args, cwd=cwd, toolchain=toolchain, env=self.pkg_config_env())

    def fetch(self, url):
        self.log("fetch:", url)
        util.extract_ar(util.retrieve_url(url, self.tmp_dir), self.tmp_dir)
        return next(util.get_dirs(self.tmp_dir))

    def configure(self, src_dir, install_prefix=None):
        util.mkdir(self.build_dir)
        args = [src_dir]
        if install_prefix is not None: args.insert(0, '-DCMAKE_INSTALL_PREFIX=' + install_prefix)
        result = self.cmake(args, cwd=self.build_dir, toolchain=self.prefix.toolchain)
        if os.path.exists(os.path.join(self.build_dir, 'Makefile')): self.is_make_generator = True
        return result

    def build(self, target=None, config=None, cwd=None, toolchain=None):
        args = ['--build', self.build_dir]
        if config is not None: args.extend(['--config', config])
        if target is not None: args.extend(['--target', target])
        if self.is_make_generator: args.extend(['--', '-j', str(multiprocessing.cpu_count())])
        return self.cmake(args, cwd=cwd, toolchain=toolchain)

def quote(s):
    return s.replace("\\", "\\\\")

def url_to_pkg(url):
    x = url[url.find('://')+3:]
    return '_url_' + util.as_string(base64.urlsafe_b64encode(util.as_bytes(x)))

def pkg_to_name(pkg):
    if pkg.startswith('_url_'): return base64.urlsafe_b64decode(pkg[5:])
    else: return pkg.replace('__', '/')

def parse_alias(s):
    i = s.find(':', 0, s.find('://'))
    if i > 0: return s[0:i], s[i+1:]
    else: return None, s


class CGetPrefix:
    def __init__(self, prefix):
        self.prefix = prefix
        self.toolchain = self.write_cmake()

    def write_cmake(self, always_write=False, **kwargs):
        return util.mkfile(self.prefix, 'cget.cmake', self.generate_cmake_toolchain(**kwargs), always_write=always_write)

    def generate_cmake_toolchain(self, toolchain=None, cxxflags=None, ldflags=None, std=None):
        if toolchain is not None: yield 'include("{0}")'.format(toolchain)
        yield 'if (CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)'
        yield '    set(CMAKE_INSTALL_PREFIX "{0}")'.format(quote(self.prefix))
        yield 'endif()'
        yield 'set(CMAKE_PREFIX_PATH "{0}")'.format(quote(self.prefix))
        if std is not None:
            yield 'if (NOT "${CMAKE_CXX_COMPILER_ID}" STREQUAL "MSVC")'
            yield '    set(CMAKE_CXX_STD_FLAG "-std={0}")'.format(std)
            yield 'endif()'
        if cxxflags is not None or std is not None:
            yield 'set(CMAKE_CXX_FLAGS "$ENV{{CXXFLAGS}} ${{CMAKE_CXX_FLAGS_INIT}} ${{CMAKE_CXX_STD_FLAG}} {0}" CACHE STRING "")'.format(util.as_string(cxxflags))
        if ldflags is not None:
            for link_type in ['SHARED', 'MODULE', 'EXE']:
                yield 'set(CMAKE_{1}_LINKER_FLAGS "$ENV{{LDFLAGS}} {0}" CACHE STRING "")'.format(ldflags, link_type)

    def get_path(self, path):
        return os.path.join(self.prefix, path)

    def create_builder(self, name):
        return Builder(self, os.path.join(self.prefix, 'tmp-' + name))

    def get_package_directory(self, name=None):
        pkg_dir = os.path.join(self.prefix, 'pkg')
        if name is None: return pkg_dir
        else: return os.path.join(pkg_dir, name)

    def parse_pkg(self, pkg):
        name, url = parse_alias(pkg)
        if '://' not in url:
            f = os.path.expanduser(url)
            if os.path.isfile(f):
                url = 'file://' + f
                if name is None: name = url_to_pkg(url)
            else:
                x = url.split('@')
                p = x[0]
                v = 'HEAD'
                if len(x) > 1: v = x[1]
                url = 'https://github.com/{0}/archive/{1}.tar.gz'.format(p, v)
                name = p.replace('/', '__')
        else:
            if name is None: name = url_to_pkg(url)
        return url, name

    def install_all(self, pkgs, test=False):
        for pkg in pkgs: self.install(pkg, test=test)

    def install(self, pkg, test=False):
        url, name = self.parse_pkg(pkg)
        pkg_dir = self.get_package_directory(name)
        if os.path.exists(pkg_dir): return "Package {0} already installed".format(pkg)
        with self.create_builder(name) as builder:
            src_dir = builder.fetch(url)
            util.requires(
                lambda: builder.configure(src_dir, install_prefix=pkg_dir),
                lambda: builder.build(target='all', config='Release')
            )
            if test: 
                util.try_until(
                    lambda: builder.build(target='check', config='Release'),
                    lambda: builder.build(target='test', config='Release')
                )
            util.require(builder.build(target='install', config='Release'))
            util.symlink_dir(pkg_dir, self.prefix)
        return "Successfully installed {0}".format(pkg)

    def remove(self, pkg):
        url, name = self.parse_pkg(pkg)
        pkg_dir = self.get_package_directory(name)
        if os.path.exists(pkg_dir):
            shutil.rmtree(pkg_dir)
            util.rm_symlink_dir(self.prefix)
            util.rm_empty_dirs(self.prefix)
            return "Removed package {0}".format(pkg)
        else:
            return "Package doesn't exists"

    def list(self):
        return (pkg_to_name(d) for d in util.lsdir(self.get_package_directory()))

    def delete_dir(self, d):
        path = os.path.join(self.prefix, d)
        if os.path.exists(path): shutil.rmtree(path)

    def clean(self):
        self.delete_dir('pkg')
        util.rm_symlink_dir(self.prefix)
        os.remove(self.toolchain)
        util.rm_empty_dirs(self.prefix)

    def pkg_config_path(self):
        libs = []
        for p in ['lib', 'lib64', 'share']:
            libs.append(self.get_path(os.path.join(p, 'pkgconfig')))
        return ':'.join(libs)

    def pkg_config(self, args):
        return util.pkg_config(args, path=self.pkg_config_path())


@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.version_option(version=__version__, prog_name='cget')
def cli():
    pass


def use_prefix():
    def callback(ctx, param, value):
        prefix = value
        if prefix is None: prefix = os.path.join(os.getcwd(), 'cget')
        return CGetPrefix(prefix)
    return click.option('-p', '--prefix', envvar='CGET_PREFIX', callback=callback, help='Set prefix used to install packages')

@cli.command(name='init')
@use_prefix()
@click.option('-t', '--toolchain', required=False, help="Set cmake toolchain file to use")
@click.option('--cxxflags', required=False, help="Set additional c++ flags")
@click.option('--ldflags', required=False, help="Set additional linker flags")
@click.option('--std', required=False, help="Set C++ standard if available")
def init_command(prefix, toolchain, cxxflags, ldflags, std):
    """ Initialize install directory """
    prefix.write_cmake(always_write=True, toolchain=toolchain, cxxflags=cxxflags, ldflags=ldflags, std=std)

# TODO: Add a verbose setting
@cli.command(name='install')
@use_prefix()
@click.option('-t', '--test', is_flag=True, help="Test package before installing by running the test or check target")
@click.argument('pkgs', nargs=-1)
def install_command(prefix, pkgs, test):
    """ Install packages """
    for pkg in pkgs:
        try:
            click.echo(prefix.install(pkg, test=test))
        except:
            click.echo("Failed to build package {0}".format(pkg))
            prefix.remove(pkg)

@cli.command(name='remove')
@use_prefix()
@click.argument('pkgs', nargs=-1)
def remove_command(prefix, pkgs):
    """ Remove packages """
    for pkg in pkgs:
        try:
            click.echo(prefix.remove(pkg))
        except:
            click.echo("Failed to remove package {0}".format(pkg))

@cli.command(name='list')
@use_prefix()
def list_command(prefix):
    """ List installed packages """
    for pkg in prefix.list():
        click.echo(pkg)

@cli.command(name='clean')
@use_prefix()
def clean_command(prefix):
    """ Clear directory """
    prefix.clean()

@cli.command(name='pkg-config', context_settings=dict(
    ignore_unknown_options=True,
))
@use_prefix()
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
def pkg_config_command(prefix, args):
    """ Pkg config """
    prefix.pkg_config(args)


if __name__ == '__main__':
    cli()

