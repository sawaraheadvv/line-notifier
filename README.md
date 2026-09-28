# line-notifier

LINE Messaging API でテキストメッセージを送る共通ライブラリ。

## インストール

各アプリの `requirements.txt` に追加する（タグで版を固定する）。

```
line-notifier @ git+https://github.com/sawaraheadvv/line-notifier@v1.0.0
```

## 使い方

```python
from line_notifier import send_message, LineNotifyError

send_message("通知したい内容")                 # 既定の宛先（LINE_USER_ID）へ
send_message("グループへの通知", to="C1234...")  # 宛先を指定
```

### 必要な環境変数

| 変数 | 内容 |
|---|---|
| `LINE_CHANNEL_ACCESS_TOKEN` | チャネルアクセストークン（`token=` 引数でも指定可） |
| `LINE_USER_ID` | 既定の送信先（`to=` 引数でも指定可） |

GitHub Actions では Secrets に登録して `env:` で渡す。ローカルで `.env` を使う場合は、アプリ側で `python-dotenv` の `load_dotenv()` を呼ぶ（このライブラリは `.env` を読まない）。

## 挙動

- 成功したら `None` を返す。失敗したら `LineNotifyError` を送出する（ジョブが失敗として記録され、監視で検知できるようにするため）。
- 本文が5000文字を超える場合は、分割せず `MessageTooLongError` を送出する。
- 429・5xx・通信エラーは再送する（既定2回、1秒→2秒待つ）。それ以外（401など）は即エラー。

## 開発

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[test]"
.venv/bin/pytest
```
