import os
import shutil
from unittest import mock

import pytest

from cget.builder import Builder
import cget.util as util


class MockPrefix:
    """Lightweight stand-in for CGetPrefix used by Builder tests."""
    def __init__(self, prefix_dir, verbose=False):
        self.prefix = prefix_dir
        self.verbose = verbose
        self.toolchain = os.path.join(prefix_dir, "cget", "cget.cmake")
        self.cmd = util.Commander(paths=[os.path.join(prefix_dir, "bin")], verbose=verbose)

    def log(self, *args):
        pass


# ── Builder construction ─────────────────────────────────────────────────────

class TestBuilderInit:
    def test_basic_init(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "build_top")
        os.makedirs(top)
        b = Builder(prefix, top)
        assert b.prefix is prefix
        assert b.top_dir == top
        assert b.build_dir == os.path.join(top, "build")
        assert b.exists is False
        assert b.cmake_original_file == '__cget_original_cmake_file__.cmake'

    def test_exists_flag(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "build_top")
        os.makedirs(top)
        b = Builder(prefix, top, exists=True)
        assert b.exists is True


# ── path helpers ─────────────────────────────────────────────────────────────

class TestBuilderPaths:
    def test_get_path(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        assert b.get_path("foo") == os.path.join(top, "foo")
        assert b.get_path("a", "b") == os.path.join(top, "a", "b")

    def test_get_build_path(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        assert b.get_build_path("CMakeCache.txt") == os.path.join(top, "build", "CMakeCache.txt")


# ── is_make_generator ────────────────────────────────────────────────────────

class TestIsMakeGenerator:
    def test_true_when_makefile_exists(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        build_dir = os.path.join(top, "build")
        os.makedirs(build_dir)
        # Create a Makefile
        with open(os.path.join(build_dir, "Makefile"), "w") as f:
            f.write("")
        b = Builder(prefix, top)
        assert b.is_make_generator() is True

    def test_false_when_no_makefile(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        assert b.is_make_generator() is False


# ── show_log / show_logs ─────────────────────────────────────────────────────

class TestShowLogs:
    def test_show_log_verbose_with_file(self, tmp_path, capsys):
        prefix = MockPrefix(str(tmp_path), verbose=True)
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        log_file = os.path.join(top, "test.log")
        with open(log_file, "w") as f:
            f.write("log content\n")
        b.show_log(log_file)
        captured = capsys.readouterr()
        assert "log content" in captured.out

    def test_show_log_not_verbose(self, tmp_path, capsys):
        prefix = MockPrefix(str(tmp_path), verbose=False)
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        log_file = os.path.join(top, "test.log")
        with open(log_file, "w") as f:
            f.write("log content\n")
        b.show_log(log_file)
        captured = capsys.readouterr()
        assert "log content" not in captured.out

    def test_show_log_nonexistent_file(self, tmp_path, capsys):
        prefix = MockPrefix(str(tmp_path), verbose=True)
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        b.show_log("/nonexistent/file.log")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_show_logs_creates_log_paths(self, tmp_path):
        prefix = MockPrefix(str(tmp_path), verbose=True)
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        # Should not raise even with no log files
        b.show_logs()


# ── targets ──────────────────────────────────────────────────────────────────

class TestTargets:
    def test_targets_empty_on_failure(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        # cmake --build will fail since there's no build dir, targets should be empty
        result = list(b.targets())
        assert result == []


# ── cmake method ─────────────────────────────────────────────────────────────

class TestCmake:
    def test_cmake_without_toolchain(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        with mock.patch.object(prefix.cmd, 'cmake') as mock_cmake:
            b.cmake(options={'-DFOO': 'bar'})
            mock_cmake.assert_called_once_with(options={'-DFOO': 'bar'})

    def test_cmake_with_toolchain(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        with mock.patch.object(prefix.cmd, 'cmake') as mock_cmake:
            b.cmake(options={'-DFOO': 'bar'}, use_toolchain=True)
            call_kwargs = mock_cmake.call_args
            opts = call_kwargs[1]['options'] if 'options' in call_kwargs[1] else call_kwargs[0][0]
            assert '-DCMAKE_TOOLCHAIN_FILE' in opts


# ── configure ────────────────────────────────────────────────────────────────

class TestConfigure:
    def test_configure_creates_build_dir(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        src_dir = str(tmp_path / "src")
        os.makedirs(src_dir)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.configure(src_dir)
            assert os.path.isdir(b.build_dir)
            mock_cmake.assert_called_once()
            call_kwargs = mock_cmake.call_args
            args = call_kwargs[1].get('args', call_kwargs[0][0] if call_kwargs[0] else [])
            # Should contain src_dir
            assert src_dir in args

    def test_configure_with_defines(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        src_dir = str(tmp_path / "src")
        os.makedirs(src_dir)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.configure(src_dir, defines=["FOO=1", "BAR=2"])
            args = mock_cmake.call_args.kwargs['args']
            assert '-DFOO=1' in args
            assert '-DBAR=2' in args

    def test_configure_with_generator(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        src_dir = str(tmp_path / "src")
        os.makedirs(src_dir)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.configure(src_dir, generator="Ninja")
            args = mock_cmake.call_args.kwargs['args']
            assert '-G' in args
            idx = args.index('-G')
            assert args[idx + 1] == "Ninja"

    def test_configure_with_install_prefix(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        src_dir = str(tmp_path / "src")
        os.makedirs(src_dir)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.configure(src_dir, install_prefix="/install/here")
            args = mock_cmake.call_args.kwargs['args']
            assert '-DCMAKE_INSTALL_PREFIX=/install/here' in args

    def test_configure_test_off(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        src_dir = str(tmp_path / "src")
        os.makedirs(src_dir)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.configure(src_dir, test=False)
            args = mock_cmake.call_args.kwargs['args']
            assert '-DBUILD_TESTING=Off' in args

    def test_configure_with_variant(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        src_dir = str(tmp_path / "src")
        os.makedirs(src_dir)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.configure(src_dir, variant="Debug")
            args = mock_cmake.call_args.kwargs['args']
            assert '-DCMAKE_BUILD_TYPE=Debug' in args


# ── build ────────────────────────────────────────────────────────────────────

class TestBuild:
    def test_build_basic(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.build()
            args = mock_cmake.call_args.kwargs['args']
            assert '--build' in args
            assert b.build_dir in args

    def test_build_with_target(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.build(target="install")
            args = mock_cmake.call_args.kwargs['args']
            assert '--target' in args
            assert 'install' in args

    def test_build_with_variant(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.build(variant="Debug")
            args = mock_cmake.call_args.kwargs['args']
            assert '--config' in args
            assert 'Debug' in args

    def test_build_with_makefile_adds_parallel(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        build_dir = os.path.join(top, "build")
        os.makedirs(build_dir)
        with open(os.path.join(build_dir, "Makefile"), "w") as f:
            f.write("")
        b = Builder(prefix, top)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.build()
            args = mock_cmake.call_args.kwargs['args']
            assert '-j' in args


# ── test method ──────────────────────────────────────────────────────────────

class TestBuilderTest:
    def test_test_with_check_target(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)

        with mock.patch.object(b, 'targets', return_value=iter(['check'])):
            with mock.patch.object(b, 'build') as mock_build:
                b.test(variant='Release')
                mock_build.assert_called_once_with(target='check', variant='Release')

    def test_test_without_check_target(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)

        with mock.patch.object(b, 'targets', return_value=iter([])):
            with mock.patch.object(prefix.cmd, 'ctest') as mock_ctest:
                b.test(variant='Release')
                mock_ctest.assert_called_once()
