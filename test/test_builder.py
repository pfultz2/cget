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
            args = mock_cmake.call_args[1]['args']
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
            args = mock_cmake.call_args[1]['args']
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
            args = mock_cmake.call_args[1]['args']
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
            args = mock_cmake.call_args[1]['args']
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
            args = mock_cmake.call_args[1]['args']
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
            args = mock_cmake.call_args[1]['args']
            assert '--build' in args
            assert b.build_dir in args

    def test_build_with_target(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.build(target="install")
            args = mock_cmake.call_args[1]['args']
            assert '--target' in args
            assert 'install' in args

    def test_build_with_variant(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.build(variant="Debug")
            args = mock_cmake.call_args[1]['args']
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
            args = mock_cmake.call_args[1]['args']
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

    def test_test_default_variant(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)

        with mock.patch.object(b, 'targets', return_value=iter(['check'])):
            with mock.patch.object(b, 'build') as mock_build:
                b.test()
                mock_build.assert_called_once_with(target='check', variant='Release')


# ── fetch ────────────────────────────────────────────────────────────────────

class TestFetch:
    def test_fetch_calls_retrieve_and_extract(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)

        # Create fake extracted directory
        extracted_dir = os.path.join(top, "project-1.0")
        os.makedirs(extracted_dir)

        with mock.patch('cget.util.retrieve_url', return_value=os.path.join(top, "pkg.tar.gz")) as mock_retrieve:
            # Create the archive file so os.path.isfile returns True
            with open(os.path.join(top, "pkg.tar.gz"), 'w') as f:
                f.write("")
            with mock.patch('cget.util.extract_ar') as mock_extract:
                result = b.fetch("https://example.com/pkg.tar.gz")
                mock_retrieve.assert_called_once()
                mock_extract.assert_called_once()
                assert result == extracted_dir

    def test_fetch_with_hash(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)

        extracted_dir = os.path.join(top, "project-1.0")
        os.makedirs(extracted_dir)

        with mock.patch('cget.util.retrieve_url', return_value=os.path.join(top, "pkg.tar.gz")) as mock_retrieve:
            with open(os.path.join(top, "pkg.tar.gz"), 'w') as f:
                f.write("")
            with mock.patch('cget.util.extract_ar'):
                b.fetch("https://example.com/pkg.tar.gz", hash="sha256:abc123")
                call_kwargs = mock_retrieve.call_args
                assert call_kwargs[1].get('hash') == "sha256:abc123" or call_kwargs[0][3] == "sha256:abc123"

    def test_fetch_insecure_replaces_https(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)

        extracted_dir = os.path.join(top, "project-1.0")
        os.makedirs(extracted_dir)

        with mock.patch('cget.util.retrieve_url', return_value=os.path.join(top, "pkg.tar.gz")) as mock_retrieve:
            with open(os.path.join(top, "pkg.tar.gz"), 'w') as f:
                f.write("")
            with mock.patch('cget.util.extract_ar'):
                b.fetch("https://example.com/pkg.tar.gz", insecure=True)
                url_arg = mock_retrieve.call_args[0][0]
                assert url_arg.startswith("http://")

    def test_fetch_with_copy(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)

        extracted_dir = os.path.join(top, "project-1.0")
        os.makedirs(extracted_dir)

        with mock.patch('cget.util.retrieve_url', return_value=os.path.join(top, "pkg.tar.gz")) as mock_retrieve:
            with open(os.path.join(top, "pkg.tar.gz"), 'w') as f:
                f.write("")
            with mock.patch('cget.util.extract_ar'):
                b.fetch("https://example.com/pkg.tar.gz", copy=True)
                assert mock_retrieve.call_args[1].get('copy') is True or mock_retrieve.call_args[0][2] is True

    def test_fetch_directory_result(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)

        # When retrieve returns a directory (not a file), no extraction happens
        src_dir = os.path.join(top, "source")
        os.makedirs(src_dir)

        with mock.patch('cget.util.retrieve_url', return_value=src_dir):
            result = b.fetch("https://example.com/pkg.tar.gz")
            assert result == src_dir


# ── configure (additional) ───────────────────────────────────────────────────

class TestConfigureAdditional:
    def test_configure_test_on(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        src_dir = str(tmp_path / "src")
        os.makedirs(src_dir)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.configure(src_dir, test=True)
            args = mock_cmake.call_args[1]['args']
            assert '-DBUILD_TESTING=On' in args

    def test_configure_default_variant_release(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        src_dir = str(tmp_path / "src")
        os.makedirs(src_dir)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.configure(src_dir)
            args = mock_cmake.call_args[1]['args']
            assert '-DCMAKE_BUILD_TYPE=Release' in args

    def test_configure_verbose_adds_verbose_makefile(self, tmp_path):
        prefix = MockPrefix(str(tmp_path), verbose=True)
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        src_dir = str(tmp_path / "src")
        os.makedirs(src_dir)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.configure(src_dir)
            args = mock_cmake.call_args[1]['args']
            assert '-DCMAKE_VERBOSE_MAKEFILE=On' in args

    def test_configure_cmake_failure_shows_logs(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        src_dir = str(tmp_path / "src")
        os.makedirs(src_dir)

        with mock.patch.object(b, 'cmake', side_effect=util.BuildError("cmake failed")):
            with mock.patch.object(b, 'show_logs') as mock_show:
                with pytest.raises(util.BuildError):
                    b.configure(src_dir)
                mock_show.assert_called_once()

    def test_configure_includes_cget_cmake_dir(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        src_dir = str(tmp_path / "src")
        os.makedirs(src_dir)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.configure(src_dir)
            args = mock_cmake.call_args[1]['args']
            cget_dir_args = [a for a in args if 'CGET_CMAKE_DIR' in a]
            assert len(cget_dir_args) == 1
            original_args = [a for a in args if 'CGET_CMAKE_ORIGINAL_SOURCE_FILE' in a]
            assert len(original_args) == 1


# ── build (additional) ──────────────────────────────────────────────────────

class TestBuildAdditional:
    def test_build_no_makefile_no_parallel(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.build()
            args = mock_cmake.call_args[1]['args']
            assert '-j' not in args
            assert '--' not in args

    def test_build_with_cwd(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.build(cwd="/some/dir")
            assert mock_cmake.call_args[1].get('cwd') == "/some/dir"

    def test_build_verbose_makefile_adds_verbose_flag(self, tmp_path):
        prefix = MockPrefix(str(tmp_path), verbose=True)
        top = str(tmp_path / "top")
        build_dir = os.path.join(top, "build")
        os.makedirs(build_dir)
        with open(os.path.join(build_dir, "Makefile"), "w") as f:
            f.write("")
        b = Builder(prefix, top)

        with mock.patch.object(b, 'cmake') as mock_cmake:
            b.build()
            args = mock_cmake.call_args[1]['args']
            assert 'VERBOSE=1' in args


# ── show_logs (additional) ──────────────────────────────────────────────────

class TestShowLogsAdditional:
    def test_show_logs_with_both_files(self, tmp_path, capsys):
        prefix = MockPrefix(str(tmp_path), verbose=True)
        top = str(tmp_path / "top")
        cmake_files = os.path.join(top, "build", "CMakeFiles")
        os.makedirs(cmake_files)
        with open(os.path.join(cmake_files, "CMakeOutput.log"), "w") as f:
            f.write("output log\n")
        with open(os.path.join(cmake_files, "CMakeError.log"), "w") as f:
            f.write("error log\n")
        b = Builder(prefix, top)
        b.show_logs()
        captured = capsys.readouterr()
        assert "output log" in captured.out
        assert "error log" in captured.out


# ── targets (additional) ────────────────────────────────────────────────────

class TestTargetsAdditional:
    def test_targets_parses_output(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)

        cmake_output = b"... all\n... clean\n... install\nother line\n"
        with mock.patch.object(b, 'cmake', return_value=(cmake_output, None)):
            result = list(b.targets())
            assert b'all' in result
            assert b'clean' in result
            assert b'install' in result
            assert len(result) == 3


# ── get_path / get_build_path (additional) ──────────────────────────────────

class TestPathsAdditional:
    def test_get_path_no_args(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        assert b.get_path() == top

    def test_get_build_path_no_args(self, tmp_path):
        prefix = MockPrefix(str(tmp_path))
        top = str(tmp_path / "top")
        os.makedirs(top)
        b = Builder(prefix, top)
        assert b.get_build_path() == os.path.join(top, "build")
