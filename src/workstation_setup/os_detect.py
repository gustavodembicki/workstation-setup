from __future__ import annotations

import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

OSFamily = Literal["linux", "macos", "windows"]
DistroFamily = Literal["debian", "fedora", "arch", "other"]

_DEBIAN_LIKE = {"debian", "ubuntu"}
_FEDORA_LIKE = {"fedora", "rhel", "centos"}
_ARCH_LIKE = {"arch", "manjaro"}


@dataclass(frozen=True)
class OSInfo:
    family: OSFamily
    distro_family: DistroFamily | None  # only meaningful when family == "linux"
    distro_name: str | None
    version: str
    arch: str


def _bucket_distro(os_release: dict[str, str]) -> DistroFamily:
    ids = {os_release.get("ID", "")}
    ids.update(os_release.get("ID_LIKE", "").split())

    if ids & _DEBIAN_LIKE:
        return "debian"
    if ids & _FEDORA_LIKE:
        return "fedora"
    if ids & _ARCH_LIKE:
        return "arch"
    return "other"


def _parse_os_release(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip().strip('"')
    return result


def _read_os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
    try:
        return _parse_os_release(path.read_text())
    except OSError:
        return {}


def detect_os() -> OSInfo:
    system = platform.system()
    arch = platform.machine()

    if system == "Darwin":
        return OSInfo(
            family="macos",
            distro_family=None,
            distro_name="macOS",
            version=platform.mac_ver()[0],
            arch=arch,
        )

    if system == "Linux":
        os_release = _read_os_release()
        return OSInfo(
            family="linux",
            distro_family=_bucket_distro(os_release),
            distro_name=os_release.get("PRETTY_NAME") or os_release.get("NAME"),
            version=os_release.get("VERSION_ID", ""),
            arch=arch,
        )

    return OSInfo(
        family="windows",
        distro_family=None,
        distro_name="Windows",
        version=platform.version(),
        arch=arch,
    )
