from workstation_setup import os_detect
from workstation_setup.os_detect import _bucket_distro, _parse_os_release, detect_os


def test_bucket_distro_debian_like():
    assert _bucket_distro({"ID": "ubuntu"}) == "debian"
    assert _bucket_distro({"ID": "debian"}) == "debian"


def test_bucket_distro_fedora_like():
    assert _bucket_distro({"ID": "fedora"}) == "fedora"
    assert _bucket_distro({"ID": "rocky", "ID_LIKE": "rhel centos fedora"}) == "fedora"


def test_bucket_distro_arch_like():
    assert _bucket_distro({"ID": "arch"}) == "arch"
    assert _bucket_distro({"ID": "manjaro", "ID_LIKE": "arch"}) == "arch"


def test_bucket_distro_unknown_falls_back_to_other():
    assert _bucket_distro({"ID": "solus"}) == "other"
    assert _bucket_distro({}) == "other"


def test_parse_os_release():
    text = (
        "\nID=ubuntu\nID_LIKE=debian\n"
        'PRETTY_NAME="Ubuntu 24.04 LTS"\n'
        '# comment\nVERSION_ID="24.04"\n'
    )
    parsed = _parse_os_release(text)
    assert parsed == {
        "ID": "ubuntu",
        "ID_LIKE": "debian",
        "PRETTY_NAME": "Ubuntu 24.04 LTS",
        "VERSION_ID": "24.04",
    }


def test_detect_os_macos(monkeypatch):
    monkeypatch.setattr(os_detect.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(os_detect.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(os_detect.platform, "mac_ver", lambda: ("14.5", ("", "", ""), ""))

    info = detect_os()

    assert info.family == "macos"
    assert info.distro_family is None
    assert info.version == "14.5"
    assert info.arch == "arm64"


def test_detect_os_linux_ubuntu(monkeypatch):
    monkeypatch.setattr(os_detect.platform, "system", lambda: "Linux")
    monkeypatch.setattr(os_detect.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(
        os_detect,
        "_read_os_release",
        lambda: {"ID": "ubuntu", "PRETTY_NAME": "Ubuntu 24.04 LTS", "VERSION_ID": "24.04"},
    )

    info = detect_os()

    assert info.family == "linux"
    assert info.distro_family == "debian"
    assert info.distro_name == "Ubuntu 24.04 LTS"
    assert info.version == "24.04"
    assert info.arch == "x86_64"


def test_detect_os_windows(monkeypatch):
    monkeypatch.setattr(os_detect.platform, "system", lambda: "Windows")
    monkeypatch.setattr(os_detect.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(os_detect.platform, "version", lambda: "10.0.26220")

    info = detect_os()

    assert info.family == "windows"
    assert info.distro_family is None
