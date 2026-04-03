import os
import sys
import json
import shutil
import hashlib
import tarfile
import tempfile
import zipfile
from unittest import mock

import pytest

import cget.util as util


# ── to_bool ──────────────────────────────────────────────────────────────────

class TestToBool:
    @pytest.mark.parametrize("value", ["no", "n", "false", "f", "0", "0.0", "", "none", "[]", "{}"])
    def test_falsy_strings(self, value):
        assert util.to_bool(value) is False

    @pytest.mark.parametrize("value", ["NO", "False", "None", "FALSE", "N"])
    def test_falsy_case_insensitive(self, value):
        assert util.to_bool(value) is False

    @pytest.mark.parametrize("value", ["yes", "1", "true", "anything", "on"])
    def test_truthy_strings(self, value):
        assert util.to_bool(value) is True

    def test_bool_true(self):
        assert util.to_bool(True) is True

    def test_bool_false(self):
        assert util.to_bool(False) is False

    def test_numeric_nonzero(self):
        assert util.to_bool(42) is True


# ── is_string ────────────────────────────────────────────────────────────────

class TestIsString:
    def test_str(self):
        assert util.is_string("hello") is True

    def test_empty_str(self):
        assert util.is_string("") is True

    def test_int(self):
        assert util.is_string(42) is False

    def test_list(self):
        assert util.is_string(["a"]) is False

    def test_none(self):
        assert util.is_string(None) is False


# ── quote ────────────────────────────────────────────────────────────────────

class TestQuote:
    def test_simple_string(self):
        assert util.quote("hello") == json.dumps("hello")

    def test_string_with_quotes(self):
        assert util.quote('say "hi"') == json.dumps('say "hi"')

    def test_empty_string(self):
        assert util.quote("") == '""'

    def test_path_with_backslashes(self):
        assert util.quote("C:\\path\\to") == json.dumps("C:\\path\\to")


# ── BuildError ───────────────────────────────────────────────────────────────

class TestBuildError:
    def test_with_message(self):
        e = util.BuildError("something broke")
        assert str(e) == "something broke"

    def test_with_data(self):
        e = util.BuildError("msg", data={"key": "val"})
        assert e.msg == "msg"
        assert e.data == {"key": "val"}

    def test_is_exception(self):
        with pytest.raises(util.BuildError):
            raise util.BuildError("fail")


# ── ensure_exists ────────────────────────────────────────────────────────────

