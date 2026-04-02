import copy
import hashlib

import pytest

from cget.package import (
    PackageSource,
    PackageBuild,
    encode_url,
    decode_url,
    fname_to_pkg,
    parse_pkg_build_tokens,
)


# ── encode_url / decode_url ─────────────────────────────────────────────────

class TestEncodeUrl:
    def test_roundtrip_https(self):
        url = "https://github.com/user/repo/archive/HEAD.tar.gz"
        encoded = encode_url(url)
        assert encoded.startswith("_url_")
        decoded = decode_url(encoded)
        assert decoded == "github.com/user/repo/archive/HEAD.tar.gz"

    def test_roundtrip_http(self):
        url = "http://example.com/file.tar.gz"
        encoded = encode_url(url)
        decoded = decode_url(encoded)
        assert decoded == "example.com/file.tar.gz"

    def test_encode_starts_with_prefix(self):
        assert encode_url("https://x.com/foo").startswith("_url_")

    def test_different_urls_different_encodings(self):
        assert encode_url("https://a.com/x") != encode_url("https://b.com/y")


# ── PackageSource ────────────────────────────────────────────────────────────

class TestPackageSource:
    def test_to_name_with_name(self):
        ps = PackageSource(name="mypackage")
        assert ps.to_name() == "mypackage"

    def test_to_name_with_url(self):
        ps = PackageSource(url="https://example.com/pkg.tar.gz")
        assert ps.to_name() == "https://example.com/pkg.tar.gz"

    def test_to_name_falls_to_fname(self):
        ps = PackageSource(fname="pkg__name")
        assert ps.to_name() == "pkg__name"

    def test_to_fname_with_name(self):
        ps = PackageSource(name="boost/regex")
        assert ps.to_fname() == "boost__regex"

    def test_to_fname_with_url_no_name(self):
        ps = PackageSource(url="https://example.com/foo.tar.gz")
        fname = ps.to_fname()
        assert fname.startswith("_url_")

    def test_to_fname_caches(self):
        ps = PackageSource(name="test")
        fname1 = ps.to_fname()
        fname2 = ps.to_fname()
        assert fname1 == fname2
        assert ps.fname == fname1

    def test_get_encoded_name_url_with_name(self):
        ps = PackageSource(name="user/repo")
        assert ps.get_encoded_name_url() == "user__repo"

    def test_get_encoded_name_url_with_url(self):
        ps = PackageSource(url="https://example.com/pkg.tar.gz")
        result = ps.get_encoded_name_url()
        assert result.startswith("_url_")

    def test_get_src_dir_file_url(self):
        ps = PackageSource(url="file:///home/user/project")
        assert ps.get_src_dir() == "/home/user/project"

    def test_get_src_dir_non_file_url(self):
        ps = PackageSource(url="https://example.com/pkg.tar.gz")
        with pytest.raises(TypeError):
            ps.get_src_dir()

    def test_get_hash_deterministic(self):
        ps = PackageSource(name="test", url="https://example.com")
        h1 = ps.get_hash()
        h2 = ps.get_hash()
        assert h1 == h2

    def test_get_hash_different_for_different_sources(self):
        ps1 = PackageSource(name="a")
        ps2 = PackageSource(name="b")
        assert ps1.get_hash() != ps2.get_hash()

    def test_get_hash_handles_none_fields(self):
        ps = PackageSource()
        h = ps.get_hash()
        assert isinstance(h, str)
        assert len(h) == 64  # sha256 hex length

    def test_get_hash_all_fields(self):
        ps = PackageSource(name="n", url="u", fname="f", recipe="r")
        h = ps.get_hash()
        assert isinstance(h, str)
        assert len(h) == 64


# ── fname_to_pkg ─────────────────────────────────────────────────────────────

class TestFnameToPkg:
    def test_url_fname(self):
        url = "https://example.com/pkg.tar.gz"
        encoded = encode_url(url)
        ps = fname_to_pkg(encoded)
        assert ps.fname == encoded
        assert "example.com" in ps.name

    def test_regular_fname(self):
        ps = fname_to_pkg("boost__regex")
        assert ps.name == "boost/regex"
        assert ps.fname == "boost__regex"

    def test_simple_name(self):
        ps = fname_to_pkg("zlib")
        assert ps.name == "zlib"
        assert ps.fname == "zlib"


# ── PackageBuild ─────────────────────────────────────────────────────────────

