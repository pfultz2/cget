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


# ── parse_deprecated_alias (additional) ──────────────────────────────────────

class TestParseDeprecatedAliasAdditional:
    def test_colon_alias(self):
        # Input like "myalias:user/repo" with no :// before the colon
        name, url = parse_deprecated_alias("myalias:user/repo")
        assert name == "myalias"
        assert url == "user/repo"

    def test_colon_after_protocol(self):
        # The colon in "https://" should NOT trigger alias parsing
        name, url = parse_deprecated_alias("https://example.com")
        assert name is None
        assert url == "https://example.com"

    def test_no_colon(self):
        name, url = parse_deprecated_alias("simple")
        assert name is None
        assert url == "simple"


# ── parse_alias (additional) ─────────────────────────────────────────────────

class TestParseAliasAdditional:
    def test_comma_at_start(self):
        # comma at position 0 -> i == 0, which is not > 0
        name, url = parse_alias(",user/repo")
        # Falls through to parse_deprecated_alias
        assert name is None

    def test_multiple_commas(self):
        name, url = parse_alias("a,b,c")
        assert name == "a"
        assert url == "b,c"


# ── parse_src_name (additional) ──────────────────────────────────────────────

class TestParseSrcNameAdditional:
    def test_multiple_at_signs(self):
        p, v = parse_src_name("user/repo@v1@extra")
        assert p == "user/repo"
        assert v == "v1"

    def test_no_slash(self):
        p, v = parse_src_name("zlib")
        assert p == "zlib"
        assert v is None

    def test_triple_same_name(self):
        # functools.reduce only reduces if consecutive pairs are equal
        # For "x/x/x": reduce(lambda x,y: x==y, ["x","x","x"]) = (True == "x") = False
        # So no reduction happens
        p, v = parse_src_name("x/x/x")
        assert p == "x/x/x"


# ── cmake_set (additional) ──────────────────────────────────────────────────

class TestCmakeSetAdditional:
    def test_cache_bool(self):
        lines = list(cmake_set("FLAG", "ON", cache="BOOL"))
        assert 'CACHE BOOL' in lines[0]

    def test_with_no_description(self):
        lines = list(cmake_set("VAR", "val", cache="STRING"))
        assert 'CACHE STRING ""' in lines[0]


# ── cmake_append (additional) ───────────────────────────────────────────────

class TestCmakeAppendAdditional:
    def test_single_value(self):
        lines = list(cmake_append("VAR", "a"))
        assert 'list(APPEND VAR "a")' == lines[0]


# ── cmake_if (additional) ───────────────────────────────────────────────────

class TestCmakeIfAdditional:
    def test_empty_body(self):
        lines = list(cmake_if("COND"))
        assert lines[0] == "if (COND)"
        assert lines[-1] == "endif()"

    def test_multiple_body_args(self):
        lines = list(cmake_if("COND", ["set(A B)"], ["set(C D)"]))
        content = "\n".join(lines)
        assert "set(A B)" in content
        assert "set(C D)" in content


# ── cmake_else (additional) ─────────────────────────────────────────────────

class TestCmakeElseAdditional:
    def test_empty_body(self):
        lines = list(cmake_else())
        assert lines == ["else ()"]

    def test_multiple_body_args(self):
        lines = list(cmake_else(["set(A B)"], ["set(C D)"]))
        assert "else ()" in lines
        assert "    set(A B)" in lines
        assert "    set(C D)" in lines


# ── parse_cmake_var_type (additional) ───────────────────────────────────────

class TestParseCmakeVarTypeAdditional:
    def test_multiple_colons(self):
        name, vtype, value = parse_cmake_var_type("MY:VAR:PATH", "val")
        assert name == "MY"
        assert vtype == "VAR"

    def test_filepath_type(self):
        name, vtype, value = parse_cmake_var_type("MY_VAR:FILEPATH", "/path/to/file")
        assert vtype == "FILEPATH"


# ── find_cmake (additional) ─────────────────────────────────────────────────

