import click, os, multiprocessing

import cget.util as util

class Builder:
    def __init__(self, prefix, top_dir, exists=False):
        self.prefix = prefix
        self.top_dir = top_dir
        self.build_dir = self.get_path('build')
        self.exists = exists
        self.cmake_original_file = '__cget_original_cmake_file__.cmake'

    def get_path(self, *args):
        return os.path.join(self.top_dir, *args)

    def get_build_path(self, *args):
        return self.get_path('build', *args)

    def is_make_generator(self):
        return os.path.exists(self.get_build_path('Makefile'))

    def cmake(self, options=None, use_toolchain=False, **kwargs):
        if use_toolchain: self.prefix.cmd.cmake(options=util.merge({'-DCMAKE_TOOLCHAIN_FILE': self.prefix.toolchain}, options), **kwargs)
        else: self.prefix.cmd.cmake(options=options, **kwargs)

    def show_log(self, log):
        if self.prefix.verbose and os.path.exists(log):
            click.echo(open(log).read())

    def show_logs(self):
        self.show_log(self.get_build_path('CMakeFiles', 'CMakeOutput.log'))
        self.show_log(self.get_build_path('CMakeFiles', 'CMakeError.log'))

    def fetch(self, url, hash=None, copy=False, insecure=False):
        self.prefix.log("fetch:", url)
        if insecure: url = url.replace('https', 'http')
        f = util.retrieve_url(url, self.top_dir, copy=copy, insecure=insecure, hash=hash)
        if os.path.isfile(f):
            click.echo("Extracting archive {0} ...".format(f))
            util.extract_ar(archive=f, dst=self.top_dir)
        return next(util.get_dirs(self.top_dir))

    def configure(self, src_dir, defines=None, generator=None, install_prefix=None, test=True, variant=None):
        self.prefix.log("configure")
        util.mkdir(self.build_dir)
        args = [
            src_dir, 
            '-DCGET_CMAKE_DIR={}'.format(util.cget_dir('cmake')), 
            '-DCGET_CMAKE_ORIGINAL_SOURCE_FILE={}'.format(os.path.join(src_dir, self.cmake_original_file))
        ]
        if generator is not None: args = ['-G', util.quote(generator)] + args
        if self.prefix.verbose: args.extend(['-DCMAKE_VERBOSE_MAKEFILE=On'])
        if test: args.extend(['-DBUILD_TESTING=On'])
        else: args.extend(['-DBUILD_TESTING=Off'])
        args.extend(['-DCMAKE_BUILD_TYPE={}'.format(variant or 'Release')])
        if install_prefix is not None: args.insert(0, '-DCMAKE_INSTALL_PREFIX=' + install_prefix)
        for d in defines or []:
            args.append('-D{0}'.format(d))
        try:
            self.cmake(args=args, cwd=self.build_dir, use_toolchain=True)
        except:
            self.show_logs()
            raise

    def build(self, target=None, variant=None, cwd=None):
        self.prefix.log("build")
        args = ['--build', self.build_dir]
        if variant is not None: args.extend(['--config', variant])
        if target is not None: args.extend(['--target', target])
        if self.is_make_generator(): 
            args.extend(['--', '-j', str(multiprocessing.cpu_count())])
            if self.prefix.verbose: args.append('VERBOSE=1')
        self.cmake(args=args, cwd=cwd)

    def test(self, variant=None):
        self.prefix.log("test")
        util.try_until(
            lambda: self.build(target='check', variant=variant or 'Release'),
            lambda: self.prefix.cmd.ctest((self.prefix.verbose and ['-VV'] or []) + ['-C', variant], cwd=self.build_dir)
        )
