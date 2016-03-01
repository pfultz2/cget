import click, os, patoolib, shutil, base64

import cget.util as util

def generate_cmake_toolchain(prefix):
    yield 'if (CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)'
    yield '    set(CMAKE_INSTALL_PREFIX "{0}")'.format(prefix)
    yield 'endif()'
    yield 'set(CMAKE_PREFIX_PATH "{0}")'.format(prefix)


class Builder:
    def __init__(self, prefix, tmp_dir):
        self.prefix = prefix
        self.tmp_dir = tmp_dir
        self.build_dir = os.path.join(tmp_dir, 'build')
    def __enter__(self):
        util.mkdir(self.tmp_dir)
        return self
    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.tmp_dir)

    def pkg_config_env(self):
        return {'PKG_CONFIG_PATH': self.prefix.pkg_config_path() }

    def cmake(self, args, cwd=None, toolchain=None):
        util.cmake(args, cwd=cwd, toolchain=toolchain, env=self.pkg_config_env())

    def fetch(self, url):
        patoolib.extract_archive(util.download_to(url, self.tmp_dir), outdir=self.tmp_dir)
        return next(util.get_dirs(self.tmp_dir))

    def configure(self, src_dir, install_prefix=None):
        util.mkdir(self.build_dir)
        args = [src_dir]
        if install_prefix is not None: args.insert(0, '-DCMAKE_INSTALL_PREFIX=' + install_prefix)
        self.cmake(args, cwd=self.build_dir, toolchain=self.prefix.toolchain)

    def build(self, target=None, config=None, cwd=None, toolchain=None):
        args = ['--build', self.build_dir]
        if config is not None: args.extend(['--config', config])
        if target is not None: args.extend(['--target', target])
        self.cmake(args, cwd=cwd, toolchain=toolchain)

class CGetPrefix:
    def __init__(self, prefix):
        self.prefix = prefix
        self.toolchain = util.mkfile(prefix, 'cget.cmake', generate_cmake_toolchain(prefix))

    def get_path(self, path):
        return os.path.join(self.prefix, path)

    def create_builder(self, name):
        return Builder(self, os.path.join(self.prefix, 'tmp-' + name))

    def get_package_directory(self, name=None):
        pkg_dir = os.path.join(self.prefix, 'pkg')
        if name is None: return pkg_dir
        else: return os.path.join(pkg_dir, name)

    def transform(self, pkg):
        url = pkg
        name = None
        if '://' not in url:
            x = url.split('@')
            p = x[0]
            v = 'HEAD'
            if len(x) > 1: v = x[1]
            url = 'https://github.com/{0}/archive/{1}.tar.gz'.format(p, v)
            name = p.replace('/', '__')
        else:
            name = '_url_' + base64.urlsafe_b64encode(url[url.find('://')+3:])
        return url, name

    def get_name(self, pkg):
        if pkg.startswith('_url_'): return base64.urlsafe_b64decode(pkg[5:])
        else: return pkg.replace('__', '/')

    def install(self, pkg):
        url, name = self.transform(pkg)
        pkg_dir = self.get_package_directory(name)
        if os.path.exists(pkg_dir): return
        with self.create_builder(name) as builder:
            src_dir = builder.fetch(url)
            builder.configure(src_dir, install_prefix=pkg_dir)
            # TODO: On window set config to Release
            builder.build(toolchain=self.toolchain)
            builder.build(target='install')
            util.symlink_dir(pkg_dir, self.prefix)

    def remove(self, pkg):
        url, name = self.transform(pkg)
        pkg_dir = self.get_package_directory(name)
        shutil.rmtree(pkg_dir)
        util.rm_symlink_dir(self.prefix)
        util.rm_empty_dirs(self.prefix)

    def list(self):
        return (self.get_name(d) for d in util.lsdir(self.get_package_directory()))

    def delete_dir(self, d):
        path = os.path.join(self.prefix, d)
        if os.path.exists(path): shutil.rmtree(path)

    def clean(self):
        self.delete_dir('pkg')
        util.rm_symlink_dir(self.prefix)
        os.remove(self.toolchain)
        util.rm_empty_dirs(self.prefix)

    def pkg_config_path(self):
        libs = [self.get_path(os.path.join('lib', 'pkgconfig')), self.get_path(os.path.join('lib64', 'pkgconfig'))]
        return ':'.join(libs)

    def pkg_config(self, args):
        util.pkg_config(args, path=self.pkg_config_path())


@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.version_option(version='0.0.1', prog_name='cget')
def cli():
    pass


def use_prefix():
    def callback(ctx, param, value):
        prefix = value
        if prefix is None: prefix = os.path.join(os.getcwd(), 'cget')
        return CGetPrefix(prefix)
    return click.option('-p', '--prefix', envvar='CGET_PREFIX', callback=callback)


@cli.command(name='install')
@use_prefix()
@click.argument('pkgs', nargs=-1)
def install_command(prefix, pkgs):
    """ Install packages """
    for pkg in pkgs:
        prefix.install(pkg)

@cli.command(name='remove')
@use_prefix()
@click.argument('pkgs', nargs=-1)
def remove_command(prefix, pkgs):
    """ Remove packages """
    for pkg in pkgs:
        prefix.remove(pkg)

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