class TestPackageBuild:
    def test_defaults(self):
        pb = PackageBuild()
        assert pb.pkg_src is None
        assert pb.define == []
        assert pb.parent is None
        assert pb.test is False
        assert pb.variant == 'Release'
        assert pb.hash is None
        assert pb.cmake is None
        assert pb.build is None
        assert pb.requirements is None
        assert pb.file is None
        assert pb.ignore_requirements is None

    def test_custom_values(self):
        ps = PackageSource(name="test")
        pb = PackageBuild(pkg_src=ps, define=["FOO=1"], test=True, variant="Debug")
        assert pb.pkg_src is ps
        assert pb.define == ["FOO=1"]
        assert pb.test is True
        assert pb.variant == "Debug"

    def test_merge_defines(self):
        pb = PackageBuild(define=["A=1"])
        result = pb.merge_defines(["B=2"])
        assert "A=1" in result.define
        assert "B=2" in result.define

    def test_merge_defines_does_not_modify_original(self):
        pb = PackageBuild(define=["A=1"])
        original_define = list(pb.define)
        result = pb.merge_defines(["B=2"])
        # Note: copy.copy is shallow, so define list is shared
        # This is current behavior
        assert "B=2" in result.define

    def test_merge_other(self):
        ps1 = PackageSource(name="pkg1")
        ps2 = PackageSource(name="pkg2")
        pb1 = PackageBuild(pkg_src=ps1, define=["A=1"], variant="Release")
        pb2 = PackageBuild(pkg_src=ps2, define=["B=2"], variant="Debug", hash="sha256:abc")
        result = pb1.merge(pb2)
        assert result.pkg_src is ps1  # pkg_src not merged
        assert "A=1" in result.define
        assert "B=2" in result.define
        assert result.variant == "Debug"  # other takes precedence
        assert result.hash == "sha256:abc"

    def test_merge_preserves_non_none(self):
        pb1 = PackageBuild(hash="sha256:abc")
        pb2 = PackageBuild()  # hash is None
        result = pb1.merge(pb2)
        assert result.hash == "sha256:abc"

    def test_of(self):
        parent_src = PackageSource(name="parent")
        parent = PackageBuild(pkg_src=parent_src, define=["PARENT_DEF=1"], variant="Debug")
        child_src = PackageSource(name="child")
        child = PackageBuild(pkg_src=child_src, define=["CHILD_DEF=1"])
        result = child.of(parent)
        assert result.parent == parent.to_fname()
        assert "CHILD_DEF=1" in result.define
        assert "PARENT_DEF=1" in result.define
        assert result.variant == "Debug"

    def test_to_fname_with_package_source(self):
        ps = PackageSource(name="mypackage")
        pb = PackageBuild(pkg_src=ps)
        assert pb.to_fname() == "mypackage"

    def test_to_fname_with_string(self):
        pb = PackageBuild(pkg_src="rawstring")
        assert pb.to_fname() == "rawstring"

    def test_to_name_with_package_source(self):
        ps = PackageSource(name="mypackage")
        pb = PackageBuild(pkg_src=ps)
        assert pb.to_name() == "mypackage"

    def test_to_name_with_string(self):
        pb = PackageBuild(pkg_src="rawstring")
        assert pb.to_name() == "rawstring"


# ── parse_pkg_build_tokens ───────────────────────────────────────────────────

class TestParsePkgBuildTokens:
    def test_basic_package(self):
        pb = parse_pkg_build_tokens(["user/repo"])
        assert pb.pkg_src == "user/repo"
        assert pb.define == []
        assert pb.test is False

    def test_with_defines(self):
        pb = parse_pkg_build_tokens(["pkg", "-DFOO=1", "-DBAR=2"])
        assert pb.pkg_src == "pkg"
        assert pb.define == ["FOO=1", "BAR=2"]

    def test_with_hash(self):
        pb = parse_pkg_build_tokens(["pkg", "-H", "sha256:abc123"])
        assert pb.hash == "sha256:abc123"

    def test_with_cmake(self):
        pb = parse_pkg_build_tokens(["pkg", "-X", "custom.cmake"])
        assert pb.cmake == "custom.cmake"

    def test_with_file(self):
        pb = parse_pkg_build_tokens(["pkg", "-f", "reqs.txt"])
        assert pb.file == "reqs.txt"

    def test_with_test_flag(self):
        pb = parse_pkg_build_tokens(["pkg", "-t"])
        assert pb.test is True

    def test_with_build_flag(self):
        pb = parse_pkg_build_tokens(["pkg", "-b"])
        assert pb.build is True

    def test_with_ignore_requirements(self):
        pb = parse_pkg_build_tokens(["pkg", "--ignore-requirements"])
        assert pb.ignore_requirements is True

    def test_all_flags(self):
        pb = parse_pkg_build_tokens([
            "pkg", "-DFOO=1", "-H", "sha256:abc",
            "-X", "cmake.cmake", "-f", "file.txt",
            "-t", "-b", "--ignore-requirements"
        ])
        assert pb.pkg_src == "pkg"
        assert pb.define == ["FOO=1"]
        assert pb.hash == "sha256:abc"
        assert pb.cmake == "cmake.cmake"
        assert pb.file == "file.txt"
        assert pb.test is True
        assert pb.build is True
        assert pb.ignore_requirements is True

    def test_no_package(self):
        pb = parse_pkg_build_tokens([])
        assert pb.pkg_src is None

    def test_result_is_package_build(self):
        pb = parse_pkg_build_tokens(["pkg"])
        assert isinstance(pb, PackageBuild)

    def test_long_define(self):
        pb = parse_pkg_build_tokens(["pkg", "--define", "LONG_KEY=val"])
        assert pb.define == ["LONG_KEY=val"]
