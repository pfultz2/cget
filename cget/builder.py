import click, os, shutil, multiprocessing

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
        self.log("cmake: ", toolchain, args)
        util.cmake(args, cwd=cwd, toolchain=toolchain, env=self.pkg_config_env())

    def fetch(self, url):
        self.log("fetch:", url)
        f = util.retrieve_url(url, self.tmp_dir)
        if os.path.isfile(f):
            click.echo("Extracting archive {0} ...".format(f))
            util.extract_ar(archive=f, dst=self.tmp_dir)
        return next(util.get_dirs(self.tmp_dir))

    def configure(self, src_dir, defines=[], install_prefix=None):
        util.mkdir(self.build_dir)
        args = [src_dir]
        if install_prefix is not None: args.insert(0, '-DCMAKE_INSTALL_PREFIX=' + install_prefix)
        for d in defines:
            args.append('-D{0}'.format(d))
        self.cmake(args, cwd=self.build_dir, toolchain=self.prefix.toolchain)
        if os.path.exists(os.path.join(self.build_dir, 'Makefile')): self.is_make_generator = True

    def build(self, target=None, config=None, cwd=None):
        args = ['--build', self.build_dir]
        if config is not None: args.extend(['--config', config])
        if target is not None: args.extend(['--target', target])
        if self.is_make_generator: 
            args.extend(['--', '-j', str(multiprocessing.cpu_count())])
            if self.verbose: args.append('VERBOSE=1')
        self.cmake(args, cwd=cwd)

    def test(self, config='Release'):
        util.try_until(
            lambda: self.build(target='check', config=config),
            lambda: util.ctest(config=config, verbose=self.verbose, cwd=self.build_dir)
        )
