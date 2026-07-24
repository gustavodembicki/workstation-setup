from urllib.error import HTTPError

from workstation_setup.registry.url_validation import (
    TrustedSource,
    _apt_repo_url,
    check_source,
    trusted_sources,
)


class Response:
    def __init__(self, status=200):
        self.status = status
        self.closed = False

    def getcode(self):
        return self.status

    def close(self):
        self.closed = True


def test_trusted_sources_include_each_network_route():
    sources = trusted_sources()

    assert {source.label for source in sources} >= {
        "chrome.gpg_key_url",
        "chrome.apt_repo_release",
        "slack.download_url",
    }
    assert all(source.url.startswith("https://") for source in sources)


def test_apt_repo_url_supports_deb_options():
    line = "deb [arch=amd64 signed-by=/key.gpg] https://example.com/deb stable main"
    assert _apt_repo_url(line) == "https://example.com/deb"


def test_check_source_uses_head_request_and_closes_response():
    seen = []
    response = Response()

    def opener(request, *, timeout):
        seen.append((request.method, timeout))
        return response

    source = TrustedSource("thing", "download_url", "https://example.com/file")
    result = check_source(source, opener=opener)

    assert result.ok
    assert result.detail == "HTTP 200"
    assert seen == [("HEAD", 20)]
    assert response.closed


def test_check_source_rejects_non_https_without_network_access():
    result = check_source(TrustedSource("thing", "download_url", "http://example.com/file"))

    assert not result.ok
    assert result.detail == "URL must use HTTPS"


def test_check_source_falls_back_to_get_when_head_not_allowed():
    methods = []

    def opener(request, *, timeout):
        methods.append(request.method)
        if request.method == "HEAD":
            raise HTTPError(request.full_url, 405, "method not allowed", {}, None)
        return Response(206)

    source = TrustedSource("thing", "download_url", "https://example.com/file")
    result = check_source(source, opener=opener)

    assert result.ok
    assert methods == ["HEAD", "GET"]
