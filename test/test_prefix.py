import os
import shutil
import textwrap
from unittest import mock

import pytest

from cget.prefix import (
    parse_deprecated_alias,
    parse_alias,
    parse_src_name,
    cmake_set,
    cmake_append,
    cmake_if,
    cmake_else,
    parse_cmake_var_type,
    find_cmake,
    CGetPrefix,
)
from cget.package import PackageSource, PackageBuild
import cget.util as util


# ── parse_deprecated_alias ───────────────────────────────────────────────────

class TestParseDeprecatedAlias:
    def test_no_alias(self):
        name, url = parse_deprecated_alias("user/repo")
        assert name is None
        assert url == "user/repo"

    def test_with_url_scheme(self):
        name, url = parse_deprecated_alias("https://example.com/pkg.tar.gz")
        assert name is None
        assert url == "https://example.com/pkg.tar.gz"

    def test_with_windows_path(self):
        name, url = parse_deprecated_alias("C:\\path\\to\\pkg")
        assert name is None
        assert url == "C:\\path\\to\\pkg"


# ── parse_alias ──────────────────────────────────────────────────────────────

class TestParseAlias:
    def test_no_alias(self):
        name, url = parse_alias("user/repo")
        assert name is None
        assert url == "user/repo"

    def test_comma_alias(self):
        name, url = parse_alias("myname,user/repo")
        assert name == "myname"
        assert url == "user/repo"

    def test_url_with_protocol(self):
        name, url = parse_alias("https://example.com/pkg.tar.gz")
        assert name is None
        assert url == "https://example.com/pkg.tar.gz"

    def test_comma_alias_with_url(self):
        name, url = parse_alias("mypkg,https://example.com/pkg.tar.gz")
        assert name == "mypkg"
        assert url == "https://example.com/pkg.tar.gz"


# ── parse_src_name ───────────────────────────────────────────────────────────

class TestParseSrcName:
    def test_simple_name(self):
        p, v = parse_src_name("user/repo")
        assert p == "user/repo"
        assert v is None

    def test_with_version(self):
        p, v = parse_src_name("user/repo@v1.0")
        assert p == "user/repo"
        assert v == "v1.0"

    def test_with_default(self):
        p, v = parse_src_name("user/repo", default="HEAD")
        assert p == "user/repo"
        assert v == "HEAD"

    def test_version_overrides_default(self):
        p, v = parse_src_name("user/repo@v2.0", default="HEAD")
        assert v == "v2.0"

    def test_same_name_reduction(self):
        p, v = parse_src_name("boost/boost")
        assert p == "boost"

    def test_different_name_no_reduction(self):
        p, v = parse_src_name("user/repo")
        assert p == "user/repo"


# ── cmake_set ────────────────────────────────────────────────────────────────

class TestCmakeSet:
    def test_basic(self):
        lines = list(cmake_set("VAR", "value"))
        assert len(lines) == 1
        assert 'set(VAR "value")' == lines[0]

    def test_no_quote(self):
        lines = list(cmake_set("VAR", "value", quote=False))
        assert 'set(VAR value)' == lines[0]

    def test_with_cache(self):
        lines = list(cmake_set("VAR", "value", cache="STRING", description="A variable"))
        assert 'CACHE STRING' in lines[0]
        assert 'A variable' in lines[0]

    def test_cache_none(self):
        lines = list(cmake_set("VAR", "value", cache="none"))
        assert 'CACHE' not in lines[0]


# ── cmake_append ─────────────────────────────────────────────────────────────

class TestCmakeAppend:
    def test_basic(self):
        lines = list(cmake_append("VAR", "a", "b"))
        assert len(lines) == 1
        assert 'list(APPEND VAR "a" "b")' == lines[0]

    def test_no_quote(self):
        lines = list(cmake_append("VAR", "a", "b", quote=False))
        assert 'list(APPEND VAR a b)' == lines[0]


# ── cmake_if / cmake_else ───────────────────────────────────────────────────

class TestCmakeIf:
    def test_basic(self):
        lines = list(cmake_if("FOO", ["set(A B)"]))
        assert lines[0] == "if (FOO)"
        assert "    set(A B)" in lines
        assert lines[-1] == "endif()"

    def test_with_else(self):
        lines = list(cmake_if("FOO",
            ["set(A B)"],
            cmake_else(["set(C D)"])
        ))
        content = "\n".join(lines)
        assert "if (FOO)" in content
        assert "else ()" in content
        assert "endif()" in content


