# Yarn Switch

Yarnは[Yarn Switch](https://v6.yarnpkg.com/concepts/switch)で導入します。Node.js 25以降はcorepackが梱包されず、Yarn公式もYarn Switchを推奨しているため、`corepack enable` は使用しません。[macos-infra](https://github.com/mitsuharu/macos-infra)と同じ方針です。

## 導入される内容

`yarn-switch` モジュール（全体実行ではanyenvの直後、Safe Chainの前）は、公式インストーラー（`https://repo.yarnpkg.com/install`）を一時ディレクトリにダウンロードしてから `bash` で実行します。`curl | bash` にはせず、ダウンロードに失敗した場合は実行しません。既定のdry-runでは予定を表示するだけで、ダウンロードも設定変更もしません。

- Yarn Switch本体を `~/.yarn/switch/bin/yarn` に配置します。公式インストーラーは常に最新の安定版を取得するため、バージョンとハッシュは固定していません。
- 公式インストーラーは `~/.yarn/switch/env` を作成し、`~/.bashrc` / `~/.zshrc`（fishがあれば `~/.config/fish/config.fish`）の末尾に読み込み行を追記します。既に追記済みなら変更しません。`ZDOTDIR` は参照しません。
- 変更前のシェル設定は通常のバックアップ先の `yarn-switch/` 以下に保存します。シンボリックリンクはリンク自体をバックアップし、独立したコピーに置き換えてからインストーラーを実行するため、リンク先は変更しません。ホーム外の設定や親ディレクトリがシンボリックリンクの設定は自動変更せず、インストーラーを実行する前に停止します。
- `dotfiles` モジュールの共通シェル設定でも、anyenvの初期化の後に `~/.yarn/switch/bin` をPATHの先頭に追加します。以前の `corepack enable` でnodenv配下に作られた `yarn` より優先させるためです。

`unzip` と `curl` が必要です（`base` モジュールで導入されます）。完了後はターミナルを再起動して確認してください。

```bash
yarn switch --version
command -v yarn   # ~/.yarn/switch/bin/yarn になっていること
```

## 追加・更新する

再実行すると最新の安定版で上書きされます。`update.sh --apply` による全体の再適用でも更新されます。

```bash
bash ~/ubuntu-infra/install.sh --only yarn-switch          # 変更予定を確認
bash ~/ubuntu-infra/install.sh --only yarn-switch --apply  # 導入・更新
```

以前のセットアップで `corepack enable` を実行済みの場合、nodenv配下のcorepack由来の `yarn` は自動では削除しません。PATHの順序でYarn Switchが優先されますが、不要なら `nodenv exec corepack disable` と `nodenv rehash` で削除できます。

## 基本コマンド

Yarn Switchは、一番近い `package.json` の `packageManager`（例: `"yarn@4.18.0"`）で指定されたバージョンのYarnを自動でダウンロードして実行します。指定がない場所ではYarn 1系の最新安定版を使います。

| コマンド | 内容 |
| --- | --- |
| `yarn switch --version` | Yarn Switch本体のバージョンを表示する |
| `yarn --version` | 現在のディレクトリで使われるYarnのバージョンを表示する |
| `yarn switch up berry` | Yarn 4系（berry）の最新安定版に更新し、`packageManager` を書き換える |
| `yarn switch up` | Yarn 6系（zpm）の最新安定版に更新する。**Yarn 4のプロジェクトでもYarn 6に上がる**ため注意 |
| `yarn switch <バージョン> <コマンド>` | `packageManager` を変えずに、指定したバージョンでコマンドを実行する（例: `yarn switch 4.18.0 --version`） |
| `yarn switch cache --install` | プロジェクトで指定されたバージョンを事前にダウンロードする |
| `yarn switch cache` | ダウンロード済みのバージョンを一覧表示する |
| `yarn switch cache --clear` | ダウンロード済みのバージョンを削除する |

`yarn switch up` の実行後は、`git diff` で `package.json` などの変更内容を確認してください。詳細は公式ドキュメントの[Yarn Switch](https://v6.yarnpkg.com/concepts/switch)と[インストール](https://v6.yarnpkg.com/getting-started)を参照してください。

## Safe Chainと併用するときの注意

Safe Chainは `yarn` をシェル関数で包み、自身のプロキシ（`HTTPS_PROXY`）と証明書（`NODE_EXTRA_CA_CERTS`）を設定して実行します。Yarn SwitchはRust製で `NODE_EXTRA_CA_CERTS` を読まないため、未取得のYarnをダウンロードするときに次のように失敗します。

```text
✗ · Failed to download Yarn 4.18.0 after 0.13s.
Error: error sending request for url (https://registry.npmjs.org/@yarnpkg/cli-dist/-/cli-dist-4.18.0.tgz)
```

Yarn Switchは、`package.json` の `packageManager` で指定されたバージョン（指定がない場所ではYarn 1系の最新安定版）を初回実行時にダウンロードします。初めて使うバージョンでこのエラーが出た場合（導入直後や `yarn switch up` の後など）は、対象のプロジェクトで次を1回実行してダウンロードしてください。`yarn switch up` 自体が失敗する場合は `command yarn switch up berry` のように実行します。`command` はシェル関数を経由せず、Safe Chainを通さずに実行します。

```bash
command yarn --version
```

一度ダウンロードしたバージョンは、以降Safe Chain経由の `yarn` でも動作します。`command yarn install` や `command yarn add` はSafe Chainの検査を回避するため使用しないでください。
