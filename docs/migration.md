# 移植元とUbuntuでの扱い

移植元: [mitsuharu/macos-infra](https://github.com/mitsuharu/macos-infra/tree/1609aabca098b5ab69b1fad7e99b65998107d3ac)。ユーザー提供メモの3記事も参照しています。メモ中のコマンドは要求された設定を把握する資料として扱い、そのまま自動実行する仕様にはしていません。

| macOS版 | Ubuntu版 |
| --- | --- |
| install.sh / shellsによるセットアップ | 同じBash構成、既定はdry-run、適用は--apply |
| Homebrew / Brewfile | aptと公式deb（Homebrewは導入しない） |
| OpenSSL / libyaml | libssl-dev / libyaml-devほかビルド依存 |
| anyenv | 公式Gitリポジトリ＋インストール定義 |
| rbenv / nodenv | 継続使用、バージョンを設定ファイルに分離 |
| Ruby 3.4.11 / Node.js 24.21.0 | 同じ版、ruby-build / node-buildの公開定義の存在を確認 |
| Corepack / aliases | 継続使用、nodenv execで対象Nodeを固定 |
| openjdk@17 / gh / gpg / watchman | openjdk-17-jdk / gh / gnupg / watchman |
| pinentry-mac | pinentry-gnome3（GPG既存設定は上書きしない） |
| .zprofile全体へのリンク | 共通設定ファイル＋.bashrc / .zshrcの管理ブロック |
| PATH全体の上書き | 既存PATHへの追加 |
| ~/Library/Android/sdk | ~/Android/Sdk（存在する場合のみPATH追加） |
| Flutterの既存ディレクトリ | 存在する場合のみPATH追加 |
| .npmrc / .huskyrc | 古いnpm設定・トークン雛形を配布しない。Huskyはプロジェクト側で設定 |
| Xcode / xcodegen / CocoaPods / iOS aliases | UbuntuではXcodeを使えないため自動導入しない |

WatchmanはUbuntu配布パッケージを使用するため、React Nativeプロジェクトがより新しい版を要求する場合は別途調整してください。JDKは導入しますがシステム全体のJava alternativesや既存のJAVA_HOMEは切り替えません。

## 日本語環境

メモのfcitx5記事はUbuntu 24.04 / GNOME X11 / USキーボードを前提としています。ユーザーのメモの入力順に合わせ、初期値は日本語キーボード→Mozcとしました。USへの切替はconfig.local.shで指定できます。既存のfcitx5 profileはバックアップした後、このグループ構成へ置き換えます。

GNOME用にim-config、ユーザー環境変数、自動起動、Gtk/IMModuleの設定を用意します。GTK_IM_MODULE=fcitxを設定してGTKのim moduleを使う方式です。GNOME以外には適用しません。GNOMEの設定辞書の他の値と型は保持します。Capsは競合するcaps:オプションを置き換え、他のXKB設定は保持します。

Waylandはアプリ・ツールキットによって入力と候補位置の挙動が異なります。GNOME Shell内の候補表示にはKimpanel等が必要になる場合があり、拡張機能やElectron起動フラグは一律変更しません。実機で不具合がある場合はfcitx5-diagnoseで確認します。

フォルダ英語化はXDGの参照先変更に限定します。記事のrm -rfやワイルドカードによるファイル移動は採用していません。

## 公式配布元

アプリはHTTPSの公式debをaptで導入します。deb内のパッケージ名・アーキテクチャを検査します。最初のdebはHTTPS配布元を信頼して取得し、別配布のチェックサムや署名との照合は行いません。ベンダーのdebが登録する署名付きaptリポジトリを以後の更新に利用します。Claude Desktopは公式手順どおりAnthropicのaptリポジトリ（`downloads.claude.ai/claude-desktop`）を登録してaptで導入します。apt全体が信頼するキーになるため、登録前に署名キーの主キーのフィンガープリントを公式ドキュメント記載の値と照合し、一致しなければ停止します。

ChatGPTは公式Linuxプレビューのdebを使います。公開されているUbuntu 24.04 / 26.04対応手順を参照しています。サインインとアプリ内セットアップは手動です。

- [メモ: fcitx5 + Mozc](https://qiita.com/kanagawa41/items/c54d0616ae27fa47dc4a)
- [メモ: CapsをCtrlへ](https://qiita.com/peachft/items/c5de9a0224a6e710ba1d)
- [メモ: フォルダ英語化](https://qiita.com/peachft/items/fde3bebd356c17c1cef6)
- [Fcitx: WaylandとGNOME](https://fcitx-im.org/wiki/Using_Fcitx_5_on_Wayland/en)
- [anyenv](https://github.com/anyenv/anyenv)
- [ruby-buildのビルド環境](https://github.com/rbenv/ruby-build/wiki#suggested-build-environment)
- [node-build](https://github.com/nodenv/node-build)
- [Chrome公式ダウンロード](https://www.google.com/chrome/)
- [VS Code Linux](https://code.visualstudio.com/docs/setup/linux)
- [1Password Linux](https://support.1password.com/install-linux/)
- [ChatGPT Linux](https://learn.chatgpt.com/docs/linux/linux-app)
- [Claude Desktop on Linux](https://code.claude.com/docs/ja/desktop-linux)

## AGENTS.mdの出典

[create-agents-mdスキル](https://github.com/mitsuharu/agent-skills/blob/main/skills/create-agents-md/SKILL.md) とその [assets/AGENTS.md](https://github.com/mitsuharu/agent-skills/blob/main/skills/create-agents-md/assets/AGENTS.md) を土台に、macos-infraの規約を補っています。概要・対応OS・固定ランタイム・検証コマンドはこのリポジトリのconfig.sh、shells/、tests/、CIから、作者はリポジトリURLから埋めています。

共通ルールの調整は、保護対象ブランチへmasterも加えたこと、競合ケースをテスト項目に明記したこと、セットアップ用なので本番マシンでのテスト実行を禁止したことです。macOSのXcode等の検証はUbuntu用の構文・GLib・一時ホームテストに置き換えています。Releaseはこの初期構成では自動化していません。