class TestCmakeElse:
    def test_basic(self):
        lines = list(cmake_else(["set(X Y)"]))
        assert lines[0] == "else ()"
        assert "    set(X Y)" in lines


# ── parse_cmake_var_type ─────────────────────────────────────────────────────

class TestParseCmakeVarType:
    def test_explicit_type(self):
        name, vtype, value = parse_cmake_var_type("MY_VAR:BOOL", "ON")
        assert name == "MY_VAR"
        assert vtype == "BOOL"
        assert value == "ON"

    def test_bool_value_on(self):
        name, vtype, value = parse_cmake_var_type("MY_VAR", "ON")
        assert vtype == "BOOL"

    def test_bool_value_off(self):
        name, vtype, value = parse_cmake_var_type("MY_VAR", "off")
        assert vtype == "BOOL"

    def test_bool_value_true(self):
        name, vtype, value = parse_cmake_var_type("MY_VAR", "true")
        assert vtype == "BOOL"

    def test_bool_value_false(self):
        name, vtype, value = parse_cmake_var_type("MY_VAR", "False")
        assert vtype == "BOOL"

    def test_string_value(self):
        name, vtype, value = parse_cmake_var_type("MY_VAR", "/usr/local")
        assert vtype == "STRING"
        assert value == "/usr/local"

    def test_explicit_string_type(self):
        name, vtype, value = parse_cmake_var_type("MY_VAR:string", "value")
        assert vtype == "STRING"


# ── find_cmake ───────────────────────────────────────────────────────────────

class TestFindCmake:
    def test_none_returns_none(self):
        assert find_cmake(None, "/start") is None

    def test_absolute_path_unchanged(self):
        assert find_cmake("/absolute/path.cmake", "/start") == "/absolute/path.cmake"

    def test_relative_path_exists(self, tmp_path):
        cmake_file = tmp_path / "custom.cmake"
        cmake_file.write_text("# cmake")
        result = find_cmake("custom.cmake", str(tmp_path))
        assert result == str(cmake_file)

    def test_relative_path_falls_to_cget_dir(self, tmp_path):
        # If relative path doesn't exist locally, check cget cmake dir
        result = find_cmake("nonexistent.cmake", str(tmp_path))
        # Should either return a cget cmake path or the original
        assert result is not None

    def test_empty_string(self):
        assert find_cmake("", "/start") == ""


# ── CGetPrefix ───────────────────────────────────────────────────────────────

