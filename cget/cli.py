import click, os, patoolib, urllib, shutil, sys, base64

if os.name == 'posix' and sys.version_info[0] < 3:
    import subprocess32 as subprocess
else:
    import subprocess

def write_to(file, lines):
    content = list((line + "\n" for line in lines))
    if (len(content) > 0):
        open(file, 'w').writelines(content)

def mkdir(p):
    if not os.path.exists(p): os.makedirs(p)
    return p
    
def mkfile(d, file, content, always_write=True):
    mkdir(d)
    p = os.path.join(d, file)
    if not os.path.exists(p) or always_write:
        write_to(p, content)
    return p

def lsdir(p):
    return (d for d in os.listdir(p) if os.path.isdir(os.path.join(p, d)))

def symlink_dir(src, dst):
    for root, dirs, files in os.walk(src):
        for file in files:
            path = os.path.relpath(root, src)
            d = os.path.join(dst, path)
            mkdir(d)
            os.symlink(os.path.join(root, file), os.path.join(d, file))

def rm_symlink(file):
    if os.path.islink(file):
        f = os.readlink(file)
        if not os.path.exists(f): os.remove(file)

def rm_symlink_dir(d):
    for root, dirs, files in os.walk(d):
        for file in files:
            rm_symlink(os.path.join(root, file))

def get_dirs(d):
    return (os.path.join(d,o) for o in os.listdir(d) if os.path.isdir(os.path.join(d,o)))

def download_to(url, download_dir):
    name = url.split('/')[-1]
    file = os.path.join(download_dir, name)
    click.echo("Downloading {0}".format(url))
    with click.progressbar(length=100) as bar:
        def hook(count, block_size, total_size):
            percent = int(count*block_size*100/total_size)
            if percent > 100: percent = 100
            if percent < 0: percent = 0
            bar.update(percent)
        urllib.urlretrieve(url, filename=file, reporthook=hook, data=None)
    return file

def cmake(args, cwd=None, toolchain=None):
    cmake_exe = ['cmake']
    if toolchain is not None: cmake_exe.append('-DCMAKE_TOOLCHAIN_FILE={0}'.format(toolchain))
    return subprocess.Popen(cmake_exe+list(args), cwd=cwd).communicate()

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
        mkdir(self.tmp_dir)
        return self
    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.tmp_dir)

    def fetch(self, url):
        patoolib.extract_archive(download_to(url, self.tmp_dir), outdir=self.tmp_dir)
        return next(get_dirs(self.tmp_dir))

    def configure(self, src_dir, install_prefix=None):
        mkdir(self.build_dir)
        args = [src_dir]
        if install_prefix is not None: args.insert(0, '-DCMAKE_INSTALL_PREFIX=' + install_prefix)
        cmake(args, cwd=self.build_dir, toolchain=self.prefix.toolchain)

    def build(self, target=None, config=None, cwd=None, toolchain=None):
        args = ['--build', self.build_dir]
        if config is not None: args.extend(['--config', config])
        if target is not None: args.extend(['--target', target])
        cmake(args, cwd=cwd, toolchain=toolchain)

class CGetPrefix:
    def __init__(self, prefix):
        self.prefix = prefix
        self.toolchain = mkfile(prefix, 'cget.cmake', generate_cmake_toolchain(prefix))

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
            name = '_url_' + base64.encode(url[url.find('://')+3:])
        return url, name

    def get_name(self, pkg):
        if pkg.startswith('_url_'): return base64.decode(pkg[5:])
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
            symlink_dir(pkg_dir, self.prefix)

    def remove(self, pkg):
        url, name = self.transform(pkg)
        pkg_dir = self.get_package_directory(name)
        shutil.rmtree(pkg_dir)
        rm_symlink_dir(self.prefix)
        # TODO: remove empty directories

    def list(self):
        return (self.get_name(d) for d in lsdir(self.get_package_directory()))

    def delete_dir(self, d):
        path = os.path.join(self.prefix, d)
        if os.path.exists(path): shutil.rmtree(path)

    def clean(self):
        self.delete_dir('include')
        self.delete_dir('lib')
        self.delete_dir('bin')
        self.delete_dir('pkg')
        os.remove(self.toolchain)


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
    """ Install package """
    for pkg in pkgs:
        prefix.install(pkg)

@cli.command(name='remove')
@use_prefix()
@click.argument('pkgs', nargs=-1)
def remove_command(prefix, pkgs):
    """ Remove package """
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


if __name__ == '__main__':
    cli()

