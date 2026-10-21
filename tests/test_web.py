"""The web page must bind to loopback and take the password in a POST body only."""
import json
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer

import pytest

from taala import web
from taala.blocklist import get_full_blocklist
from taala import pack


@pytest.fixture(scope="module")
def server():
    srv = HTTPServer(("127.0.0.1", 0), web.TaalaHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()
    srv.server_close()


def _post(url, body):
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(req)


def test_post_check_returns_band(server):
    data = json.load(_post(server + "/check", json.dumps({"pwd": "pyaar123"}).encode()))
    assert data["band"] in ("Weak", "Fair", "Strong")


def test_get_check_is_gone(server):
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(server + "/check?pwd=secret")
    assert e.value.code == 404


@pytest.mark.parametrize("body", [b"not json", b"{}", json.dumps({"pwd": "x" * 100}).encode()])
def test_bad_bodies_are_400(server, body):
    with pytest.raises(urllib.error.HTTPError) as e:
        _post(server + "/check", body)
    assert e.value.code == 400


def test_binds_loopback_only():
    import inspect
    assert '"127.0.0.1"' in inspect.getsource(web.main)
    assert "0.0.0.0" not in inspect.getsource(web.main)


def test_blocklist_is_cached_and_follows_configure():
    a = get_full_blocklist()
    assert get_full_blocklist() is a
    pack.configure()
    assert get_full_blocklist() is not a