class TestCGetPrefix:
    def test_init_default_prefix(self, tmp_path, monkeypatch):
        monkeypatch.chdir(str(tmp_path))
        p = CGetPrefix(None)
        assert p.prefix == os.path.abspath("cget")

    def test_init_custom_prefix(self, tmp_path):
        prefix_dir = str(tmp_path / "myprefix")
        p = CGetPrefix(prefix_dir)
        assert p.prefix == prefix_dir

    def test_get_path(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        assert p.get_path("lib") == os.path.join(p.prefix, "lib")
        assert p.get_path("a", "b") == os.path.join(p.prefix, "a", "b")

    def test_get_private_path(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        assert p.get_private_path() == os.path.join(p.prefix, "cget")
        assert p.get_private_path("pkg") == os.path.join(p.prefix, "cget", "pkg")

    def test_get_public_path(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        assert p.get_public_path() == os.path.join(p.prefix, "etc", "cget")
        assert p.get_public_path("recipes") == os.path.join(p.prefix, "etc", "cget", "recipes")

    def test_get_recipe_paths(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        paths = p.get_recipe_paths()
        assert len(paths) == 1
        assert paths[0].endswith("recipes")

    def test_get_builder_path_default(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.get_builder_path("pkg")
        assert "cget" in result
        assert "build" in result
        assert result.endswith("pkg")

    def test_get_builder_path_custom(self, tmp_path):
        bp = str(tmp_path / "custom_build")
        p = CGetPrefix(str(tmp_path / "pfx"), build_path=bp)
        result = p.get_builder_path("pkg")
        assert result == os.path.join(bp, "pkg")

    def test_get_package_directory(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.get_package_directory("mypkg")
        assert result == os.path.join(p.prefix, "cget", "pkg", "mypkg")

    def test_get_unlink_directory(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.get_unlink_directory("mypkg")
        assert result == os.path.join(p.prefix, "cget", "unlink", "mypkg")

    def test_get_deps_directory(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.get_deps_directory("mypkg")
        assert result == os.path.join(p.prefix, "cget", "pkg", "mypkg", "deps")

    def test_get_unlink_deps_directory(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.get_unlink_deps_directory("mypkg")
        assert result == os.path.join(p.prefix, "cget", "unlink", "mypkg", "deps")

    def test_get_env(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        env = p.get_env()
        assert 'LD_LIBRARY_PATH' in env
        assert 'PKG_CONFIG_PATH' in env
        assert env['LD_LIBRARY_PATH'] == p.get_path('lib')

    def test_pkg_config_path(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.pkg_config_path()
        assert "lib" in result
        assert "lib64" in result
        assert "share" in result
        assert "pkgconfig" in result


# ── CGetPrefix.log ───────────────────────────────────────────────────────────

class TestCGetPrefixLog:
    def test_verbose_logging(self, tmp_path, capsys):
        p = CGetPrefix(str(tmp_path / "pfx"), verbose=True)
        p.log("test", "message")
        captured = capsys.readouterr()
        assert "test message" in captured.out

    def test_quiet_no_logging(self, tmp_path, capsys):
        p = CGetPrefix(str(tmp_path / "pfx"), verbose=False)
        p.log("test", "message")
        captured = capsys.readouterr()
        assert captured.out == ""


# ── CGetPrefix.check ────────────────────────────────────────────────────────

class TestCGetPrefixCheck:
    def test_check_passes(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"), verbose=True)
        p.check(lambda: True)  # Should not raise

    def test_check_fails(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"), verbose=True)
        with pytest.raises(util.BuildError, match="ASSERTION FAILURE"):
            p.check(lambda: False)

    def test_check_not_verbose(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"), verbose=False)
        p.check(lambda: False)  # Should not raise when not verbose


# ── CGetPrefix.parse_src_file ────────────────────────────────────────────────

class TestParseSrcFile:
    def test_existing_file(self, tmp_path):
        f = tmp_path / "pkg"
        f.mkdir()
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.parse_src_file("mypkg", str(f))
        assert result is not None
        assert result.name == "mypkg"
        assert result.url == "file://" + str(f)

    def test_nonexistent_file(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.parse_src_file("mypkg", str(tmp_path / "nonexistent"))
        assert result is None

    def test_with_start_dir(self, tmp_path):
        d = tmp_path / "sub"
        d.mkdir()
        f = d / "pkg"
        f.mkdir()
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.parse_src_file("mypkg", "pkg", start=str(d))
        assert result is not None


# ── CGetPrefix.parse_src_github ──────────────────────────────────────────────

class TestParseSrcGithub:
    def test_user_repo(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.parse_src_github(None, "user/repo")
        assert result.name == "user/repo"
        assert "github.com" in result.url
        assert "user/repo" in result.url
        assert "HEAD" in result.url

    def test_user_repo_with_version(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.parse_src_github(None, "user/repo@v1.0")
        assert "v1.0" in result.url
        assert "HEAD" not in result.url

    def test_single_name(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.parse_src_github(None, "boost")
        assert "boost/boost" in result.url

    def test_custom_name(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.parse_src_github("myname", "user/repo")
        assert result.name == "myname"


# ── CGetPrefix.create_builder ────────────────────────────────────────────────

class TestCreateBuilder:
    def test_creates_directory(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        with p.create_builder("testpkg") as builder:
            assert os.path.isdir(builder.top_dir)
            assert builder.exists is False

    def test_tmp_builder_cleaned_up(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        builder_dir = None
        with p.create_builder("testpkg", tmp=True) as builder:
            builder_dir = builder.top_dir
            assert os.path.isdir(builder_dir)
        assert not os.path.exists(builder_dir)

    def test_exists_flag(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        # First create
        with p.create_builder("testpkg") as builder:
            pass
        # Second create should have exists=True
        with p.create_builder("testpkg") as builder:
            assert builder.exists is True


# ── CGetPrefix.write_cmake ──────────────────────────────────────────────────

class TestWriteCmake:
    def test_creates_toolchain_file(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        toolchain = p.write_cmake(always_write=True)
        assert os.path.exists(toolchain)
        assert toolchain.endswith("cget.cmake")


# ── CGetPrefix.generate_cmake_toolchain ──────────────────────────────────────

class TestGenerateCmakeToolchain:
    def test_basic_output(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        lines = list(p.generate_cmake_toolchain())
        content = "\n".join(lines)
        assert "CGET_PREFIX" in content
        assert "CMAKE_PREFIX_PATH" in content
        assert "CMAKE_INSTALL_PREFIX" in content

    def test_with_toolchain(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        lines = list(p.generate_cmake_toolchain(toolchain="/path/to/toolchain.cmake"))
        content = "\n".join(lines)
        assert "include" in content
        assert "toolchain.cmake" in content

    def test_with_cc(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        lines = list(p.generate_cmake_toolchain(cc="/usr/bin/gcc"))
        content = "\n".join(lines)
        assert "CMAKE_C_COMPILER" in content
        assert "/usr/bin/gcc" in content

    def test_with_cxx(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        lines = list(p.generate_cmake_toolchain(cxx="/usr/bin/g++"))
        content = "\n".join(lines)
        assert "CMAKE_CXX_COMPILER" in content

    def test_with_std(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        lines = list(p.generate_cmake_toolchain(std="c++17"))
        content = "\n".join(lines)
        assert "c++17" in content
        assert "CMAKE_CXX_STD_FLAG" in content

    def test_with_cflags(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        lines = list(p.generate_cmake_toolchain(cflags="-O2"))
        content = "\n".join(lines)
        assert "CMAKE_C_FLAGS" in content
        assert "-O2" in content

    def test_with_cxxflags(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        lines = list(p.generate_cmake_toolchain(cxxflags="-Wall"))
        content = "\n".join(lines)
        assert "CMAKE_CXX_FLAGS" in content
        assert "-Wall" in content

    def test_with_ldflags(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        lines = list(p.generate_cmake_toolchain(ldflags="-L/usr/local/lib"))
        content = "\n".join(lines)
        assert "LINKER_FLAGS" in content
        for link_type in ['STATIC', 'SHARED', 'MODULE', 'EXE']:
            assert 'CMAKE_{}_LINKER_FLAGS'.format(link_type) in content

    def test_with_defines(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        lines = list(p.generate_cmake_toolchain(defines={"MY_VAR": "value"}))
        content = "\n".join(lines)
        assert "MY_VAR" in content

    def test_shared_libs_export(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        lines = list(p.generate_cmake_toolchain())
        content = "\n".join(lines)
        assert "CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS" in content

    def test_find_framework(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        lines = list(p.generate_cmake_toolchain())
        content = "\n".join(lines)
        assert "CMAKE_FIND_FRAMEWORK" in content
        assert "LAST" in content

    def test_install_rpath(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        lines = list(p.generate_cmake_toolchain())
        content = "\n".join(lines)
        assert "CMAKE_INSTALL_RPATH" in content


# ── CGetPrefix.from_file ────────────────────────────────────────────────────

class TestFromFile:
    def test_none_file(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = list(p.from_file(None))
        assert result == []

    def test_nonexistent_file(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = list(p.from_file("/nonexistent/file.txt"))
        assert result == []

    def test_parses_package_file(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        req = tmp_path / "requirements.txt"
        req.write_text("user/repo\n")
        results = list(p.from_file(str(req)))
        assert len(results) == 1
        assert results[0].pkg_src.name == "user/repo"

    def test_skips_comments(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        req = tmp_path / "requirements.txt"
        req.write_text("# comment\nuser/repo\n")
        results = list(p.from_file(str(req)))
        assert len(results) == 1

    def test_skips_empty_lines(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        req = tmp_path / "requirements.txt"
        req.write_text("\n\nuser/repo\n\n")
        results = list(p.from_file(str(req)))
        assert len(results) == 1

    def test_multiple_packages(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        req = tmp_path / "requirements.txt"
        req.write_text("user/repo1\nuser/repo2\n")
        results = list(p.from_file(str(req)))
        assert len(results) == 2

    def test_with_defines(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        req = tmp_path / "requirements.txt"
        req.write_text("user/repo -DFOO=1\n")
        results = list(p.from_file(str(req)))
        assert len(results) == 1
        assert "FOO=1" in results[0].define


# ── CGetPrefix.write_parent ─────────────────────────────────────────────────

class TestWriteParent:
    def test_writes_parent_file(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        ps = PackageSource(name="child")
        pb = PackageBuild(pkg_src=ps, parent="parent_pkg")
        os.makedirs(p.get_deps_directory(pb.to_fname()), exist_ok=True)
        p.write_parent(pb)
        deps_dir = p.get_deps_directory(pb.to_fname())
        assert os.path.exists(os.path.join(deps_dir, "parent_pkg"))

    def test_no_parent(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        ps = PackageSource(name="child")
        pb = PackageBuild(pkg_src=ps)
        p.write_parent(pb)  # Should not raise

    def test_track_false(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        ps = PackageSource(name="child")
        pb = PackageBuild(pkg_src=ps, parent="parent_pkg")
        p.write_parent(pb, track=False)
        # Should not write when track=False


# ── CGetPrefix._list_files / list ────────────────────────────────────────────

class TestCGetPrefixList:
    def test_list_empty(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = list(p.list())
        assert result == []

    def test_list_with_packages(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        pkg_dir = p.get_package_directory("mypkg")
        os.makedirs(pkg_dir)
        result = list(p.list())
        assert len(result) == 1
        assert result[0].name == "mypkg"

    def test_list_multiple_packages(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        for name in ["pkg1", "pkg2", "pkg3"]:
            os.makedirs(p.get_package_directory(name))
        result = list(p.list())
        assert len(result) == 3
        names = sorted([r.name for r in result])
        assert names == ["pkg1", "pkg2", "pkg3"]


# ── CGetPrefix.try_ ─────────────────────────────────────────────────────────

class TestTry:
    def test_success(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"), verbose=True)
        with p.try_():
            pass  # no exception

    def test_build_error_verbose(self, tmp_path, capsys):
        p = CGetPrefix(str(tmp_path / "pfx"), verbose=True)
        with pytest.raises(util.BuildError):
            with p.try_():
                raise util.BuildError("test error")

    def test_build_error_non_verbose(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"), verbose=False)
        with pytest.raises(SystemExit):
            with p.try_():
                raise util.BuildError("test error")

    def test_build_error_with_msg(self, tmp_path, capsys):
        p = CGetPrefix(str(tmp_path / "pfx"), verbose=True)
        with pytest.raises(util.BuildError):
            with p.try_(msg="custom message"):
                raise util.BuildError("test error")
        captured = capsys.readouterr()
        assert "custom message" in captured.out

    def test_build_error_with_on_fail(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"), verbose=True)
        callback_called = []
        with pytest.raises(util.BuildError):
            with p.try_(on_fail=lambda: callback_called.append(True)):
                raise util.BuildError("test error")
        assert callback_called == [True]

    def test_unexpected_error_non_verbose(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"), verbose=False)
        with pytest.raises(SystemExit):
            with p.try_():
                raise RuntimeError("unexpected")

    def test_unexpected_error_verbose(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"), verbose=True)
        with pytest.raises(RuntimeError):
            with p.try_():
                raise RuntimeError("unexpected")


# ── CGetPrefix.clean ────────────────────────────────────────────────────────

class TestClean:
    def test_clean_removes_private_dir(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        private = p.get_private_path()
        # private dir already exists from __init__ (write_cmake)
        util.mkfile(private, "test.txt", ["data"])
        # Need a file in prefix to avoid rm_empty_dirs error
        os.makedirs(p.get_path("lib"), exist_ok=True)
        util.mkfile(p.get_path("lib"), "keep.txt", ["data"])
        p.clean()
        assert not os.path.exists(private)


# ── CGetPrefix.clean_cache ──────────────────────────────────────────────────

class TestCleanCache:
    def test_clean_cache(self, tmp_path, monkeypatch):
        cache_dir = str(tmp_path / "cache")
        os.makedirs(cache_dir)
        monkeypatch.setattr(util, 'get_cache_path', lambda *args: os.path.join(cache_dir, *args) if args else cache_dir)
        p = CGetPrefix(str(tmp_path / "pfx"))
        (tmp_path / "cache" / "somefile").write_text("data")
        p.clean_cache()
        assert not os.path.exists(cache_dir)

    def test_clean_cache_no_cache(self, tmp_path, monkeypatch):
        cache_dir = str(tmp_path / "nocache")
        monkeypatch.setattr(util, 'get_cache_path', lambda *args: os.path.join(cache_dir, *args) if args else cache_dir)
        p = CGetPrefix(str(tmp_path / "pfx"))
        p.clean_cache()  # Should not raise