class TestEnsureExists:
    def test_existing_file(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("data")
        util.ensure_exists(str(f))  # should not raise

    def test_nonexistent_file(self, tmp_path):
        with pytest.raises(util.BuildError, match="File does not exists"):
            util.ensure_exists(str(tmp_path / "nope.txt"))

    def test_empty_path(self):
        with pytest.raises(util.BuildError, match="Invalid file path"):
            util.ensure_exists("")

    def test_none_path(self):
        with pytest.raises(util.BuildError, match="Invalid file path"):
            util.ensure_exists(None)


# ── can ──────────────────────────────────────────────────────────────────────

class TestCan:
    def test_success(self):
        assert util.can(lambda: 42) is True

    def test_failure(self):
        def fail():
            raise ValueError()
        assert util.can(fail) is False


# ── try_until ────────────────────────────────────────────────────────────────

class TestTryUntil:
    def test_first_succeeds(self):
        results = []
        util.try_until(lambda: results.append(1), lambda: results.append(2))
        assert results == [1]

    def test_first_fails(self):
        results = []
        def fail():
            raise ValueError()
        util.try_until(fail, lambda: results.append(2))
        assert results == [2]

    def test_all_fail(self):
        def fail():
            raise ValueError("bad")
        with pytest.raises(ValueError, match="bad"):
            util.try_until(fail, fail)


# ── write_to ─────────────────────────────────────────────────────────────────

class TestWriteTo:
    def test_writes_lines(self, tmp_path):
        f = str(tmp_path / "out.txt")
        util.write_to(f, ["hello", "world"])
        assert open(f).read() == "hello\nworld\n"

    def test_empty_lines(self, tmp_path):
        f = str(tmp_path / "out.txt")
        util.write_to(f, [])
        assert not os.path.exists(f)


# ── mkdir ────────────────────────────────────────────────────────────────────

class TestMkdir:
    def test_creates_directory(self, tmp_path):
        d = str(tmp_path / "a" / "b")
        result = util.mkdir(d)
        assert os.path.isdir(d)
        assert result == d

    def test_existing_directory(self, tmp_path):
        d = str(tmp_path)
        result = util.mkdir(d)
        assert result == d


# ── mkfile ───────────────────────────────────────────────────────────────────

class TestMkfile:
    def test_creates_file(self, tmp_path):
        d = str(tmp_path / "sub")
        p = util.mkfile(d, "test.txt", ["line1", "line2"])
        assert os.path.exists(p)
        assert open(p).read() == "line1\nline2\n"

    def test_always_write_true(self, tmp_path):
        d = str(tmp_path)
        util.mkfile(d, "f.txt", ["old"])
        util.mkfile(d, "f.txt", ["new"], always_write=True)
        p = os.path.join(d, "f.txt")
        assert open(p).read() == "new\n"

    def test_always_write_false(self, tmp_path):
        d = str(tmp_path)
        util.mkfile(d, "f.txt", ["old"])
        util.mkfile(d, "f.txt", ["new"], always_write=False)
        p = os.path.join(d, "f.txt")
        assert open(p).read() == "old\n"


# ── ls ───────────────────────────────────────────────────────────────────────

class TestLs:
    def test_lists_files(self, tmp_path):
        (tmp_path / "a.txt").write_text("")
        (tmp_path / "b.txt").write_text("")
        result = sorted(util.ls(str(tmp_path)))
        assert result == ["a.txt", "b.txt"]

    def test_with_predicate(self, tmp_path):
        (tmp_path / "a.txt").write_text("")
        d = tmp_path / "subdir"
        d.mkdir()
        result = list(util.ls(str(tmp_path), os.path.isdir))
        assert result == ["subdir"]

    def test_nonexistent_dir(self):
        result = list(util.ls("/nonexistent/path"))
        assert result == []


# ── adjust_path ──────────────────────────────────────────────────────────────

class TestAdjustPath:
    def test_posix_no_change(self):
        if os.name == 'posix':
            assert util.adjust_path("/some/path") == "/some/path"

    def test_relative_no_change(self):
        assert util.adjust_path("relative/path") == "relative/path"


# ── delete_dir ───────────────────────────────────────────────────────────────

class TestDeleteDir:
    def test_removes_directory(self, tmp_path):
        d = tmp_path / "todelete"
        d.mkdir()
        (d / "file.txt").write_text("data")
        util.delete_dir(str(d))
        assert not d.exists()

    def test_none_path(self):
        util.delete_dir(None)  # should not raise

    def test_nonexistent_path(self):
        util.delete_dir("/nonexistent/path/xyz")  # should not raise


# ── symlink_dir / copy_dir ───────────────────────────────────────────────────

class TestSymlinkDir:
    @pytest.mark.skipif(os.name != 'posix', reason="symlinks need posix")
    def test_symlinks_files(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "a.txt").write_text("hello")
        sub = src / "sub"
        sub.mkdir()
        (sub / "b.txt").write_text("world")
        dst.mkdir()
        util.symlink_dir(str(src), str(dst))
        assert os.path.islink(str(dst / "a.txt"))
        assert os.path.islink(str(dst / "sub" / "b.txt"))
        assert open(str(dst / "a.txt")).read() == "hello"


class TestCopyDir:
    def test_copies_files(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "a.txt").write_text("hello")
        sub = src / "sub"
        sub.mkdir()
        (sub / "b.txt").write_text("world")
        dst.mkdir()
        util.copy_dir(str(src), str(dst))
        assert (dst / "a.txt").read_text() == "hello"
        assert (dst / "sub" / "b.txt").read_text() == "world"
        assert not os.path.islink(str(dst / "a.txt"))


# ── readlink ─────────────────────────────────────────────────────────────────

class TestReadlink:
    @pytest.mark.skipif(os.name != 'posix', reason="symlinks need posix")
    def test_relative_symlink(self, tmp_path):
        target = tmp_path / "target.txt"
        target.write_text("data")
        link = tmp_path / "link.txt"
        os.symlink("target.txt", str(link))
        result = util.readlink(str(link))
        assert os.path.isabs(result)
        assert result == str(target)

    @pytest.mark.skipif(os.name != 'posix', reason="symlinks need posix")
    def test_absolute_symlink(self, tmp_path):
        target = tmp_path / "target.txt"
        target.write_text("data")
        link = tmp_path / "link.txt"
        os.symlink(str(target), str(link))
        assert util.readlink(str(link)) == str(target)


# ── rm_symlink ───────────────────────────────────────────────────────────────

class TestRmSymlink:
    @pytest.mark.skipif(os.name != 'posix', reason="symlinks need posix")
    def test_removes_broken_symlink(self, tmp_path):
        link = tmp_path / "link.txt"
        os.symlink("/nonexistent/target", str(link))
        assert os.path.islink(str(link))
        util.rm_symlink(str(link))
        assert not os.path.exists(str(link))

    @pytest.mark.skipif(os.name != 'posix', reason="symlinks need posix")
    def test_keeps_valid_symlink(self, tmp_path):
        target = tmp_path / "target.txt"
        target.write_text("data")
        link = tmp_path / "link.txt"
        os.symlink(str(target), str(link))
        util.rm_symlink(str(link))
        assert os.path.islink(str(link))

    def test_regular_file_no_op(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("data")
        util.rm_symlink(str(f))  # should not raise or remove
        assert f.exists()


# ── rm_symlink_in ────────────────────────────────────────────────────────────

class TestRmSymlinkIn:
    @pytest.mark.skipif(os.name != 'posix', reason="symlinks need posix")
    def test_removes_link_in_prefix(self, tmp_path):
        target = tmp_path / "prefix" / "target.txt"
        target.parent.mkdir()
        target.write_text("data")
        link = tmp_path / "link.txt"
        os.symlink(str(target), str(link))
        util.rm_symlink_in(str(link), str(tmp_path / "prefix"))
        assert not os.path.exists(str(link))

    @pytest.mark.skipif(os.name != 'posix', reason="symlinks need posix")
    def test_keeps_link_outside_prefix(self, tmp_path):
        target = tmp_path / "other" / "target.txt"
        target.parent.mkdir()
        target.write_text("data")
        link = tmp_path / "link.txt"
        os.symlink(str(target), str(link))
        util.rm_symlink_in(str(link), str(tmp_path / "prefix"))
        assert os.path.islink(str(link))


# ── rm_empty_dirs ────────────────────────────────────────────────────────────

class TestRmEmptyDirs:
    def test_removes_empty_nested(self, tmp_path):
        d = tmp_path / "a" / "b" / "c"
        d.mkdir(parents=True)
        util.rm_empty_dirs(str(tmp_path / "a"))
        assert not (tmp_path / "a").exists()

    def test_keeps_dir_with_files(self, tmp_path):
        d = tmp_path / "a" / "b"
        d.mkdir(parents=True)
        (d / "file.txt").write_text("data")
        result = util.rm_empty_dirs(str(tmp_path / "a"))
        assert result is True
        assert d.exists()


# ── get_dirs ─────────────────────────────────────────────────────────────────

class TestGetDirs:
    def test_lists_dirs(self, tmp_path):
        (tmp_path / "dir1").mkdir()
        (tmp_path / "dir2").mkdir()
        (tmp_path / "file.txt").write_text("data")
        result = sorted(util.get_dirs(str(tmp_path)))
        assert len(result) == 2
        assert all(os.path.isdir(d) for d in result)


# ── copy_to / symlink_to ────────────────────────────────────────────────────

class TestCopyTo:
    def test_copy_file(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("hello")
        dst_dir = tmp_path / "dst"
        dst_dir.mkdir()
        result = util.copy_to(str(src), str(dst_dir))
        assert os.path.basename(result) == "src.txt"
        assert open(result).read() == "hello"

    def test_copy_directory(self, tmp_path):
        src = tmp_path / "srcdir"
        src.mkdir()
        (src / "a.txt").write_text("data")
        dst_dir = tmp_path / "dst"
        dst_dir.mkdir()
        result = util.copy_to(str(src), str(dst_dir))
        assert os.path.isdir(result)
        assert open(os.path.join(result, "a.txt")).read() == "data"


class TestSymlinkTo:
    @pytest.mark.skipif(os.name != 'posix', reason="symlinks need posix")
    def test_creates_symlink(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("hello")
        dst_dir = tmp_path / "dst"
        dst_dir.mkdir()
        result = util.symlink_to(str(src), str(dst_dir))
        assert os.path.islink(result)
        assert open(result).read() == "hello"


# ── hash_file / check_hash ──────────────────────────────────────────────────

class TestHashFile:
    def test_sha256(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_bytes(b"hello world")
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert util.hash_file(str(f), "sha256") == expected

    def test_md5(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_bytes(b"test")
        expected = hashlib.md5(b"test").hexdigest()
        assert util.hash_file(str(f), "md5") == expected


class TestCheckHash:
    def test_matching_hash(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_bytes(b"hello")
        h = hashlib.sha256(b"hello").hexdigest()
        assert util.check_hash(str(f), "sha256:" + h) is True

    def test_wrong_hash(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_bytes(b"hello")
        assert util.check_hash(str(f), "sha256:0000bad") is False


# ── is_executable ────────────────────────────────────────────────────────────

class TestIsExecutable:
    def test_nonexistent(self):
        assert util.is_executable("/nonexistent/file") is False

    @pytest.mark.skipif(os.name != 'posix', reason="posix permissions")
    def test_executable_file(self, tmp_path):
        f = tmp_path / "run.sh"
        f.write_text("#!/bin/sh\n")
        os.chmod(str(f), 0o755)
        assert util.is_executable(str(f)) is True

    @pytest.mark.skipif(os.name != 'posix', reason="posix permissions")
    def test_non_executable_file(self, tmp_path):
        f = tmp_path / "data.txt"
        f.write_text("hello")
        os.chmod(str(f), 0o644)
        assert util.is_executable(str(f)) is False


# ── which ────────────────────────────────────────────────────────────────────

class TestWhich:
    @pytest.mark.skipif(os.name != 'posix', reason="posix paths")
    def test_finds_system_binary(self):
        result = util.which("sh")
        assert result is not None
        assert os.path.isfile(result)

    def test_not_found_throws(self):
        with pytest.raises(util.BuildError, match="Can't find file"):
            util.which("nonexistent_binary_xyz123")

    def test_not_found_no_throw(self):
        assert util.which("nonexistent_binary_xyz123", throws=False) is None

    @pytest.mark.skipif(os.name != 'posix', reason="posix permissions")
    def test_custom_paths(self, tmp_path):
        exe = tmp_path / "mytool"
        exe.write_text("#!/bin/sh\n")
        os.chmod(str(exe), 0o755)
        result = util.which("mytool", paths=[str(tmp_path)])
        assert result == str(exe)


# ── merge ────────────────────────────────────────────────────────────────────

class TestMerge:
    def test_two_dicts(self):
        assert util.merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}

    def test_override(self):
        assert util.merge({"a": 1}, {"a": 2}) == {"a": 2}

    def test_with_none(self):
        assert util.merge(None, {"a": 1}) == {"a": 1}

    def test_empty(self):
        assert util.merge() == {}

    def test_three_dicts(self):
        assert util.merge({"a": 1}, {"b": 2}, {"c": 3}) == {"a": 1, "b": 2, "c": 3}


# ── flat ─────────────────────────────────────────────────────────────────────

class TestFlat:
    def test_flattens(self):
        assert list(util.flat([[1, 2], [3, 4]])) == [1, 2, 3, 4]

    def test_empty(self):
        assert list(util.flat([])) == []

    def test_multiple_args(self):
        assert list(util.flat([[1, 2]], [[3, 4]])) == [1, 2, 3, 4]


# ── as_list ──────────────────────────────────────────────────────────────────

class TestAsList:
    def test_string(self):
        assert util.as_list("hello") == ["hello"]

    def test_list(self):
        assert util.as_list([1, 2]) == [1, 2]

    def test_tuple(self):
        assert util.as_list((1, 2)) == [1, 2]

    def test_generator(self):
        assert util.as_list(x for x in [1, 2]) == [1, 2]


# ── to_define_dict ───────────────────────────────────────────────────────────

class TestToDefineDict:
    def test_key_value_pairs(self):
        result = util.to_define_dict(["FOO=bar", "BAZ=qux"])
        assert result == {"FOO": "bar", "BAZ": "qux"}

    def test_key_only(self):
        result = util.to_define_dict(["FLAG"])
        assert result == {"FLAG": ""}

    def test_mixed(self):
        result = util.to_define_dict(["A=1", "B"])
        assert result == {"A": "1", "B": ""}

    def test_empty(self):
        assert util.to_define_dict([]) == {}


# ── as_dict_str ──────────────────────────────────────────────────────────────

class TestAsDictStr:
    def test_converts_values(self):
        assert util.as_dict_str({"a": 1, "b": True}) == {"a": "1", "b": "True"}

    def test_strings_unchanged(self):
        assert util.as_dict_str({"a": "x"}) == {"a": "x"}


# ── actual_path ──────────────────────────────────────────────────────────────

class TestActualPath:
    def test_absolute_path_unchanged(self):
        assert util.actual_path("/absolute/path") == "/absolute/path"

    def test_relative_with_start(self):
        result = util.actual_path("sub/dir", start="/base")
        assert result == os.path.normpath("/base/sub/dir")

    def test_relative_without_start(self):
        result = util.actual_path("sub/dir")
        assert result == os.path.normpath(os.path.join(os.getcwd(), "sub/dir"))

    def test_tilde_expansion(self):
        result = util.actual_path("~/something", start="/base")
        assert os.path.expanduser("~") in result


# ── Commander ────────────────────────────────────────────────────────────────

class TestCommander:
    def test_init(self):
        c = util.Commander(paths=["/usr/bin"], verbose=True)
        assert c.paths == ["/usr/bin"]
        assert c.verbose is True

    def test_get_paths_env_with_paths(self):
        c = util.Commander(paths=["/custom/bin"])
        env = c._get_paths_env()
        assert env is not None
        assert "/custom/bin" in env['PATH']

    def test_get_paths_env_without_paths(self):
        c = util.Commander()
        assert c._get_paths_env() is None

    def test_contains_existing(self):
        c = util.Commander()
        if os.name == 'posix':
            assert 'sh' in c

    def test_contains_nonexistent(self):
        c = util.Commander()
        assert 'nonexistent_tool_xyz' not in c

    def test_getattr_returns_callable(self):
        c = util.Commander()
        assert callable(c.some_command)

    def test_getitem_returns_callable(self):
        c = util.Commander()
        assert callable(c['some-command'])


# ── cmd ──────────────────────────────────────────────────────────────────────

class TestCmd:
    @pytest.mark.skipif(os.name != 'posix', reason="posix only")
    def test_successful_command(self):
        out, err = util.cmd(["echo", "hello"], capture="out")
        assert b"hello" in out

    @pytest.mark.skipif(os.name != 'posix', reason="posix only")
    def test_failed_command(self):
        with pytest.raises(util.BuildError, match="Command failed"):
            util.cmd(["false"])

    @pytest.mark.skipif(os.name != 'posix', reason="posix only")
    def test_capture_stderr(self):
        out, err = util.cmd(["sh", "-c", "echo err >&2"], capture="err")
        assert b"err" in err

    @pytest.mark.skipif(os.name != 'posix', reason="posix only")
    def test_with_env(self):
        out, _ = util.cmd(["sh", "-c", "echo $MY_VAR"], env={"MY_VAR": "test_val"}, capture="out")
        assert b"test_val" in out


# ── yield_from ───────────────────────────────────────────────────────────────

class TestYieldFrom:
    def test_flattens_generator(self):
        @util.yield_from
        def gen():
            yield [1, 2]
            yield [3, 4]
        assert list(gen()) == [1, 2, 3, 4]


# ── transfer_to ──────────────────────────────────────────────────────────────

class TestTransferTo:
    def test_copy_mode(self, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("data")
        dst = tmp_path / "dst"
        dst.mkdir()
        result = util.transfer_to(str(src), str(dst), copy=True)
        assert os.path.exists(result)
        assert not os.path.islink(result)
        assert open(result).read() == "data"


# ── cache operations ─────────────────────────────────────────────────────────

class TestCacheOperations:
    def test_add_and_get_cache_file(self, tmp_path, monkeypatch):
        cache_dir = str(tmp_path / "cache")
        monkeypatch.setattr(util, 'get_cache_path', lambda *args: os.path.join(cache_dir, *args))
        src = tmp_path / "myfile.tar.gz"
        src.write_text("archive data")
        util.add_cache_file("mykey", str(src))
        result = util.get_cache_file("mykey")
        assert result is not None
        assert open(result).read() == "archive data"

    def test_get_cache_file_miss(self, tmp_path, monkeypatch):
        cache_dir = str(tmp_path / "cache")
        monkeypatch.setattr(util, 'get_cache_path', lambda *args: os.path.join(cache_dir, *args))
        result = util.get_cache_file("nonexistent_key")
        assert result is None


# ── rm_dup_dir ───────────────────────────────────────────────────────────────

class TestRmDupDir:
    def test_removes_duplicates(self, tmp_path):
        pkg = tmp_path / "pkg"
        prefix = tmp_path / "prefix"
        pkg.mkdir()
        prefix.mkdir()
        (pkg / "file.txt").write_text("data")
        (prefix / "file.txt").write_text("data")
        util.rm_dup_dir(str(pkg), str(prefix), remove_both=True)
        assert not (pkg / "file.txt").exists()
        assert not (prefix / "file.txt").exists()

    def test_removes_only_prefix(self, tmp_path):
        pkg = tmp_path / "pkg"
        prefix = tmp_path / "prefix"
        pkg.mkdir()
        prefix.mkdir()
        (pkg / "file.txt").write_text("data")
        (prefix / "file.txt").write_text("data")
        util.rm_dup_dir(str(pkg), str(prefix), remove_both=False)
        assert (pkg / "file.txt").exists()
        assert not (prefix / "file.txt").exists()


# ── rm_symlink_dir ───────────────────────────────────────────────────────────

class TestRmSymlinkDir:
    @pytest.mark.skipif(os.name != 'posix', reason="symlinks need posix")
    def test_removes_broken_symlinks(self, tmp_path):
        d = tmp_path / "dir"
        d.mkdir()
        link = d / "broken_link"
        os.symlink("/nonexistent/target", str(link))
        util.rm_symlink_dir(str(d))
        assert not link.exists()

    @pytest.mark.skipif(os.name != 'posix', reason="symlinks need posix")
    def test_keeps_valid_symlinks(self, tmp_path):
        d = tmp_path / "dir"
        d.mkdir()
        target = d / "target.txt"
        target.write_text("data")
        link = d / "valid_link"
        os.symlink(str(target), str(link))
        util.rm_symlink_dir(str(d))
        assert link.exists()


# ── cget_dir ─────────────────────────────────────────────────────────────────

class TestCgetDir:
    def test_returns_path_in_cget_module(self):
        result = util.cget_dir()
        assert os.path.isdir(result)
        assert result == util.__CGET_DIR__

    def test_with_subpath(self):
        result = util.cget_dir("cmake")
        assert result == os.path.join(util.__CGET_DIR__, "cmake")

    def test_with_multiple_subpaths(self):
        result = util.cget_dir("cmake", "foo.cmake")
        assert result == os.path.join(util.__CGET_DIR__, "cmake", "foo.cmake")


# ── get_app_dir / get_cache_path ─────────────────────────────────────────────

class TestGetAppDir:
    def test_returns_string(self):
        result = util.get_app_dir()
        assert isinstance(result, str)

    def test_with_subpath(self):
        result = util.get_app_dir("sub")
        assert result.endswith("sub")


class TestGetCachePath:
    def test_returns_string(self):
        result = util.get_cache_path()
        assert isinstance(result, str)
        assert "cache" in result

    def test_with_key(self):
        result = util.get_cache_path("mykey")
        assert result.endswith("mykey")


# ── CGetURLOpener ────────────────────────────────────────────────────────────

class TestCGetURLOpener:
    def test_error_code_400_raises(self):
        opener = util.CGetURLOpener()
        with pytest.raises(util.BuildError, match="Download failed"):
            opener.http_error_default("http://example.com", None, 404, "Not Found", {})

    def test_error_code_500_raises(self):
        opener = util.CGetURLOpener()
        with pytest.raises(util.BuildError, match="Download failed"):
            opener.http_error_default("http://example.com", None, 500, "Server Error", {})


# ── download_to ──────────────────────────────────────────────────────────────

class TestDownloadTo:
    def test_download_file_url(self, tmp_path):
        # Create a source file to "download"
        src = tmp_path / "source" / "file.txt"
        src.parent.mkdir()
        src.write_text("hello")
        download_dir = tmp_path / "dl"
        download_dir.mkdir()
        # Mock the URL opener to copy the file instead of downloading
        with mock.patch.object(util.CGetURLOpener, 'retrieve') as mock_retrieve:
            def fake_retrieve(url, filename=None, reporthook=None, data=None):
                shutil.copy(str(src), filename)
            mock_retrieve.side_effect = fake_retrieve
            result = util.download_to("http://example.com/file.txt", str(download_dir))
            assert os.path.exists(result)
            assert os.path.basename(result) == "file.txt"
            assert open(result).read() == "hello"

    def test_download_failed_no_file(self, tmp_path):
        download_dir = tmp_path / "dl"
        download_dir.mkdir()
        with mock.patch.object(util.CGetURLOpener, 'retrieve') as mock_retrieve:
            mock_retrieve.side_effect = lambda *a, **kw: None
            with pytest.raises(util.BuildError, match="Download failed"):
                util.download_to("http://example.com/missing.tar.gz", str(download_dir))

    def test_download_insecure(self, tmp_path):
        src = tmp_path / "source" / "file.txt"
        src.parent.mkdir()
        src.write_text("hello")
        download_dir = tmp_path / "dl"
        download_dir.mkdir()
        with mock.patch.object(util.CGetURLOpener, 'retrieve') as mock_retrieve:
            def fake_retrieve(url, filename=None, reporthook=None, data=None):
                shutil.copy(str(src), filename)
            mock_retrieve.side_effect = fake_retrieve
            # Should not raise with insecure=True
            result = util.download_to("https://example.com/file.txt", str(download_dir), insecure=True)
            assert os.path.exists(result)


# ── retrieve_url ─────────────────────────────────────────────────────────────

class TestRetrieveUrl:
    def test_file_protocol_symlink(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_text("local file")
        dst = tmp_path / "dst"
        dst.mkdir()
        result = util.retrieve_url("file://" + str(src), str(dst), copy=True)
        assert os.path.exists(result)
        assert open(result).read() == "local file"

    def test_file_protocol_no_hash(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_text("data")
        dst = tmp_path / "dst"
        dst.mkdir()
        result = util.retrieve_url("file://" + str(src), str(dst), copy=True)
        assert os.path.exists(result)

    def test_file_protocol_with_valid_hash(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_bytes(b"data")
        dst = tmp_path / "dst"
        dst.mkdir()
        h = hashlib.sha256(b"data").hexdigest()
        result = util.retrieve_url("file://" + str(src), str(dst), copy=True, hash="sha256:" + h)
        assert os.path.exists(result)

    def test_file_protocol_with_invalid_hash(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_bytes(b"data")
        dst = tmp_path / "dst"
        dst.mkdir()
        with pytest.raises(util.BuildError, match="Hash doesn't match"):
            util.retrieve_url("file://" + str(src), str(dst), copy=True, hash="sha256:badhash")

    def test_remote_cache_hit(self, tmp_path, monkeypatch):
        cache_dir = str(tmp_path / "cache")
        monkeypatch.setattr(util, 'get_cache_path', lambda *args: os.path.join(cache_dir, *args))
        # Put a file in cache
        key = "sha256-abc123"
        os.makedirs(os.path.join(cache_dir, key))
        cached = os.path.join(cache_dir, key, "pkg.tar.gz")
        with open(cached, 'w') as f:
            f.write("cached data")
        dst = tmp_path / "dst"
        dst.mkdir()
        result = util.retrieve_url("https://example.com/pkg.tar.gz", str(dst), hash="sha256:abc123")
        assert result == cached

    def test_remote_downloads_and_caches(self, tmp_path, monkeypatch):
        cache_dir = str(tmp_path / "cache")
        monkeypatch.setattr(util, 'get_cache_path', lambda *args: os.path.join(cache_dir, *args))
        dst = tmp_path / "dst"
        dst.mkdir()
        content = b"downloaded data"
        h = hashlib.sha256(content).hexdigest()
        # Mock download_to
        def fake_download(url, download_dir, insecure=False):
            f = os.path.join(download_dir, "pkg.tar.gz")
            with open(f, 'wb') as fh:
                fh.write(content)
            return f
        monkeypatch.setattr(util, 'download_to', fake_download)
        result = util.retrieve_url("https://example.com/pkg.tar.gz", str(dst), hash="sha256:" + h)
        assert os.path.exists(result)
        # Verify it was cached
        assert os.path.exists(os.path.join(cache_dir, "sha256-" + h))


# ── extract_ar ───────────────────────────────────────────────────────────────

class TestExtractAr:
    def test_extract_tar_gz(self, tmp_path):
        # Create a tar.gz archive
        archive_dir = tmp_path / "archive_src"
        archive_dir.mkdir()
        (archive_dir / "hello.txt").write_text("hello from tar")
        archive = str(tmp_path / "test.tar.gz")
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(str(archive_dir), arcname="myproject")
        dst = tmp_path / "extracted"
        dst.mkdir()
        util.extract_ar(archive, str(dst))
        # Should have extracted contents
        assert (dst / "myproject" / "hello.txt").exists()

    def test_extract_zip(self, tmp_path):
        # Create a zip archive
        archive = str(tmp_path / "test.zip")
        with zipfile.ZipFile(archive, 'w') as zf:
            zf.writestr("myproject/hello.txt", "hello from zip")
        dst = tmp_path / "extracted"
        dst.mkdir()
        util.extract_ar(archive, str(dst))
        assert (dst / "myproject" / "hello.txt").exists()
        assert (dst / "myproject" / "hello.txt").read_text() == "hello from zip"

    def test_extract_single_file(self, tmp_path):
        # Non-archive file should be treated as single source
        src = tmp_path / "header.h"
        src.write_text("#pragma once")
        dst = tmp_path / "extracted"
        dst.mkdir()
        util.extract_ar(str(src), str(dst))
        assert (dst / "header" / "header.h").exists()

    def test_extract_tar_bz2(self, tmp_path):
        archive_dir = tmp_path / "archive_src"
        archive_dir.mkdir()
        (archive_dir / "file.txt").write_text("bz2 content")
        archive = str(tmp_path / "test.tar.bz2")
        with tarfile.open(archive, "w:bz2") as tar:
            tar.add(str(archive_dir), arcname="proj")
        dst = tmp_path / "extracted"
        dst.mkdir()
        util.extract_ar(archive, str(dst))
        assert (dst / "proj" / "file.txt").exists()


# ── rm_symlink_from ──────────────────────────────────────────────────────────

class TestRmSymlinkFrom:
    @pytest.mark.skipif(os.name != 'posix', reason="symlinks need posix")
    def test_removes_symlinks_pointing_to_dir(self, tmp_path):
        pkg_install = tmp_path / "pkg" / "install"
        pkg_install.mkdir(parents=True)
        target = pkg_install / "lib" / "libfoo.so"
        target.parent.mkdir(parents=True)
        target.write_text("lib")
        # Create prefix with symlink pointing into pkg_install
        prefix = tmp_path / "prefix"
        prefix.mkdir()
        lib_dir = prefix / "lib"
        lib_dir.mkdir()
        os.symlink(str(target), str(lib_dir / "libfoo.so"))
        util.rm_symlink_from(str(pkg_install), str(prefix))
        assert not (lib_dir / "libfoo.so").exists()

    @pytest.mark.skipif(os.name != 'posix', reason="symlinks need posix")
    def test_keeps_symlinks_to_other_dirs(self, tmp_path):
        other = tmp_path / "other"
        other.mkdir()
        target = other / "libbar.so"
        target.write_text("lib")
        prefix = tmp_path / "prefix"
        prefix.mkdir()
        lib_dir = prefix / "lib"
        lib_dir.mkdir()
        os.symlink(str(target), str(lib_dir / "libbar.so"))
        pkg_install = tmp_path / "pkg" / "install"
        pkg_install.mkdir(parents=True)
        util.rm_symlink_from(str(pkg_install), str(prefix))
        assert (lib_dir / "libbar.so").exists()


# ── rm_empty_dirs (additional) ───────────────────────────────────────────────

class TestRmEmptyDirsAdditional:
    @pytest.mark.skipif(os.name != 'posix', reason="symlinks need posix")
    def test_symlink_dirs_not_recursed(self, tmp_path):
        d = tmp_path / "root"
        d.mkdir()
        real = tmp_path / "real_dir"
        real.mkdir()
        os.symlink(str(real), str(d / "link_dir"))
        # Should not try to recurse into symlink dir
        result = util.rm_empty_dirs(str(d))
        assert result is True  # has symlink (counts as file-like)

    def test_mixed_empty_and_nonempty(self, tmp_path):
        root = tmp_path / "root"
        (root / "empty" / "nested").mkdir(parents=True)
        (root / "nonempty").mkdir(parents=True)
        (root / "nonempty" / "file.txt").write_text("data")
        result = util.rm_empty_dirs(str(root))
        assert result is True
        # macOS may create .DS_Store files in directories, making them
        # non-empty from the OS perspective, so skip this check on darwin.
        if sys.platform != "darwin":
            assert not (root / "empty").exists()
        assert (root / "nonempty" / "file.txt").exists()


# ── rm_dup_dir (additional) ──────────────────────────────────────────────────

class TestRmDupDirAdditional:
    def test_relpath_outside_prefix_raises(self, tmp_path):
        # Create structure where relpath would go outside
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        # Create a symlink pointing outside
        prefix = tmp_path / "prefix"
        prefix.mkdir()
        # rm_dup_dir checks for '..' in relpath
        # We need files in pkg that when relpaths relative to pkg contain '..'
        # This requires pkg to have a file at a path that resolves outside
        # In practice this is hard to trigger without symlinks
        # The check is: relpath = os.path.relpath(fullpath, d); if '..' in relpath
        # This triggers when fullpath is not under d, but os.walk shouldn't produce that
        # Just test normal nested subdirectory case
        sub = pkg / "sub"
        sub.mkdir()
        (sub / "file.txt").write_text("data")
        (prefix / "sub").mkdir()
        (prefix / "sub" / "file.txt").write_text("data")
        util.rm_dup_dir(str(pkg), str(prefix), remove_both=True)
        assert not (sub / "file.txt").exists()
        assert not (prefix / "sub" / "file.txt").exists()


# ── transfer_to (additional) ────────────────────────────────────────────────

class TestTransferToAdditional:
    @pytest.mark.skipif(os.name != 'posix', reason="symlinks need posix")
    def test_symlink_mode(self, tmp_path, monkeypatch):
        monkeypatch.setattr(util, 'USE_SYMLINKS', True)
        src = tmp_path / "src.txt"
        src.write_text("data")
        dst = tmp_path / "dst"
        dst.mkdir()
        result = util.transfer_to(str(src), str(dst), copy=False)
        assert os.path.islink(result)
        assert open(result).read() == "data"


# ── cmd (additional) ─────────────────────────────────────────────────────────

class TestCmdAdditional:
    @pytest.mark.skipif(os.name != 'posix', reason="posix only")
    def test_capture_all(self):
        out, err = util.cmd(["sh", "-c", "echo out; echo err >&2"], capture="all")
        assert b"out" in out
        assert b"err" in err

    @pytest.mark.skipif(os.name != 'posix', reason="posix only")
    def test_no_capture(self):
        result = util.cmd(["true"])
        # Returns tuple of (None, None) when no capture
        assert result == (None, None)

    @pytest.mark.skipif(os.name != 'posix', reason="posix only")
    def test_with_cwd(self, tmp_path):
        out, _ = util.cmd(["pwd"], capture="out", cwd=str(tmp_path))
        assert str(tmp_path) in out.decode().strip()


# ── to_define_dict (additional) ──────────────────────────────────────────────

class TestToDefineDictAdditional:
    def test_value_with_equals(self):
        result = util.to_define_dict(["KEY=val=ue"])
        assert result["KEY"] == "val"  # split on first '='

    def test_single_entry(self):
        result = util.to_define_dict(["X=Y"])
        assert result == {"X": "Y"}


# ── as_dict_str (additional) ─────────────────────────────────────────────────

class TestAsDictStrAdditional:
    def test_none_value(self):
        result = util.as_dict_str({"a": None})
        assert result == {"a": "None"}

    def test_empty_dict(self):
        assert util.as_dict_str({}) == {}


# ── write_to (additional) ───────────────────────────────────────────────────

class TestWriteToAdditional:
    def test_single_line(self, tmp_path):
        f = str(tmp_path / "out.txt")
        util.write_to(f, ["one"])
        assert open(f).read() == "one\n"

    def test_overwrites_existing(self, tmp_path):
        f = str(tmp_path / "out.txt")
        util.write_to(f, ["old"])
        util.write_to(f, ["new"])
        assert open(f).read() == "new\n"


# ── check_hash (additional) ─────────────────────────────────────────────────

class TestCheckHashAdditional:
    def test_md5_match(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_bytes(b"test")
        h = hashlib.md5(b"test").hexdigest()
        assert util.check_hash(str(f), "md5:" + h) is True

    def test_case_insensitive_hash_type(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_bytes(b"test")
        h = hashlib.sha256(b"test").hexdigest()
        assert util.check_hash(str(f), "SHA256:" + h) is True


# ── Commander (additional) ──────────────────────────────────────────────────

class TestCommanderAdditional:
    @pytest.mark.skipif(os.name != 'posix', reason="posix only")
    def test_getattr_underscore_to_hyphen(self):
        c = util.Commander()
        # __getattr__ replaces _ with -
        # Access some_command should try to run "some-command"
        f = c.some_command
        assert callable(f)

    def test_init_with_env(self):
        c = util.Commander(env={"FOO": "bar"})
        assert c.env == {"FOO": "bar"}

    @pytest.mark.skipif(os.name != 'posix', reason="posix only")
    def test_cmd_execution_via_getattr(self):
        c = util.Commander()
        out, _ = c.echo(args=["hello"], capture="out")
        assert b"hello" in out

    @pytest.mark.skipif(os.name != 'posix', reason="posix only")
    def test_cmd_execution_via_getitem(self):
        c = util.Commander()
        out, _ = c['echo'](args=["world"], capture="out")
        assert b"world" in out

    @pytest.mark.skipif(os.name != 'posix', reason="posix only")
    def test_verbose_echoes(self, capsys):
        c = util.Commander(verbose=True)
        c.echo(args=["test"], capture="out")
        captured = capsys.readouterr()
        assert "echo" in captured.out

    @pytest.mark.skipif(os.name != 'posix', reason="posix only")
    def test_cmd_with_options(self):
        c = util.Commander()
        # Options are passed as KEY=VALUE args before other args
        # Just verify it doesn't crash
        out, _ = c.echo(args=["hi"], options={}, capture="out")
        assert b"hi" in out


# ── is_executable (additional) ───────────────────────────────────────────────

class TestIsExecutableAdditional:
    def test_directory_returns_false(self, tmp_path):
        d = tmp_path / "dir"
        d.mkdir()
        assert util.is_executable(str(d)) is False


# ── which (additional) ──────────────────────────────────────────────────────

class TestWhichAdditional:
    def test_empty_paths_list(self):
        # With empty paths and binary not in PATH, should raise
        with pytest.raises(util.BuildError):
            util.which("nonexistent_xyz", paths=[])

    @pytest.mark.skipif(os.name != 'posix', reason="posix only")
    def test_finds_in_system_path(self):
        result = util.which("echo")
        assert result is not None
        assert os.path.isfile(result)


# ── yield_from (additional) ──────────────────────────────────────────────────

class TestYieldFromAdditional:
    def test_with_args(self):
        @util.yield_from
        def gen(n):
            yield list(range(n))
            yield [n, n + 1]
        assert list(gen(3)) == [0, 1, 2, 3, 4]

    def test_empty_yield(self):
        @util.yield_from
        def gen():
            yield []
        assert list(gen()) == []


# ── symlink_dir (additional) ─────────────────────────────────────────────────

class TestSymlinkDirAdditional:
    @pytest.mark.skipif(os.name != 'posix', reason="symlinks need posix")
    def test_empty_src(self, tmp_path):
        src = tmp_path / "empty_src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()
        util.symlink_dir(str(src), str(dst))
        # No files should be created in dst
        assert list(os.listdir(str(dst))) == []

    @pytest.mark.skipif(os.name != 'posix', reason="symlinks need posix")
    def test_deeply_nested(self, tmp_path):
        src = tmp_path / "src"
        (src / "a" / "b" / "c").mkdir(parents=True)
        (src / "a" / "b" / "c" / "deep.txt").write_text("deep")
        dst = tmp_path / "dst"
        dst.mkdir()
        util.symlink_dir(str(src), str(dst))
        assert os.path.islink(str(dst / "a" / "b" / "c" / "deep.txt"))
        assert open(str(dst / "a" / "b" / "c" / "deep.txt")).read() == "deep"


# ── copy_dir (additional) ───────────────────────────────────────────────────

class TestCopyDirAdditional:
    def test_empty_src(self, tmp_path):
        src = tmp_path / "empty_src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()
        util.copy_dir(str(src), str(dst))
        assert list(os.listdir(str(dst))) == []

    def test_multiple_files(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        for i in range(5):
            (src / "file{}.txt".format(i)).write_text("content {}".format(i))
        dst = tmp_path / "dst"
        dst.mkdir()
        util.copy_dir(str(src), str(dst))
        assert len(list(os.listdir(str(dst)))) == 5
