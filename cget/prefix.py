import os, shutil, shlex, six, inspect, click, contextlib, uuid, sys

from cget.builder import Builder
from cget.package import fname_to_pkg
from cget.package import PackageSource
from cget.package import PackageBuild
from cget.package import parse_pkg_build_tokens
import cget.util as util
from cget.types import returns
from cget.types import params

@params(s=six.string_types)
def parse_deprecated_alias(s):
    i = s.find(':', 0, max(s.find('://'), s.find(':\\')))
    if i > 0: 
        click.echo("WARNING: Using ':' for aliases is now deprecated.")
        return s[0:i], s[i+1:]
    else: return None, s

@params(s=six.string_types)
def parse_alias(s):
    i = s.find(',')
    if i > 0: return s[0:i], s[i+1:]
    else: return parse_deprecated_alias(s)

def cmake_set(var, val, quote=True, cache=None, description=None):
    x = val
    if quote: x = util.quote(val)
    if cache is None or cache.lower() == 'none':
        yield "set({0} {1})".format(var, x)
    else:
        yield 'set({0} {1} CACHE {2} "{3}")'.format(var, x, cache, description or '')

def cmake_if(cond, *args):
    yield 'if ({})'.format(cond)
    for arg in args:
        for line in arg:
            yield '    ' + line
    yield 'endif()'

def parse_cmake_var_type(key, value):
    if ':' in key:
        p = key.split(':')
        return (p[0], p[1].upper(), value)
    elif value.lower() in ['on', 'off', 'true', 'false']: 
        return (key, 'BOOL', value)
    else:
        return (key, 'STRING', value)



PACKAGE_SOURCE_TYPES = (six.string_types, PackageSource, PackageBuild)

