# 問い合わせ管理システム

公開フォームから受け付けた問い合わせをSQLiteへ保存し、ログインした管理者が一覧で管理できるWebアプリケーションです。

現在のリリースバージョン（最新タグ）は **v0.3.0** です。

## 制作目的

問い合わせの受付と、その後の対応状況の管理を一つのシステムで行いやすくすることを目的としています。

利用者向けの受付画面と管理者向けの画面を分けることで、利用者は迷わず問い合わせを送信でき、管理者は未対応・対応済みの状況を整理できます。

## 主な機能

### 公開フォーム

- ログインせずに問い合わせを登録
- 名前、メールアドレス、問い合わせ内容を入力
- 未入力やメールアドレス形式のエラーを表示
- 登録内容をSQLiteデータベースへ保存

### 管理者ログイン

- 管理者名とパスワードによるログイン
- 未ログイン時の管理画面と管理用APIを保護
- ログアウト
- パスワードは平文ではなくハッシュを使って照合

### 管理画面

- 問い合わせを一覧表示
- 名前、メールアドレス、問い合わせ内容からキーワード検索
- 「未対応」「対応済み」で絞り込み
- 登録日時の新しい順・古い順で並べ替え
- 対応状況を「未対応」と「対応済み」の間で変更
- 不要になった問い合わせを確認後に削除

## 使用技術

| 分類 | 技術 |
| --- | --- |
| バックエンド | Python、Flask |
| データベース | SQLite |
| フロントエンド | HTML、CSS、JavaScript |
| 自動テスト | pytest |

## ローカルでの起動方法

以下は、プロジェクトのフォルダーを開いた状態で実行します。Python 3.10以上を利用してください。

### 1. 仮想環境を作成する

Windows PowerShellの場合：

```powershell
py -m venv .venv
```

`py` が見つからない場合は、インストールされているPythonのコマンド名に読み替えてください。

macOSまたはLinuxの場合：

```bash
python3 -m venv .venv
```

### 2. 必要なパッケージをインストールする

Windows PowerShellの場合：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

macOSまたはLinuxの場合：

```bash
./.venv/bin/python -m pip install -r requirements.txt
```

### 3. `.env` を準備する

まず、`.env.example` を `.env` という名前でコピーします。

Windows PowerShellの場合：

```powershell
Copy-Item .env.example .env
```

macOSまたはLinuxの場合：

```bash
cp .env.example .env
```

作成した `.env` に、次の3項目を自分の環境用として設定します。

| 項目 | 用途 |
| --- | --- |
| `SECRET_KEY` | ログイン状態を安全に保持するためのランダムな値 |
| `ADMIN_USERNAME` | 管理者ログインで使うユーザー名 |
| `ADMIN_PASSWORD_HASH` | 管理者パスワードから生成したハッシュ |

`SECRET_KEY` 用のランダムな値は、次のコマンドで生成できます。

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

管理者パスワードのハッシュは、次のコマンドで生成できます。入力したパスワード自体は画面やコマンド履歴に表示されません。

```powershell
.\.venv\Scripts\python.exe -c "from getpass import getpass; from werkzeug.security import generate_password_hash; print(generate_password_hash(getpass('管理者パスワード: ')))"
```

各コマンドの出力を対応する項目へ設定してください。実際の値はREADME、チャット、ソースコードへ貼り付けないでください。`ADMIN_PASSWORD_HASH` に平文のパスワードを設定しないでください。

macOSまたはLinuxでは、コマンド先頭の `.\.venv\Scripts\python.exe` を `./.venv/bin/python` に読み替えます。

### 4. アプリを起動する

Windows PowerShellの場合：

```powershell
.\.venv\Scripts\python.exe app.py
```

macOSまたはLinuxの場合：

```bash
./.venv/bin/python app.py
```

起動後、ブラウザーで次のローカルURLを開きます。

- 公開フォーム: `http://127.0.0.1:5000/`
- 管理者ログイン: `http://127.0.0.1:5000/admin/login`
- 管理画面: `http://127.0.0.1:5000/admin`

終了するときは、アプリを実行しているターミナルで `Ctrl + C` を押します。

## 自動テスト

公開フォーム、入力エラー、管理者認証、APIのアクセス制御、ログイン後の一覧取得・状態変更・削除を確認する **16件の自動テスト** があります。

テストでは一時データベースとテスト専用の認証設定を使うため、実際の `.env` や `instance/inquiries.db` は使用しません。

Windows PowerShellの場合：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

macOSまたはLinuxの場合：

```bash
./.venv/bin/python -m pytest -q
```

すべて成功すると、結果に `16 passed` と表示されます。

## 秘密情報をGitへ登録しないための注意

- `.env`、APIキー、秘密鍵、パスワード、実際のパスワードハッシュをGitへ登録しないでください。
- `.env.example` には項目名や説明だけを残し、実際の値を記載しないでください。
- `.env` と `instance/` は `.gitignore` の対象ですが、コミット前に `git status` で対象ファイルを必ず確認してください。
- `.env` を `git add -f` などで強制的に追加しないでください。
- 将来AI用のAPIキーを追加する場合も、ソースコードへ直接書かず `.env` などで安全に管理してください。

## 今後の追加候補

次の機能は、現時点では未実装です。

- AIによる問い合わせ返信案の作成
- オンライン環境への公開