class TestFindCmakeAdditional:
    def test_cget_cmake_file_exists(self, tmp_path):
        # Test the path where cget_dir/cmake/name exists
        name = "cget.cmake"
        result = find_cmake(name, str(tmp_path))
        # Since cget/cmake/cget.cmake likely doesn't exist, it should fall through
        assert result is not None

    def test_cget_cmake_file_with_extension(self):
        # Test the .cmake extension append path
        result = find_cmake("nonexistent_xyz", "/tmp")
        # Will check cget_dir/cmake/nonexistent_xyz and nonexistent_xyz.cmake
        assert result is not None


# ── CGetPrefix.parse_src_recipe ──────────────────────────────────────────────

class TestParseSrcRecipe:
    def test_recipe_found(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        # Create recipe directory
        recipe_path = os.path.join(p.get_recipe_paths()[0], "mypkg")
        os.makedirs(recipe_path)
        result = p.parse_src_recipe(None, "mypkg")
        assert result is not None
        assert result.name == "mypkg"
        # parse_src_recipe uses normcase on the path; version=None appends trailing sep
        assert os.path.normcase(recipe_path) in result.recipe

    def test_recipe_not_found(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.parse_src_recipe(None, "nonexistent_pkg")
        assert result is None

    def test_recipe_with_custom_name(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        recipe_path = os.path.join(p.get_recipe_paths()[0], "mypkg")
        os.makedirs(recipe_path)
        result = p.parse_src_recipe("custom_name", "mypkg")
        assert result is not None
        assert result.name == "custom_name"

    def test_recipe_with_version(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        recipe_path = os.path.join(p.get_recipe_paths()[0], "mypkg", "1.0")
        os.makedirs(recipe_path)
        result = p.parse_src_recipe(None, "mypkg@1.0")
        assert result is not None
        assert result.recipe == os.path.normcase(recipe_path)


# ── CGetPrefix.parse_pkg_src ────────────────────────────────────────────────

class TestParsePkgSrc:
    def test_with_package_source(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        ps = PackageSource(name="test", url="https://example.com")
        result = p.parse_pkg_src(ps)
        assert result is ps

    def test_with_package_build(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        ps = PackageSource(name="test", url="https://example.com")
        pb = PackageBuild(pkg_src=ps)
        result = p.parse_pkg_src(pb)
        assert result is ps

    def test_string_with_url(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.parse_pkg_src("https://example.com/pkg.tar.gz")
        assert isinstance(result, PackageSource)
        assert result.url == "https://example.com/pkg.tar.gz"

    def test_string_github(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.parse_pkg_src("user/repo")
        assert isinstance(result, PackageSource)
        assert "github.com" in result.url

    def test_string_local_file(self, tmp_path):
        d = tmp_path / "localdir"
        d.mkdir()
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.parse_pkg_src(str(d))
        assert isinstance(result, PackageSource)
        assert result.url.startswith("file://")

    def test_string_with_alias(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.parse_pkg_src("myname,user/repo")
        assert result.name == "myname"
        assert "github.com" in result.url

    def test_no_recipe_flag(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        # Create a recipe that would match
        recipe_path = os.path.join(p.get_recipe_paths()[0], "zlib")
        os.makedirs(recipe_path)
        # With no_recipe=True, should skip recipe and go to github
        result = p.parse_pkg_src("zlib", no_recipe=True)
        assert result.recipe is None
        assert "github.com" in result.url


# ── CGetPrefix.parse_pkg_build ──────────────────────────────────────────────

class TestParsePkgBuild:
    def test_with_string(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.parse_pkg_build("user/repo")
        assert isinstance(result, PackageBuild)
        assert result.pkg_src.name == "user/repo"

    def test_with_package_build(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        ps = PackageSource(name="test", url="https://example.com/pkg.tar.gz")
        pb = PackageBuild(pkg_src=ps, define=["FOO=1"])
        result = p.parse_pkg_build(pb)
        assert result.define == ["FOO=1"]
        assert result.pkg_src.url == "https://example.com/pkg.tar.gz"

    def test_with_cmake(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        cmake_file = tmp_path / "custom.cmake"
        cmake_file.write_text("# cmake")
        ps = PackageSource(name="test", url="https://example.com/pkg.tar.gz")
        pb = PackageBuild(pkg_src=ps, cmake=str(cmake_file))
        result = p.parse_pkg_build(pb, start=str(tmp_path))
        assert result.cmake == str(cmake_file)

    def test_with_recipe_via_package_build(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        # Create recipe
        recipe_path = os.path.join(p.get_recipe_paths()[0], "mypkg")
        os.makedirs(recipe_path, exist_ok=True)
        pkg_txt = os.path.join(recipe_path, "package.txt")
        with open(pkg_txt, 'w') as f:
            f.write("user/mypkg\n")
        # Go through PackageBuild path which correctly passes pkg to from_recipe
        pb = PackageBuild(pkg_src="mypkg", define=["FOO=1"])
        result = p.parse_pkg_build(pb)
        assert isinstance(result, PackageBuild)
        assert result.pkg_src.name == "mypkg"
        assert "FOO=1" in result.define


# ── CGetPrefix.from_recipe ──────────────────────────────────────────────────

class TestFromRecipe:
    def test_basic_recipe(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        recipe = str(tmp_path / "recipe")
        os.makedirs(recipe)
        with open(os.path.join(recipe, "package.txt"), 'w') as f:
            f.write("user/repo\n")
        result = p.from_recipe(recipe, name="myname")
        assert isinstance(result, PackageBuild)
        assert result.pkg_src.name == "myname"

    def test_recipe_with_requirements(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        recipe = str(tmp_path / "recipe")
        os.makedirs(recipe)
        with open(os.path.join(recipe, "package.txt"), 'w') as f:
            f.write("user/repo\n")
        req = os.path.join(recipe, "requirements.txt")
        with open(req, 'w') as f:
            f.write("dep/lib\n")
        result = p.from_recipe(recipe)
        assert result.requirements == req

    def test_recipe_missing_package_txt(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        recipe = str(tmp_path / "recipe")
        os.makedirs(recipe)
        with pytest.raises(util.BuildError):
            p.from_recipe(recipe)

    def test_recipe_with_pkg_merge(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        recipe = str(tmp_path / "recipe")
        os.makedirs(recipe)
        with open(os.path.join(recipe, "package.txt"), 'w') as f:
            f.write("user/repo -DFOO=1\n")
        ps = PackageSource(name="override", url="https://example.com/pkg.tar.gz")
        pkg = PackageBuild(pkg_src=ps, define=["BAR=2"])
        result = p.from_recipe(recipe, pkg=pkg)
        assert result.pkg_src.name == "override"
        assert "BAR=2" in result.define


# ── CGetPrefix.from_file (additional) ───────────────────────────────────────

class TestFromFileAdditional:
    def test_recursive_file_reference(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        # Create a file that references another file via -f
        inner = tmp_path / "inner.txt"
        inner.write_text("user/inner_pkg\n")
        outer = tmp_path / "outer.txt"
        outer.write_text("user/outer_pkg\n-f {}\n".format(str(inner)))
        results = list(p.from_file(str(outer)))
        assert len(results) == 2
        names = [r.pkg_src.name for r in results]
        assert "user/outer_pkg" in names
        assert "user/inner_pkg" in names

    def test_with_url(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        req = tmp_path / "requirements.txt"
        req.write_text("user/repo\n")
        results = list(p.from_file(str(req), url="file://" + str(tmp_path)))
        assert len(results) == 1

    def test_with_hash(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        req = tmp_path / "requirements.txt"
        req.write_text("user/repo -H sha256:abc123\n")
        results = list(p.from_file(str(req)))
        assert len(results) == 1
        assert results[0].hash == "sha256:abc123"

    def test_with_cmake_flag(self, tmp_path):
        cmake_file = tmp_path / "custom.cmake"
        cmake_file.write_text("# cmake")
        p = CGetPrefix(str(tmp_path / "pfx"))
        req = tmp_path / "requirements.txt"
        req.write_text("user/repo -X {}\n".format(str(cmake_file)))
        results = list(p.from_file(str(req)))
        assert len(results) == 1
        assert results[0].cmake is not None

    def test_with_test_flag(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        req = tmp_path / "requirements.txt"
        req.write_text("user/repo -t\n")
        results = list(p.from_file(str(req)))
        assert len(results) == 1
        assert results[0].test is True

    def test_with_build_flag(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        req = tmp_path / "requirements.txt"
        req.write_text("user/repo -b\n")
        results = list(p.from_file(str(req)))
        assert len(results) == 1
        assert results[0].build is True

    def test_deeply_nested_file_references(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        # level3 -> level2 -> level1
        level1 = tmp_path / "level1.txt"
        level1.write_text("user/pkg1\n")
        level2 = tmp_path / "level2.txt"
        level2.write_text("-f {}\nuser/pkg2\n".format(str(level1)))
        level3 = tmp_path / "level3.txt"
        level3.write_text("-f {}\nuser/pkg3\n".format(str(level2)))
        results = list(p.from_file(str(level3)))
        assert len(results) == 3
        names = sorted([r.pkg_src.name for r in results])
        assert names == ["user/pkg1", "user/pkg2", "user/pkg3"]


# ── CGetPrefix.ignore ───────────────────────────────────────────────────────

class TestIgnore:
    def test_ignore_new_package(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        result = p.ignore("user/repo")
        assert "Ignore" in result
        pkg_dir = p.get_package_directory(p.parse_pkg_src("user/repo").to_fname())
        assert os.path.exists(pkg_dir)
        assert os.path.exists(os.path.join(pkg_dir, "ignore"))

    def test_ignore_already_installed(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        # Pre-create the package directory
        pkg_src = p.parse_pkg_src("user/repo")
        pkg_dir = p.get_package_directory(pkg_src.to_fname())
        os.makedirs(pkg_dir)
        result = p.ignore("user/repo")
        assert "already installed" in result


# ── CGetPrefix.build_path ───────────────────────────────────────────────────

class TestBuildPath:
    def test_build_path(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        # Use a file:// URL so parse_pkg_build works
        d = tmp_path / "project"
        d.mkdir()
        result = p.build_path("file://" + str(d))
        assert result.endswith("build")


# ── CGetPrefix.build_clean ──────────────────────────────────────────────────

class TestBuildClean:
    def test_build_clean_existing(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        d = tmp_path / "project"
        d.mkdir()
        ps = p.parse_pkg_src("file://" + str(d))
        # Create builder directory
        builder_dir = p.get_builder_path(ps.to_fname())
        os.makedirs(builder_dir)
        (os.path.join(builder_dir, "somefile")).encode  # just a marker
        p.build_clean("file://" + str(d))
        assert not os.path.exists(builder_dir)

    def test_build_clean_nonexistent(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        d = tmp_path / "project"
        d.mkdir()
        p.build_clean("file://" + str(d))  # Should not raise


# ── CGetPrefix.remove / unlink / link ───────────────────────────────────────

class TestUnlinkLink:
    def _setup_installed_package(self, p, name, tmp_path):
        """Helper to create a fake installed package."""
        pkg_dir = p.get_package_directory(name)
        install_dir = os.path.join(pkg_dir, "install")
        os.makedirs(install_dir)
        lib_dir = os.path.join(install_dir, "lib")
        os.makedirs(lib_dir)
        with open(os.path.join(lib_dir, "libfoo.txt"), "w") as f:
            f.write("lib content")
        # Copy install into prefix
        prefix_lib = p.get_path("lib")
        os.makedirs(prefix_lib, exist_ok=True)
        shutil.copy(os.path.join(lib_dir, "libfoo.txt"), os.path.join(prefix_lib, "libfoo.txt"))
        return pkg_dir

    def test_unlink_moves_to_unlink_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(util, 'USE_SYMLINKS', False)
        p = CGetPrefix(str(tmp_path / "pfx"))
        pkg_name = "mypkg"
        self._setup_installed_package(p, pkg_name, tmp_path)
        p.unlink(PackageSource(name=pkg_name, fname=pkg_name))
        # Package should be moved to unlink directory
        assert os.path.exists(p.get_unlink_directory(pkg_name))
        assert not os.path.exists(p.get_package_directory(pkg_name))

    def test_remove_deletes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(util, 'USE_SYMLINKS', False)
        p = CGetPrefix(str(tmp_path / "pfx"))
        pkg_name = "mypkg"
        self._setup_installed_package(p, pkg_name, tmp_path)
        p.remove(PackageSource(name=pkg_name, fname=pkg_name))
        # Package should be completely gone
        assert not os.path.exists(p.get_package_directory(pkg_name))
        assert not os.path.exists(p.get_unlink_directory(pkg_name))

    def test_link_restores(self, tmp_path, monkeypatch):
        monkeypatch.setattr(util, 'USE_SYMLINKS', False)
        p = CGetPrefix(str(tmp_path / "pfx"))
        pkg_name = "mypkg"
        self._setup_installed_package(p, pkg_name, tmp_path)
        ps = PackageSource(name=pkg_name, fname=pkg_name)
        # Unlink first
        p.unlink(ps)
        assert os.path.exists(p.get_unlink_directory(pkg_name))
        # Then link back
        p.link(ps)
        assert os.path.exists(p.get_package_directory(pkg_name))
        assert not os.path.exists(p.get_unlink_directory(pkg_name))

    def test_unlink_nonexistent_no_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(util, 'USE_SYMLINKS', False)
        p = CGetPrefix(str(tmp_path / "pfx"))
        # Unlinking something that doesn't exist should not raise
        ps = PackageSource(name="nonexistent", fname="nonexistent")
        p.unlink(ps)  # no error

    @pytest.mark.skipif(os.name != 'posix', reason="symlinks need posix")
    def test_unlink_with_symlinks(self, tmp_path, monkeypatch):
        monkeypatch.setattr(util, 'USE_SYMLINKS', True)
        p = CGetPrefix(str(tmp_path / "pfx"))
        pkg_name = "mypkg"
        pkg_dir = p.get_package_directory(pkg_name)
        install_dir = os.path.join(pkg_dir, "install")
        os.makedirs(install_dir)
        lib_dir = os.path.join(install_dir, "lib")
        os.makedirs(lib_dir)
        with open(os.path.join(lib_dir, "libfoo.txt"), "w") as f:
            f.write("lib content")
        # Symlink into prefix
        prefix_lib = p.get_path("lib")
        os.makedirs(prefix_lib, exist_ok=True)
        os.symlink(os.path.join(lib_dir, "libfoo.txt"), os.path.join(prefix_lib, "libfoo.txt"))
        ps = PackageSource(name=pkg_name, fname=pkg_name)
        p.unlink(ps)
        assert os.path.exists(p.get_unlink_directory(pkg_name))
        # Symlink in prefix should be removed
        assert not os.path.exists(os.path.join(prefix_lib, "libfoo.txt"))


# ── CGetPrefix._list_files ──────────────────────────────────────────────────

class TestListFiles:
    def test_list_files_no_package(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        for name in ["pkg1", "pkg2"]:
            os.makedirs(p.get_package_directory(name))
        result = sorted(p._list_files())
        assert "pkg1" in result
        assert "pkg2" in result

    def test_list_files_with_package(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        pkg_dir = p.get_package_directory("mypkg")
        deps_dir = p.get_deps_directory("mypkg")
        os.makedirs(pkg_dir)
        os.makedirs(deps_dir)
        # Add a dependency file
        with open(os.path.join(deps_dir, "dep1"), "w") as f:
            f.write("dep1")
        result = list(p._list_files("mypkg"))
        assert "mypkg" in result
        assert "dep1" in result

    def test_list_files_top_false(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        pkg_dir = p.get_package_directory("mypkg")
        deps_dir = p.get_deps_directory("mypkg")
        os.makedirs(pkg_dir)
        os.makedirs(deps_dir)
        with open(os.path.join(deps_dir, "dep1"), "w") as f:
            f.write("dep1")
        result = list(p._list_files("mypkg", top=False))
        assert "mypkg" not in result
        assert "dep1" in result


# ── CGetPrefix.list (additional) ────────────────────────────────────────────

class TestCGetPrefixListAdditional:
    def test_list_recursive(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        # Create parent and child packages
        os.makedirs(p.get_package_directory("parent"))
        os.makedirs(p.get_package_directory("child"))
        deps_dir = p.get_deps_directory("parent")
        os.makedirs(deps_dir)
        with open(os.path.join(deps_dir, "child"), "w") as f:
            f.write("child")
        result = list(p.list("parent", recursive=True))
        names = [r.name for r in result]
        assert "parent" in names
        assert "child" in names

    def test_list_specific_package(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        os.makedirs(p.get_package_directory("mypkg"))
        result = list(p.list("mypkg"))
        assert len(result) == 1
        assert result[0].name == "mypkg"


# ── CGetPrefix.install ──────────────────────────────────────────────────────

class TestInstall:
    def test_install_already_installed(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        ps = PackageSource(name="user/repo", url="https://github.com/user/repo/archive/HEAD.tar.gz")
        pkg_dir = p.get_package_directory(ps.to_fname())
        os.makedirs(pkg_dir)
        result = p.install(PackageBuild(pkg_src=ps))
        assert "already installed" in result

    def test_install_relinks_unlinked(self, tmp_path, monkeypatch):
        monkeypatch.setattr(util, 'USE_SYMLINKS', False)
        p = CGetPrefix(str(tmp_path / "pfx"))
        ps = PackageSource(name="mypkg", url="https://github.com/user/repo/archive/HEAD.tar.gz")
        # Create unlink directory with install subdir
        unlink_dir = p.get_unlink_directory(ps.to_fname())
        install_dir = os.path.join(unlink_dir, "install")
        os.makedirs(install_dir)
        lib_dir = os.path.join(install_dir, "lib")
        os.makedirs(lib_dir)
        with open(os.path.join(lib_dir, "libfoo.txt"), "w") as f:
            f.write("lib content")
        # Need pkg dir to exist for link
        os.makedirs(p.get_package_directory(), exist_ok=True)
        result = p.install(PackageBuild(pkg_src=ps))
        assert "Linking" in result

    def test_install_update_removes_unlinked(self, tmp_path, monkeypatch):
        monkeypatch.setattr(util, 'USE_SYMLINKS', False)
        p = CGetPrefix(str(tmp_path / "pfx"))
        ps = PackageSource(name="mypkg", url="https://github.com/user/repo/archive/HEAD.tar.gz")
        # Create unlink directory
        unlink_dir = p.get_unlink_directory(ps.to_fname())
        os.makedirs(unlink_dir)
        # update=True should remove unlinked dir rather than relinking
        # This will then try to fetch/build which we need to mock
        with mock.patch.object(p, 'create_builder') as mock_cb:
            mock_builder = mock.MagicMock()
            mock_builder.fetch.return_value = str(tmp_path / "src")
            os.makedirs(str(tmp_path / "src"), exist_ok=True)
            mock_builder.cmake_original_file = '__cget_original_cmake_file__.cmake'
            mock_cb.return_value.__enter__ = mock.MagicMock(return_value=mock_builder)
            mock_cb.return_value.__exit__ = mock.MagicMock(return_value=False)
            with mock.patch.object(p, 'install_deps'):
                result = p.install(PackageBuild(pkg_src=ps), update=True)
                assert "Successfully installed" in result
                assert not os.path.exists(unlink_dir)


# ── CGetPrefix.install_deps ─────────────────────────────────────────────────

class TestInstallDeps:
    def test_no_requirements(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        ps = PackageSource(name="pkg", url="https://example.com")
        pb = PackageBuild(pkg_src=ps)
        src_dir = str(tmp_path / "src")
        os.makedirs(src_dir)
        # No requirements.txt in src_dir, should not raise
        p.install_deps(pb, src_dir)

    def test_with_requirements_file(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        ps = PackageSource(name="pkg", url="https://example.com")
        pb = PackageBuild(pkg_src=ps)
        src_dir = str(tmp_path / "src")
        os.makedirs(src_dir)
        req = os.path.join(src_dir, "requirements.txt")
        with open(req, 'w') as f:
            f.write("dep/lib\n")
        with mock.patch.object(p, 'install') as mock_install:
            mock_install.return_value = "installed"
            p.install_deps(pb, src_dir)
            mock_install.assert_called_once()

    def test_ignore_requirements(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        ps = PackageSource(name="pkg", url="https://example.com")
        pb = PackageBuild(pkg_src=ps)
        src_dir = str(tmp_path / "src")
        os.makedirs(src_dir)
        req = os.path.join(src_dir, "requirements.txt")
        with open(req, 'w') as f:
            f.write("dep/lib\n")
        with mock.patch.object(p, 'install') as mock_install:
            p.install_deps(pb, src_dir, ignore_requirements=True)
            mock_install.assert_not_called()

    def test_test_dependency_skipped_when_not_testing(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        ps = PackageSource(name="pkg", url="https://example.com")
        pb = PackageBuild(pkg_src=ps)
        src_dir = str(tmp_path / "src")
        os.makedirs(src_dir)
        req = os.path.join(src_dir, "requirements.txt")
        with open(req, 'w') as f:
            f.write("dep/lib -t\n")
        with mock.patch.object(p, 'install') as mock_install:
            p.install_deps(pb, src_dir, test=False)
            # Test dependency should be skipped when not testing
            mock_install.assert_not_called()

    def test_test_dependency_installed_when_testing(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        ps = PackageSource(name="pkg", url="https://example.com")
        pb = PackageBuild(pkg_src=ps)
        src_dir = str(tmp_path / "src")
        os.makedirs(src_dir)
        req = os.path.join(src_dir, "requirements.txt")
        with open(req, 'w') as f:
            f.write("dep/lib -t\n")
        with mock.patch.object(p, 'install') as mock_install:
            mock_install.return_value = "installed"
            p.install_deps(pb, src_dir, test=True)
            mock_install.assert_called_once()

    def test_custom_requirements_file(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        custom_req = str(tmp_path / "custom_reqs.txt")
        with open(custom_req, 'w') as f:
            f.write("dep/custom\n")
        ps = PackageSource(name="pkg", url="https://example.com")
        pb = PackageBuild(pkg_src=ps, requirements=custom_req)
        src_dir = str(tmp_path / "src")
        os.makedirs(src_dir)
        with mock.patch.object(p, 'install') as mock_install:
            mock_install.return_value = "installed"
            p.install_deps(pb, src_dir)
            mock_install.assert_called_once()


# ── CGetPrefix.build ────────────────────────────────────────────────────────

class TestPrefixBuild:
    def test_build_from_local_dir(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        src = tmp_path / "project"
        src.mkdir()
        (src / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.0)\nproject(test)")
        ps = PackageSource(name="test", url="file://" + str(src))
        pb = PackageBuild(pkg_src=ps)
        with mock.patch.object(p, 'install_deps'):
            with mock.patch('cget.builder.Builder.configure') as mock_configure:
                with mock.patch('cget.builder.Builder.build') as mock_build:
                    p.build(pb)
                    mock_configure.assert_called_once()
                    mock_build.assert_called_once()

    def test_build_with_dev_requirements(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        src = tmp_path / "project"
        src.mkdir()
        dev_req = src / "dev-requirements.txt"
        dev_req.write_text("dep/dev\n")
        ps = PackageSource(name="test", url="file://" + str(src))
        pb = PackageBuild(pkg_src=ps)
        with mock.patch.object(p, 'install_deps') as mock_deps:
            with mock.patch('cget.builder.Builder.configure'):
                with mock.patch('cget.builder.Builder.build'):
                    p.build(pb)
                    # pb.requirements should be set to dev-requirements.txt
                    assert pb.requirements == str(dev_req)

    def test_build_with_regular_requirements(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        src = tmp_path / "project"
        src.mkdir()
        req = src / "requirements.txt"
        req.write_text("dep/lib\n")
        ps = PackageSource(name="test", url="file://" + str(src))
        pb = PackageBuild(pkg_src=ps)
        with mock.patch.object(p, 'install_deps') as mock_deps:
            with mock.patch('cget.builder.Builder.configure'):
                with mock.patch('cget.builder.Builder.build'):
                    p.build(pb)
                    assert pb.requirements == str(req)

    def test_build_existing_skips_configure(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        src = tmp_path / "project"
        src.mkdir()
        ps = PackageSource(name="test", url="file://" + str(src))
        pb = PackageBuild(pkg_src=ps)
        # Pre-create builder dir so exists=True
        builder_path = p.get_builder_path(pb.to_fname())
        os.makedirs(builder_path)
        with mock.patch.object(p, 'install_deps'):
            with mock.patch('cget.builder.Builder.configure') as mock_configure:
                with mock.patch('cget.builder.Builder.build'):
                    p.build(pb)
                    mock_configure.assert_not_called()

    def test_build_with_test(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        src = tmp_path / "project"
        src.mkdir()
        ps = PackageSource(name="test", url="file://" + str(src))
        pb = PackageBuild(pkg_src=ps)
        with mock.patch.object(p, 'install_deps'):
            with mock.patch('cget.builder.Builder.configure'):
                with mock.patch('cget.builder.Builder.build'):
                    with mock.patch('cget.builder.Builder.test') as mock_test:
                        p.build(pb, test=True)
                        mock_test.assert_called_once()


# ── CGetPrefix.try_ (additional) ────────────────────────────────────────────

class TestTryAdditional:
    def test_build_error_with_data_verbose(self, tmp_path, capsys):
        p = CGetPrefix(str(tmp_path / "pfx"), verbose=True)
        with pytest.raises(util.BuildError):
            with p.try_():
                raise util.BuildError("err", data={"env": "val"})
        captured = capsys.readouterr()
        assert "err" in captured.out

    def test_unexpected_error_with_on_fail(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"), verbose=True)
        callback_called = []
        with pytest.raises(RuntimeError):
            with p.try_(on_fail=lambda: callback_called.append(True)):
                raise RuntimeError("unexpected")
        assert callback_called == [True]


# ── CGetPrefix.generate_cmake_toolchain (additional) ────────────────────────

class TestGenerateCmakeToolchainAdditional:
    def test_std_with_cxxflags(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        lines = list(p.generate_cmake_toolchain(std="c++17", cxxflags="-Wall"))
        content = "\n".join(lines)
        assert "CMAKE_CXX_FLAGS" in content
        assert "CMAKE_CXX_STD_FLAG" in content
        assert "-Wall" in content
        assert "c++17" in content

    def test_defines_bool_type(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        lines = list(p.generate_cmake_toolchain(defines={"BUILD_SHARED:BOOL": "ON"}))
        content = "\n".join(lines)
        assert "BUILD_SHARED" in content
        assert "BOOL" in content

    def test_defines_auto_detected_bool(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        lines = list(p.generate_cmake_toolchain(defines={"MY_FLAG": "ON"}))
        content = "\n".join(lines)
        assert "MY_FLAG" in content
        assert "BOOL" in content

    def test_empty_defines(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        lines = list(p.generate_cmake_toolchain(defines={}))
        content = "\n".join(lines)
        # Should still produce basic toolchain without errors
        assert "CGET_PREFIX" in content


# ── CGetPrefix.create_builder (additional) ──────────────────────────────────

class TestCreateBuilderAdditional:
    def test_tmp_with_long_name(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        long_name = "a" * 50
        with p.create_builder(long_name, tmp=True) as builder:
            # Should hash to short name
            assert os.path.isdir(builder.top_dir)
            dirname = os.path.basename(builder.top_dir)
            assert dirname.startswith("tmp-")
            # Hashed name should be 12 chars
            assert len(dirname[4:]) == 12

    def test_tmp_with_short_name(self, tmp_path):
        p = CGetPrefix(str(tmp_path / "pfx"))
        with p.create_builder("short", tmp=True) as builder:
            dirname = os.path.basename(builder.top_dir)
            assert dirname == "tmp-short"