class CGetPrefix:
    def __init__(self, prefix, verbose=False, build_path=None):
        self.prefix = prefix
        self.verbose = verbose
        self.build_path_var = build_path
        self.cmd = util.Commander(paths=[self.get_path('bin')], env=self.get_env(), verbose=self.verbose)
        self.toolchain = self.write_cmake()

    def log(self, *args):
        if self.verbose: click.secho(' '.join([str(arg) for arg in args]), bold=True)

    def get_env(self):
        return {
            'PKG_CONFIG_PATH': self.pkg_config_path()
        }

    def write_cmake(self, always_write=False, **kwargs):
        return util.mkfile(self.get_private_path(), 'cget.cmake', util.flat(self.generate_cmake_toolchain(**kwargs)), always_write=always_write)

    @returns(inspect.isgenerator)
    def generate_cmake_toolchain(self, toolchain=None, cxx=None, cxxflags=None, ldflags=None, std=None, defines=None):
        set_ = cmake_set
        if_ = cmake_if
        yield set_('CGET_PREFIX', self.prefix)
        yield set_('CMAKE_PREFIX_PATH', self.prefix)
        yield ['include_directories(SYSTEM ${CMAKE_PREFIX_PATH}/include)']
        if toolchain: yield ['include({})'.format(util.quote(os.path.abspath(toolchain)))]
        yield if_('CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT',
            set_('CMAKE_INSTALL_PREFIX', self.prefix)
        )
        if cxx: yield set_('CMAKE_CXX_COMPILER', cxx)
        if std:
            yield if_('NOT "${CMAKE_CXX_COMPILER_ID}" STREQUAL "MSVC"',
                set_('CMAKE_CXX_STD_FLAG', "-std={}".format(std))
            )
        if cxxflags or std:
            yield set_('CMAKE_CXX_FLAGS', "$ENV{{CXXFLAGS}} ${{CMAKE_CXX_FLAGS_INIT}} ${{CMAKE_CXX_STD_FLAG}} {}".format(cxxflags or ''), cache='STRING')
        if ldflags:
            for link_type in ['SHARED', 'MODULE', 'EXE']:
                yield set_('CMAKE_{}_LINKER_FLAGS'.format(link_type), "$ENV{{LDFLAGS}} {0}".format(ldflags), cache='STRING')
        for dkey in defines or {}:
            name, vtype, value = parse_cmake_var_type(dkey, defines[dkey])
            yield set_(name, value, cache=vtype, quote=(vtype != 'BOOL'))


    def get_path(self, *paths):
        return os.path.join(self.prefix, *paths)

    def get_private_path(self, *paths):
        return self.get_path('cget', *paths)

    def get_builder_path(self, *paths):
        if self.build_path_var: return os.path.join(self.build_path_var, *paths)
        else: return self.get_private_path('build', *paths)

    @contextlib.contextmanager
    def create_builder(self, name, tmp=False):
        pre = ''
        if tmp: pre = 'tmp-'
        d = self.get_builder_path(pre + name)
        exists = os.path.exists(d)
        util.mkdir(d)
        yield Builder(self, d, exists)
        if tmp: shutil.rmtree(d)

    def get_package_directory(self, *dirs):
        return self.get_private_path('pkg', *dirs)

    def get_deps_directory(self, name, *dirs):
        return self.get_package_directory(name, 'deps', *dirs)

    @returns(PackageSource)
    @params(pkg=PACKAGE_SOURCE_TYPES)
    def parse_pkg_src(self, pkg, start=None):
        if isinstance(pkg, PackageSource): return pkg
        if isinstance(pkg, PackageBuild): return self.parse_pkg_src(pkg.pkg_src, start)
        name, url = parse_alias(pkg)
        self.log('parse_pkg_src:', name, url, pkg)
        if '://' not in url:
            f = util.actual_path(url, start)
            self.log('parse_pkg_src atual_path:', start, f)
            # f = os.path.abspath(os.path.expanduser(url))
            if os.path.exists(f):
                url = 'file://' + f
            else:
                x = url.split('@')
                p = x[0]
                v = 'HEAD'
                if len(x) > 1: v = x[1]
                if '/' in p: url = 'https://github.com/{0}/archive/{1}.tar.gz'.format(p, v)
                if name is None: name = p
        return PackageSource(name=name, url=url)

    @returns(PackageBuild)
    @params(pkg=PACKAGE_SOURCE_TYPES)
    def parse_pkg_build(self, pkg, start=None):
        if isinstance(pkg, PackageBuild): 
            pkg.pkg_src = self.parse_pkg_src(pkg.pkg_src, start)
            if pkg.cmake and not os.path.isabs(pkg.cmake):
                pkg.cmake = util.actual_path(pkg.cmake, start)
            return pkg
        else: return PackageBuild(self.parse_pkg_src(pkg, start))

    def from_file(self, file, url=None):
        if file is not None and os.path.exists(file):
            start = file
            if url is not None and url.startswith('file://'):
                start = url[7:]
            with open(file) as f:
                for line in f.readlines():
                    tokens = shlex.split(line, comments=True)
                    if len(tokens) > 0: 
                        yield self.parse_pkg_build(parse_pkg_build_tokens(tokens), start=start)

    def write_parent(self, pb, track=True):
        if track and pb.parent is not None: util.mkfile(self.get_deps_directory(pb.to_fname()), pb.parent, pb.parent)

    def install_deps(self, pb, d, test=False, test_all=False, generator=None):
        for dependent in self.from_file(os.path.join(d, 'requirements.txt'), pb.pkg_src.url):
            transient = dependent.test or dependent.build
            testing = test or test_all
            installable = not dependent.test or dependent.test == testing
            if installable: 
                self.install(dependent.of(pb), test_all=test_all, generator=generator, track=not transient)

    @returns(six.string_types)
    @params(pb=PACKAGE_SOURCE_TYPES, test=bool, test_all=bool, update=bool, track=bool)
    def install(self, pb, test=False, test_all=False, generator=None, update=False, track=True):
        pb = self.parse_pkg_build(pb)
        pkg_dir = self.get_package_directory(pb.to_fname())
        install_dir = self.get_package_directory(pb.to_fname(), 'install')
        if os.path.exists(pkg_dir): 
            self.write_parent(pb, track=track)
            if update: self.remove(pb)
            else: return "Package {} already installed".format(pb.to_name())
        with self.create_builder(uuid.uuid4().hex, tmp=True) as builder:
            # Fetch package
            src_dir = builder.fetch(pb.pkg_src.url, pb.hash)
            # Install any dependencies first
            self.install_deps(pb, src_dir, test=test, test_all=test_all, generator=generator)
            # Setup cmake file
            if pb.cmake: 
                target = os.path.join(src_dir, 'CMakeLists.txt')
                shutil.copyfile(pb.cmake, target)
            # Confirue and build
            builder.configure(src_dir, defines=pb.define, generator=generator, install_prefix=install_dir)
            builder.build(config='Release')
            # Run tests if enabled
            if test or test_all: builder.test(config='Release')
            # Install
            builder.build(target='install', config='Release')
            util.symlink_dir(install_dir, self.prefix)
        self.write_parent(pb, track=track)
        return "Successfully installed {}".format(pb.to_name())

    @params(pb=PACKAGE_SOURCE_TYPES, test=bool)
    def build(self, pb, test=False, target=None, generator=None):
        pb = self.parse_pkg_build(pb)
        src_dir = pb.pkg_src.get_src_dir()
        with self.create_builder(pb.to_fname()) as builder:
            # Install any dependencies first
            self.install_deps(pb, src_dir, generator=generator, test=test)
            # Configure and build
            if not builder.exists: builder.configure(src_dir, defines=pb.define, generator=generator)
            builder.build(config='Release', target=target)
            # Run tests if enabled
            if test: builder.test(config='Release')

    @params(pb=PACKAGE_SOURCE_TYPES)
    def build_path(self, pb):
        pb = self.parse_pkg_build(pb)
        return self.get_builder_path(pb.to_fname(), 'build')

    @params(pb=PACKAGE_SOURCE_TYPES)
    def build_clean(self, pb):
        pb = self.parse_pkg_build(pb)
        p = self.get_builder_path(pb.to_fname())
        if os.path.exists(p): shutil.rmtree(p)

    @params(pb=PACKAGE_SOURCE_TYPES)
    def build_configure(self, pb):
        pb = self.parse_pkg_build(pb)
        src_dir = pb.pkg_src.get_src_dir()
        if 'ccmake' in self.cmd:
            self.cmd.ccmake([src_dir], cwd=self.build_path(pb))
        elif 'cmake-gui' in self.cmd:
            self.cmd.cmake_gui([src_dir], cwd=self.build_path(pb))

    @params(pkg=PACKAGE_SOURCE_TYPES)
    def remove(self, pkg):
        pkg = self.parse_pkg_src(pkg)
        pkg_dir = self.get_package_directory(pkg.to_fname())
        if os.path.exists(pkg_dir):
            shutil.rmtree(pkg_dir)
            util.rm_symlink_dir(self.prefix)
            util.rm_empty_dirs(self.prefix)
            return "Removed package {}".format(pkg.name)
        else:
            return "Package doesn't exists"

    def _list_files(self, pkg=None, top=True):
        if pkg is None:
            return util.ls(self.get_package_directory(), os.path.isdir)
        else:
            p = self.parse_pkg_src(pkg)
            ls = util.ls(self.get_deps_directory(p.to_fname()), os.path.isfile)
            if top: return [p.to_fname()]+list(ls)
            else: return ls

    def list(self, pkg=None, recursive=False, top=True):
        for d in self._list_files(pkg, top):
            p = fname_to_pkg(d)
            yield p
            if recursive:
                for child in self.list(p, recursive=recursive, top=False):
                    yield child

    def clean(self):
        util.delete_dir(self.get_private_path())
        util.rm_symlink_dir(self.prefix)
        util.rm_empty_dirs(self.prefix)

    def pkg_config_path(self):
        libs = []
        for p in ['lib', 'lib64', 'share']:
            libs.append(self.get_path(p, 'pkgconfig'))
        return os.pathsep.join(libs)

    @contextlib.contextmanager
    def try_(self, msg=None, on_fail=None):
        try:
            yield
        except util.BuildError as err:
            if msg: click.echo(msg)
            if on_fail: on_fail()
            if self.verbose: 
                if err.data: click.echo(err.data)
                raise
            sys.exit(1)
        except:
            if msg: click.echo(msg)
            if on_fail: on_fail()
            if self.verbose: raise
            sys.exit(1)

