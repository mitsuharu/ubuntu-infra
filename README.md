# ubuntu-infra

Ubuntu Desktopの日本語入力と開発環境を再現する、個人用Bashセットアップです。[macos-infra](https://github.com/mitsuharu/macos-infra) の構成をUbuntu向けに移植しています。

対象は **Ubuntu 24.04 / 26.04 LTS、GNOME、amd64（Intel / AMD）**。日本語UI、キーボード日本語配列が初期値です。Wayland / X11でfcitx5のim moduleを使用します。ARM、他のデスクトップは現時点では対象外です。

**検証状況:** Ubuntu 26.04で構文、ShellCheck、一時ホームを使った安全性テスト、変更なしのdry-runを検証しています。新規OSへの全インストール、Rubyビルド、実際の日本語入力、再ログイン後の挙動は未検証です。

## 実行する

Gitの事前インストールは不要です。`curl` でbootstrapを取得し、内容を確認してから実行します。`curl` がない場合だけ、先に `sudo apt update` と `sudo apt install -y curl ca-certificates` を実行してください。`build-essential` にはGitやcurlは含まれません。

```bash
bootstrap_file=$(mktemp)
curl --proto '=https' --tlsv1.2 -fL \
  https://raw.githubusercontent.com/mitsuharu/ubuntu-infra/master/bootstrap.sh \
  -o "$bootstrap_file"
cat "$bootstrap_file"           # 実行前に内容を確認
bash "$bootstrap_file" https://github.com/mitsuharu/ubuntu-infra.git
rm -f "$bootstrap_file"
```

bootstrapはGitがなければaptで導入し、`~/ubuntu-infra` にリポジトリをcloneして、セットアップの変更予定を表示します。**bootstrap自体のGit導入・cloneは実際に行いますが、環境設定の適用はまだ行いません。** 既存のチェックアウトがあれば、その内容を使い、自動更新しません。取得に失敗した場合は実行せず、URLや通信状態を確認してください。

取得した `~/ubuntu-infra` のスクリプト・`config.sh` と表示された予定を確認した後、必要な設定を調整して適用します。

```bash
cd ~/ubuntu-infra
bash install.sh                 # 変更予定をもう一度確認
bash install.sh --apply         # 実際に適用
```

すでにGitがある場合は、`git clone https://github.com/mitsuharu/ubuntu-infra.git ~/ubuntu-infra` で取得しても構いません。

全体を `sudo bash install.sh` で起動しないでください。システムパッケージ操作にだけsudoを使い、ユーザー設定・anyenvは通常ユーザーのホームに配置します。既存のanyenvやdotfilesがあるマシンでも再実行できます。既存のanyenv本体やプラグインは自動pullせず、そのチェックアウトを使います。

日本語入力を設定する際、fcitx5が起動済みならトレイから一度終了してください。設定ファイルの書き戻しとの競合を避けるため、その状態では適用前に停止します。GNOMEにログインした端末で実行し、終了後はログアウト→ログインしてください。自動再起動はしません。

## 設定を変える

`config.sh` を参照し、個人の変更はGit管理しない `config.local.sh` に書きます。

```bash
cat > config.local.sh <<'CONFIG'
KEYBOARD_LAYOUT=us
RUBY_VERSION=3.4.11
NODE_VERSION=24.21.0
INSTALL_CHATGPT=0
CONFIG
```

キーボードの初期値はメモの「キーボードー日本語」に合わせた `jp` です。USキーボードでは `us` に変更してください。GNOMEのシステム全体の物理キーボード配列は変更せず、fcitx5のグループ配列を設定します。

## モジュール

```bash
bash install.sh --only anyenv          # この部分だけ予定を見る
bash install.sh --only base --apply    # 依存パッケージ
bash install.sh --only dotfiles --apply
bash install.sh --only anyenv --apply
bash install.sh --only safe-chain          # Safe Chainの変更予定
bash install.sh --only safe-chain --apply  # Safe Chainの導入・更新
```

| モジュール | 内容 |
| --- | --- |
| `base` | build-essential、Rubyビルド依存、Zsh、Java 17、gh、GPG、pinentry、Watchmanなど |
| `dotfiles` | Bash / Zshのanyenv初期化、GPG_TTY、Linux版Android SDK / FlutterのPATH、共通alias |
| `anyenv` | anyenv、anyenv-update、rbenv、nodenv、Ruby 3.4.11、Node.js 24.21.0、Corepack、aliasesプラグイン |
| `safe-chain` | 公式インストーラーをバージョン固定・SHA-256検証付きで実行し、パッケージ取得時の保護を設定 |
| `japanese` | fcitx5＋Mozc、GTK / Qt frontend、日本語パック・フォント、自動起動、キーボード→Mozcの順序 |
| `desktop` | Caps Lock→Ctrl、XDG標準フォルダの英語名への参照変更 |
| `apps` | Chrome、VS Code、1Password、ChatGPT、Claude Code（個別に無効化可能） |
| `chrome-keyring` | Seahorse導入と起動、自動ログイン時のパスワードなしキーリングへの変更案内 |

個別実行時、`dotfiles` / `anyenv` / `safe-chain` / `desktop` より先に `base` を適用してください。全体実行時は順に処理します。`all` が初期値です。途中で失敗した場合は、原因を修正して同じコマンドを再実行できます。

`anyenv` はグローバルRuby / Nodeバージョンを上表の値に設定します。プロジェクト内の `.ruby-version` / `.node-version` は以後のシェルでは引き続き優先されます。スクリプト実行中のみ環境変数で導入対象バージョンを固定します。YarnはプロジェクトごとにCorepackで選びます。デフォルトシェルの変更、Android SDK / Flutterそのもののインストールは行いません。

## Safe Chain

全体の `--apply` では、anyenvの直後に `safe-chain` モジュールを実行します。既定のdry-runは予定の表示だけで、ダウンロードも設定変更もしません。導入・更新は[公式Unix/Linux/macOS手順](https://github.com/AikidoSec/safe-chain#unixlinuxmacos)の「バージョン固定URLから取得 → SHA-256照合 → `sh` で実行」の順序を維持します。

導入先は `~/.safe-chain` です。公式処理はBash / Zshなど検出したシェルの初期化ファイルに読み込み処理を追加し、対象パッケージマネージャーの既存aliasを置き換える場合があります。npm / Volta / nvm版のSafe Chainがあれば公式処理で移行されることがあります。変更前のシェル設定は通常のバックアップ先の `safe-chain/` 以下へ保存し、ファイル自体がシンボリックリンクならリンクをバックアップして独立したコピーに置き換えます。ホーム外の設定、親ディレクトリがシンボリックリンクの設定、壊れたリンクは自動変更せず停止します。

完了後はターミナルを再起動し、次を確認してください。

```bash
safe-chain --version
npm safe-chain-verify
```

`OK: Safe-chain works!` が成功の目印です。同じバージョンが導入済みなら再インストールしません。シェル統合が無効な場合は既存設定を確認してください。

バージョンとハッシュは `shells/safe-chain-release.sh` にまとめています。月次の更新PRを取り込んだ後、`bash install.sh --only safe-chain --apply` で更新できます。`update.sh --apply` による全体の再適用でも反映されます。

毎月の更新確認、PR作成のためのGitHub設定、失敗時の対応は [Safe Chainの運用手順](docs/safe-chain.md) を参照してください。

## 初回だけ必要な操作

- Chromeのキーリングは [専用手順](docs/chrome-keyring.md) に従って、新しいパスワードを空にします。削除は不要です。
- アプリのサインイン、1Passwordのブラウザ拡張連携は画面で設定します。
- 日本語入力は再ログイン後に `fcitx5-configtool` を開き、キーボード→Mozcの順と切替キーを確認します。診断は `fcitx5-diagnose` です。GNOME Shell内の入力欄やアプリ固有の候補ウィンドウ位置には制約があります。
- 日本語名フォルダ内のファイルは残します。必要なものを英語名のフォルダへ手動で移してください。日本語名のフォルダを削除する処理はありません。次回ログイン時に標準フォルダ名の更新を尋ねられた場合は「古い名前のままにする」を選びます。

## バックアップ・戻し方

変更したユーザー設定は `~/.local/state/ubuntu-infra/backups/<日時>-<PID>/` 以下に元の相対パスで保存します（`XDG_STATE_HOME` があればその配下）。変更がなければ同じ設定ファイルを再バックアップしません。キーリングなどの秘密情報はバックアップしません。

復元するファイルを確認し、対応するホーム側のパスへコピーしてください。シンボリックリンクだった設定は、リンク自体をバックアップし、リンク先を直接書き換えません。

GNOME設定の元の値はバックアップ内の `gsettings/*.txt` にあります。例えばCaps設定は次のように戻せます。

```bash
gsettings set org.gnome.desktop.input-sources xkb-options "$(cat /path/to/backup/gsettings/org.gnome.desktop.input-sources.xkb-options.txt)"
```

これはユーザー設定の復元です。aptパッケージ、ベンダーのdebが登録するaptリポジトリ、anyenv本体・ビルド成果物の自動アンインストール機能はありません。

## 更新

### 手動で更新する

`master` を最新にしてから、変更予定を確認して適用します。

```bash
cd ~/ubuntu-infra
git status                      # 未コミットの変更がないことを確認
git switch master
git pull --ff-only origin master
bash install.sh                 # 変更予定を確認
bash install.sh --apply         # 実際に適用
```

`--ff-only` により、手元に独自のコミットがあって履歴が分かれている場合はマージせずに止まります。その場合は手元の変更を確認してから対処してください。

### 更新スクリプトを使う

`update.sh` は上の `git pull --ff-only` と再適用をまとめたものです。

```bash
bash ~/ubuntu-infra/update.sh          # リポジトリのみfast-forward更新
bash ~/ubuntu-infra/update.sh --apply  # 更新後にセットアップを再適用
```

`--apply` は変更予定の表示を挟まずに適用します。更新内容を確認したい場合は、`update.sh` だけを実行し、`bash install.sh` で予定を見てから `bash install.sh --apply` を実行してください。

どちらの方法も `main` / `master` かつ作業ツリーがクリーンな場合に限ります（`update.sh` はそれ以外では止まります）。アプリの既存パッケージはセットアップ時に再ダウンロードせず、通常の `sudo apt update` とパッケージを指定した `sudo apt install --only-upgrade ...` で更新します。Claude Codeは公式インストーラーの更新方式を利用します。Ruby / Nodeは `config.local.sh` のバージョンを明示的に変えてからanyenvを再適用します。定義が見つからない場合は対応するruby-build / node-buildの更新を確認してください。

`bootstrap.sh` は冒頭のcurl手順で使う初回セットアップの入口です。取得済みのbootstrapに `--apply` を付けるとclone後にそのまま適用できます。まず既定の変更予定表示で設定を確認してください。

## リリース

`master` にマージ済みのコミットへ `1.2.3` 形式のタグをpushすると、[.github/workflows/release.yml](.github/workflows/release.yml) がそのタグでGitHub Releaseを作成します。リリースノートはGitHubの自動生成を使います。

```bash
git tag 1.0.0 && git push origin 1.0.0
```

Actionsの「GitHub Release」を `master` から手動実行し、`version` にタグ名を入れると、そのときの `master` の先頭コミットにタグを作って公開します。`v1.0.0` や `1.0.0-rc1` のような形式、`master` 以外からの手動実行、同名のリリースが既にある場合は失敗し、既存のリリースは上書きしません。タグとリリースは公開後に取り消しにくいため、作成前に作者が確認してください。

## 検証

```bash
find . -name '*.sh' -print0 | xargs -0 -n1 bash -n
zsh -n dotfiles/shell.sh
shellcheck -x -e SC1090,SC1091,SC2034 install.sh bootstrap.sh update.sh shells/*.sh
/usr/bin/python3 -m unittest discover -s tests -v
bash install.sh --dry-run
```

Zsh、ShellCheck、python3-giが必要です。CIはPRと毎月の構文・安全性テストのみで、セットアップ本体やホストのユーザー設定は変更しません。CI成功は新規Ubuntuへの全導入成功を保証しません。

移植元と判断の詳細は [docs/migration.md](docs/migration.md)、エージェントの作業規約は [AGENTS.md](AGENTS.md) を参照してください。
