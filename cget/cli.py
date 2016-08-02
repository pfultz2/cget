import click, os, functools, sys

from cget import __version__
from cget.prefix import CGetPrefix
from cget.prefix import PackageBuild
import cget.util as util


aliases = {
    'rm': 'remove',
    'ls': 'list'
}

class AliasedGroup(click.Group):
    def get_command(self, ctx, cmd_name):
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv
        return click.Group.get_command(self, ctx, aliases[cmd_name])


@click.group(cls=AliasedGroup, context_settings={'help_option_names': ['-h', '--help']})
@click.version_option(version=__version__, prog_name='cget')
def cli():
    pass

def use_prefix(f):
    @click.option('-p', '--prefix', envvar='CGET_PREFIX', help='Set prefix used to install packages')
    @click.option('-v', '--verbose', is_flag=True, envvar='VERBOSE', help="Enable verbose mode")
    @click.option('-B', '--build-path', envvar='CGET_BUILD_PATH', help='Set the path for the build directory to use when building the package')
    @functools.wraps(f)
    def w(prefix, verbose, build_path, *args, **kwargs):
        if prefix is None: prefix = os.path.join(os.getcwd(), 'cget')
        f(CGetPrefix(prefix, verbose, build_path), *args, **kwargs)
    return w

@cli.command(name='init')
@use_prefix
@click.option('-t', '--toolchain', required=False, help="Set cmake toolchain file to use")
@click.option('--cxx', required=False, help="Set c++ compiler")
@click.option('--cxxflags', required=False, help="Set additional c++ flags")
@click.option('--ldflags', required=False, help="Set additional linker flags")
@click.option('--std', required=False, help="Set C++ standard if available")
@click.option('-D', '--define', multiple=True, help="Extra configuration variables to pass to CMake")
@click.option('--shared', is_flag=True, help="Set toolchain to build shared libraries by default")
@click.option('--static', is_flag=True, help="Set toolchain to build static libraries by default")
def init_command(prefix, toolchain, cxx, cxxflags, ldflags, std, define, shared, static):
    """ Initialize install directory """
    if shared and static:
        click.echo("ERROR: shared and static are not supported together")
        sys.exit(1)
    defines = util.to_define_dict(define)
    if shared: defines['BUILD_SHARED_LIBS'] = 'On'
    if static: defines['BUILD_SHARED_LIBS'] = 'Off'
    prefix.write_cmake(
        always_write=True, 
        toolchain=toolchain, 
        cxx=cxx,
        cxxflags=cxxflags, 
        ldflags=ldflags, 
        std=std, 
        defines=defines)

@cli.command(name='install')
@use_prefix
@click.option('-U', '--update', is_flag=True, help="Update package")
@click.option('-t', '--test', is_flag=True, help="Test package before installing by running ctest or check target")
@click.option('--test-all', is_flag=True, help="Test all packages including its dependencies before installing by running ctest or check target")
@click.option('-f', '--file', default=None, help="Install packages listed in the file")
@click.option('-D', '--define', multiple=True, help="Extra configuration variables to pass to CMake")
@click.option('-G', '--generator', envvar='CGET_GENERATOR', help='Set the generator for CMake to use')
@click.option('-X', '--cmake', help='Set cmake file to use to build project')
@click.argument('pkgs', nargs=-1, type=click.STRING)
def install_command(prefix, pkgs, define, file, test, test_all, update, generator, cmake):
    """ Install packages """
    pbs = [PackageBuild(pkg, define=define, cmake=cmake) for pkg in pkgs]
    for pb in list(prefix.from_file(file))+pbs:
        with prefix.try_("Failed to build package {}".format(pb.to_name()), on_fail=lambda: prefix.remove(pb)):
            click.echo(prefix.install(pb, test=test, test_all=test_all, update=update, generator=generator))

@cli.command(name='build')
@use_prefix
@click.option('-t', '--test', is_flag=True, help="Test package by running ctest or check target")
@click.option('-c', '--configure', is_flag=True, help="Configure cmake")
@click.option('-C', '--clean', is_flag=True, help="Remove build directory")
@click.option('-P', '--path', is_flag=True, help="Show path to build directory")
@click.option('-D', '--define', multiple=True, help="Extra configuration variables to pass to CMake")
@click.option('-T', '--target', default=None, help="Cmake target to build")
@click.option('-y', '--yes', is_flag=True, default=False)
@click.option('-G', '--generator', envvar='CGET_GENERATOR', help='Set the generator for CMake to use')
@click.argument('pkg', nargs=1, default='.', type=click.STRING)
def build_command(prefix, pkg, define, test, configure, clean, path, yes, target, generator):
    """ Build package """
    pb = PackageBuild(pkg).merge(define)
    with prefix.try_("Failed to build package {}".format(pb.to_name())):
        if configure: prefix.build_configure(pb)
        elif path: click.echo(prefix.build_path(pb))
        elif clean: 
            if not yes: yes = click.confirm("Are you sure you want to delete the build directory?")
            if yes: prefix.build_clean(pb)
        else: prefix.build(pb, test=test, target=target, generator=generator)

@cli.command(name='remove')
@use_prefix
@click.argument('pkgs', nargs=-1, type=click.STRING)
@click.option('-y', '--yes', is_flag=True, default=False)
def remove_command(prefix, pkgs, yes):
    """ Remove packages """
    pkgs_set = set((dep.name for pkg in pkgs for dep in prefix.list(pkg, recursive=True)))
    click.echo("The following packages will be deleted:")
    for pkg in pkgs_set: click.echo(pkg)
    if not yes: yes = click.confirm("Are you sure you want to remove these packages?")
    if yes:
        for pkg in pkgs_set:
            with prefix.try_("Failed to remove package {}".format(pkg)):
                prefix.remove(pkg)
                click.echo("Removed package {}".format(pkg))

@cli.command(name='list')
@use_prefix
def list_command(prefix):
    """ List installed packages """
    for pkg in prefix.list():
        click.echo(pkg.name)

# TODO: Make this command hidden
@cli.command(name='size')
@use_prefix
@click.argument('n')
def size_command(prefix, n):
    pkgs = len(list(util.ls(prefix.get_package_directory(), os.path.isdir)))
    if pkgs != int(n):
        raise util.BuildError("Not the correct number of items: {}".format(pkgs))

@cli.command(name='clean')
@use_prefix
@click.option('-y', '--yes', is_flag=True, default=False)
def clean_command(prefix, yes):
    """ Clear directory """
    if not yes: yes = click.confirm("Are you sure you want to delete all cget packages in {}?".format(prefix.prefix))
    if yes: prefix.clean()

@cli.command(name='pkg-config', context_settings=dict(
    ignore_unknown_options=True,
))
@use_prefix
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
def pkg_config_command(prefix, args):
    """ Pkg config """
    prefix.cmd.pkg_config(args)


if __name__ == '__main__':
    cli()

