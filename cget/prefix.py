import os, shutil, shlex, six, inspect, click, contextlib

from cget.builder import Builder
from cget.package import fname_to_pkg
from cget.package import PackageSource
from cget.package import PackageBuild
from cget.package import parse_pkg_build
import cget.util as util
from cget.types import returns
from cget.types import params

@params(s=six.string_types)
def parse_alias(s):
    i = s.find(':', 0, max(s.find('://'), s.find(':\\')))
    if i > 0: return s[0:i], s[i+1:]
    else: return None, s

PACKAGE_SOURCE_TYPES = (six.string_types, PackageSource, PackageBuild)

class CGetPrefix:
    def __init__(self, prefix, verbose=False):
        self.prefix = prefix
        self.verbose = verbose
        self.cmd = util.Commander(paths=[self.get_path('bin')], env=self.get_env(), verbose=self.verbose)
        self.toolchain = self.write_cmake()

    def log(self, *args):
        if self.verbose: click.secho(' '.join([str(arg) for arg in args]), bold=True)

    def get_env(self):
        return {
            'PKG_CONFIG_PATH': self.pkg_config_path()
        }

    def write_cmake(self, always_write=False, **kwargs):
        return util.mkfile(self.get_private_path(), 'cget.cmake', self.generate_cmake_toolchain(**kwargs), always_write=always_write)

    @returns(inspect.isgenerator)
    def generate_cmake_toolchain(self, toolchain=None, cxxflags=None, ldflags=None, std=None):
        yield 'set(CGET_PREFIX {})'.format(util.quote(self.prefix))
        yield 'set(CMAKE_PREFIX_PATH {})'.format(util.quote(self.prefix))
        if toolchain is not None: yield 'include({})'.format(util.quote(os.path.abspath(toolchain)))
        yield 'if (CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)'
        yield '    set(CMAKE_INSTALL_PREFIX {})'.format(util.quote(self.prefix))
        yield 'endif()'
        # yield 'set(CMAKE_MODULE_PATH  ${CMAKE_PREFIX_PATH}/lib/cmake)'
        if std is not None:
            yield 'if (NOT "${CMAKE_CXX_COMPILER_ID}" STREQUAL "MSVC")'
            yield '    set(CMAKE_CXX_STD_FLAG "-std={}")'.format(std)
            yield 'endif()'
        if cxxflags is not None or std is not None:
            yield 'set(CMAKE_CXX_FLAGS "$ENV{{CXXFLAGS}} ${{CMAKE_CXX_FLAGS_INIT}} ${{CMAKE_CXX_STD_FLAG}} {}" CACHE STRING "")'.format(cxxflags or '')
        if ldflags is not None:
            for link_type in ['SHARED', 'MODULE', 'EXE']:
                yield 'set(CMAKE_{1}_LINKER_FLAGS "$ENV{{LDFLAGS}} {}" CACHE STRING "")'.format(ldflags, link_type)

    def get_path(self, path):
        return os.path.join(self.prefix, path)

    def get_private_path(self, path=None):
        p = self.get_path('cget')
        if path is None: return p
        else: return os.path.join(p, path)

    def get_builder_path(self, name, tmp=True):
        pre = 'build-'
        if tmp: pre = 'tmp-'
        return self.get_private_path(pre + name)

    @contextlib.contextmanager
    def create_builder(self, name, tmp=True):
        d = self.get_builder_path(name, tmp)
        exists = os.path.exists(d)
        util.mkdir(d)
        yield Builder(self, d, exists)
        if tmp: shutil.rmtree(d)

    def get_package_directory(self, name=None):
        pkg_dir = self.get_private_path('pkg')
        if name is None: return pkg_dir
        else: return os.path.join(pkg_dir, name)

    def get_deps_directory(self, name=None):
        deps_dir = self.get_private_path('deps')
        if name is None: return deps_dir
        else: return os.path.join(deps_dir, name)

    @returns(PackageSource)
    @params(pkg=PACKAGE_SOURCE_TYPES)
    def parse_pkg_src(self, pkg):
        if isinstance(pkg, PackageSource): return pkg
        if isinstance(pkg, PackageBuild): return self.parse_pkg_src(pkg.pkg_src)
        name, url = parse_alias(pkg)
        if '://' not in url:
            f = os.path.abspath(os.path.expanduser(url))
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
    def parse_pkg_build(self, pkg):
        if isinstance(pkg, PackageBuild): 
            pkg.pkg_src = self.parse_pkg_src(pkg.pkg_src)
            return pkg
        else: return PackageBuild(self.parse_pkg_src(pkg))

    def from_file(self, file):
        if file is not None and os.path.exists(file):
            with open(file) as f:
                for line in f.readlines():
                    tokens = shlex.split(line, comments=True)
                    if len(tokens) > 0: yield parse_pkg_build(tokens)

    def write_parent(self, pb):
        if pb.parent is not None: util.mkfile(self.get_deps_directory(pb.to_fname()), pb.parent, pb.parent)

    def install_deps(self, pb, d, test_all=False):
        for dependent in self.from_file(os.path.join(d, 'requirements.txt')):
            self.install(dependent.of(pb), test_all=test_all)

    @returns(six.string_types)
    @params(pb=PACKAGE_SOURCE_TYPES, test=bool, test_all=bool, update=bool)
    def install(self, pb, test=False, test_all=False, update=False):
        pb = self.parse_pkg_build(pb)
        # Only install test packages if we are testing
        if pb.test != test and pb.test != test_all: return ""
        pkg_dir = self.get_package_directory(pb.to_fname())
        if os.path.exists(pkg_dir): 
            self.write_parent(pb)
            if update: self.remove(pb)
            else: return "Package {} already installed".format(pb.to_name())
        with self.create_builder(pb.to_fname()) as builder:
            # Fetch package
            src_dir = builder.fetch(pb.pkg_src.url)
            # Install any dependencies first
            self.install_deps(pb, src_dir, test_all=test_all)
            # Confirue and build
            builder.configure(src_dir, defines=pb.define, install_prefix=pkg_dir)
            builder.build(config='Release')
            # Run tests if enabled
            if test or test_all: builder.test(config='Release')
            # Install
            builder.build(target='install', config='Release')
            util.symlink_dir(pkg_dir, self.prefix)
        self.write_parent(pb)
        return "Successfully installed {}".format(pb.to_name())

    @params(pb=PACKAGE_SOURCE_TYPES, test=bool)
    def build(self, pb, test=False):
        pb = self.parse_pkg_build(pb)
        src_dir = pb.pkg_src.url[7:] # Remove "file://"
        with self.create_builder(pb.to_fname(), tmp=False) as builder:
            # Install any dependencies first
            self.install_deps(pb, src_dir)
            # Confirue and build
            if not builder.exists: builder.configure(src_dir, defines=pb.define)
            builder.build(config='Release')
            # Run tests if enabled
            if test: builder.test(config='Release')

    @params(pb=PACKAGE_SOURCE_TYPES)
    def clean_build(self, pb):
        pb = self.parse_pkg_build(pb)
        shutil.rmtree(self.get_builder_path(pb.to_fname()))

    @params(pkg=PACKAGE_SOURCE_TYPES)
    def remove(self, pkg):
        pkg = self.parse_pkg_src(pkg)
        pkg_dir = self.get_package_directory(pkg.to_fname())
        deps_dir = self.get_deps_directory(pkg.to_fname())
        if os.path.exists(pkg_dir):
            shutil.rmtree(pkg_dir)
            if os.path.exists(deps_dir): shutil.rmtree(deps_dir)
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
            libs.append(self.get_path(os.path.join(p, 'pkgconfig')))
        return os.pathsep.join(libs)

