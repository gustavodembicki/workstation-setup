"""Validate that every trusted vendor endpoint is structurally valid and live."""

from __future__ import annotations

import argparse
import shlex
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from workstation_setup.registry.trustlist import TRUSTLIST


class URLResponse(Protocol):
    def getcode(self) -> int | None: ...

    def close(self) -> None: ...


URLOpener = Callable[..., URLResponse]


@dataclass(frozen=True)
class TrustedSource:
    app_id: str
    field: str
    url: str

    @property
    def label(self) -> str:
        return f"{self.app_id}.{self.field}"


@dataclass(frozen=True)
class URLCheck:
    source: TrustedSource
    ok: bool
    detail: str


def _apt_repo_parts(repo_line: str) -> tuple[str, str]:
    """Extract the repository URL and suite from a deb source line."""
    parts = shlex.split(repo_line)
    if not parts or parts[0] != "deb":
        raise ValueError("APT source must start with 'deb'")
    index = 1
    if len(parts) > index and parts[index].startswith("["):
        while index < len(parts) and not parts[index].endswith("]"):
            index += 1
        index += 1
    if len(parts) <= index + 1:
        raise ValueError("APT source is missing its repository URL or suite")
    return parts[index], parts[index + 1]


def _apt_repo_url(repo_line: str) -> str:
    """Extract the repository URL from a deb source line, including options."""
    return _apt_repo_parts(repo_line)[0]


def _apt_release_url(repo_line: str) -> str:
    """Return the small APT metadata document an apt install will actually need."""
    base_url, suite = _apt_repo_parts(repo_line)
    return f"{base_url.rstrip('/')}/dists/{suite}/Release"


def trusted_sources() -> tuple[TrustedSource, ...]:
    """Return the complete auditable set of network endpoints in the trustlist."""
    sources: list[TrustedSource] = []
    for app_id, links in TRUSTLIST.items():
        if links.download_url:
            sources.append(TrustedSource(app_id, "download_url", links.download_url))
        if links.gpg_key_url:
            sources.append(TrustedSource(app_id, "gpg_key_url", links.gpg_key_url))
        if links.apt_repo_line:
            sources.append(
                TrustedSource(app_id, "apt_repo_release", _apt_release_url(links.apt_repo_line))
            )
    return tuple(sources)


def is_secure_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _request(url: str, *, method: str, opener: URLOpener, timeout: float) -> int:
    headers = {"User-Agent": "workstation-setup-url-check"}
    if method == "GET":
        headers["Range"] = "bytes=0-0"
    request = Request(url, method=method, headers=headers)
    response = opener(request, timeout=timeout)
    try:
        return response.getcode() or 0
    finally:
        response.close()


def check_source(
    source: TrustedSource, *, opener: URLOpener = urlopen, timeout: float = 20
) -> URLCheck:
    """Check an endpoint, falling back to GET when HEAD is unsupported."""
    if not is_secure_url(source.url):
        return URLCheck(source, False, "URL must use HTTPS")
    try:
        status = _request(source.url, method="HEAD", opener=opener, timeout=timeout)
    except HTTPError as error:
        if error.code != 405:
            return URLCheck(source, False, f"HTTP {error.code}")
        try:
            status = _request(source.url, method="GET", opener=opener, timeout=timeout)
        except HTTPError as fallback_error:
            return URLCheck(source, False, f"HTTP {fallback_error.code}")
        except URLError as fallback_error:
            return URLCheck(source, False, str(fallback_error.reason))
    except URLError as error:
        return URLCheck(source, False, str(error.reason))
    return URLCheck(source, 200 <= status < 400, f"HTTP {status}")


def check_sources(
    sources: Iterable[TrustedSource] | None = None,
    *,
    opener: URLOpener = urlopen,
    timeout: float = 20,
) -> tuple[URLCheck, ...]:
    return tuple(
        check_source(source, opener=opener, timeout=timeout)
        for source in sources or trusted_sources()
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check trusted application download endpoints.")
    parser.add_argument("--timeout", type=float, default=20, help="per-request timeout in seconds")
    args = parser.parse_args(argv)
    checks = check_sources(timeout=args.timeout)
    for check in checks:
        mark = "OK" if check.ok else "FAIL"
        print(f"{mark:4} {check.source.label}: {check.detail} ({check.source.url})")
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
