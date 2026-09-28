import pytest
import requests

import line_notifier
from line_notifier import LineNotifyError, MessageTooLongError, send_message


class FakeResponse:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "dummy-token")
    monkeypatch.setenv("LINE_USER_ID", "U-default")


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(line_notifier.time, "sleep", lambda _: None)


@pytest.fixture
def post(monkeypatch):
    """requests.post を差し替え、呼び出し内容を記録しつつ用意した応答を順に返す"""
    calls = []
    responses = []

    def fake_post(url, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json})
        r = responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(line_notifier.requests, "post", fake_post)
    return calls, responses


def test_送信成功_既定の宛先とトークンを使う(env, post):
    calls, responses = post
    responses.append(FakeResponse(200))

    send_message("こんにちは")

    assert len(calls) == 1
    assert calls[0]["url"] == line_notifier.PUSH_URL
    assert calls[0]["headers"]["Authorization"] == "Bearer dummy-token"
    assert calls[0]["json"] == {
        "to": "U-default",
        "messages": [{"type": "text", "text": "こんにちは"}],
    }


def test_宛先とトークンを引数で上書きできる(env, post):
    calls, responses = post
    responses.append(FakeResponse(200))

    send_message("hi", to="C-group", token="other-token")

    assert calls[0]["json"]["to"] == "C-group"
    assert calls[0]["headers"]["Authorization"] == "Bearer other-token"


def test_ちょうど5000文字は送れる(env, post):
    calls, responses = post
    responses.append(FakeResponse(200))

    send_message("あ" * 5000)

    assert len(calls) == 1


def test_5000文字を超えると送信せずエラー(env, post):
    calls, _ = post

    with pytest.raises(MessageTooLongError):
        send_message("あ" * 5001)

    assert calls == []


def test_空メッセージはエラー(env, post):
    with pytest.raises(LineNotifyError):
        send_message("")


def test_環境変数がなければエラー(monkeypatch, post):
    monkeypatch.delenv("LINE_CHANNEL_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("LINE_USER_ID", raising=False)

    with pytest.raises(LineNotifyError, match="LINE_CHANNEL_ACCESS_TOKEN"):
        send_message("hi")


def test_import時に環境変数がなくても落ちない(monkeypatch):
    # reload するとテスト中の例外クラスが差し替わるので、別プロセスで確かめる
    import subprocess
    import sys

    monkeypatch.delenv("LINE_CHANNEL_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("LINE_USER_ID", raising=False)
    subprocess.run([sys.executable, "-c", "import line_notifier"], check=True)


def test_一時的なエラーは再送して成功する(env, post):
    calls, responses = post
    responses.extend([
        FakeResponse(500),
        requests.ConnectionError("boom"),
        FakeResponse(200),
    ])

    send_message("hi", retries=2)

    assert len(calls) == 3


def test_再送しても失敗したらエラー(env, post):
    calls, responses = post
    responses.extend([FakeResponse(429)] * 3)

    with pytest.raises(LineNotifyError, match="429"):
        send_message("hi", retries=2)

    assert len(calls) == 3


def test_400系は再送せず即エラー(env, post):
    calls, responses = post
    responses.append(FakeResponse(401, "invalid token"))

    with pytest.raises(LineNotifyError, match="401 invalid token"):
        send_message("hi")

    assert len(calls) == 1
