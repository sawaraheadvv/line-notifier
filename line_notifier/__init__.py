"""LINE Messaging API でテキストメッセージを送る共通ライブラリ"""
from __future__ import annotations

import os
import time
from typing import Optional

import requests

__all__ = [
    "send_message",
    "LineNotifyError",
    "MessageTooLongError",
    "MAX_TEXT_LENGTH",
]

PUSH_URL = "https://api.line.me/v2/bot/message/push"

# LINE のテキストメッセージ1通あたりの上限。超えたら分割せずエラーにする
MAX_TEXT_LENGTH = 5000

# 再送しても意味がありうるステータス（レート制限・サーバー側の一時的な不調）
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class LineNotifyError(Exception):
    """LINE への送信に失敗した"""


class MessageTooLongError(LineNotifyError, ValueError):
    """メッセージが MAX_TEXT_LENGTH を超えている"""


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise LineNotifyError(f"環境変数 {name} が設定されていません")
    return value


def send_message(
    text: str,
    to: Optional[str] = None,
    *,
    token: Optional[str] = None,
    retries: int = 2,
    timeout: float = 10.0,
) -> None:
    """LINE にテキストメッセージを送信する。失敗したら LineNotifyError を送出する。

    Args:
        text: 送信する本文（空文字・5000文字超はエラー）
        to: 送信先のユーザーID／グループID。省略時は環境変数 LINE_USER_ID
        token: チャネルアクセストークン。省略時は環境変数 LINE_CHANNEL_ACCESS_TOKEN
        retries: 一時的なエラー（429・5xx・通信エラー）のときに再送する回数
        timeout: 1回のリクエストのタイムアウト秒数
    """
    if not text:
        raise LineNotifyError("送信するメッセージが空です")
    if len(text) > MAX_TEXT_LENGTH:
        raise MessageTooLongError(
            f"メッセージが長すぎます（{len(text)}文字 > 上限{MAX_TEXT_LENGTH}文字）"
        )

    token = token or _require_env("LINE_CHANNEL_ACCESS_TOKEN")
    to = to or _require_env("LINE_USER_ID")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = {"to": to, "messages": [{"type": "text", "text": text}]}

    last_error = ""
    for attempt in range(retries + 1):
        if attempt > 0:
            time.sleep(2 ** (attempt - 1))  # 1秒, 2秒, 4秒...

        try:
            resp = requests.post(PUSH_URL, headers=headers, json=payload, timeout=timeout)
        except requests.RequestException as e:
            last_error = f"通信エラー: {e}"
            continue

        if resp.status_code == 200:
            print("LINE送信成功")
            return

        last_error = f"{resp.status_code} {resp.text}"
        if resp.status_code not in RETRYABLE_STATUS:
            break

    raise LineNotifyError(f"LINE送信失敗: {last_error}")
