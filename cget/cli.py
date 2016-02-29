import click, os, patoolib, urllib, shutil, sys

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
    yield 'set(CMAKE_INSTALL_PREFIX "{0}")'.format(prefix)
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

    def configure(self, src_dir):
        mkdir(self.build_dir)
        cmake([src_dir], cwd=self.build_dir, toolchain=self.prefix.toolchain)

    def build(self, target=None, config=None, cwd=None, toolchain=None):
        args = ['--build', self.build_dir]
        if config is not None: args.extend(['--config', config])
        if target is not None: args.extend(['--target', target])
        cmake(args, cwd=cwd, toolchain=toolchain)

class CGetPrefix:
    def __init__(self, prefix):
        self.prefix = prefix
        self.toolchain = mkfile(prefix, 'cget.cmake', generate_cmake_toolchain(prefix))

    def create_builder(self):
        return Builder(self, os.path.join(self.prefix, 'tmp'))

    def transform_url(self, url):
        if '://' not in url:
            x = url.split('@')
            p = x[0]
            v = 'HEAD'
            if len(x) > 1: v = x[1]
            return 'https://github.com/{0}/archive/{1}.tar.gz'.format(p, v)
        else: return url

    def install(self, url):
        with self.create_builder() as builder:
            src_dir = builder.fetch(self.transform_url(url))
            builder.configure(src_dir)
            # TODO: On window set config to Release
            builder.build(toolchain=self.toolchain)
            builder.build(target='install')

    def delete_dir(self, d):
        if os.path.exists(d): shutil.rmtree(os.path.join(self.prefix, d))

    def clean(self):
        self.delete_dir('include')
        self.delete_dir('lib')
        self.delete_dir('bin')
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
@click.argument('urls', nargs=-1)
def install_command(prefix, urls):
    """ Install url """
    for url in urls:
        prefix.install(url)

@cli.command(name='clean')
@use_prefix()
def clean_command(prefix):
    """ Clear directory """
    prefix.clean()


if __name__ == '__main__':
    cli()

