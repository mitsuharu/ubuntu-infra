# Safe Chainの月次更新

[公式README](https://github.com/AikidoSec/safe-chain#unixlinuxmacos)のインストール手順を保つため、`.github/workflows/safe-chain-update.yml` が毎月1日11:37（日本時間）に確認します。macOS版と実行時刻をずらしています。Actionsの「Safe Chainの月次更新」から `master` を選んで手動実行することもできます。

1. 公式READMEのUnix/Linux/macOS手順から固定バージョンとSHA-256を読み取ります。
2. 最新の正式リリースとバージョンが一致し、取得したインストーラーのSHA-256が一致することを確認します。
3. `shells/safe-chain-release.sh` に変更がある場合だけ更新PRを作成します。同じ内容のPRを再作成せず、自動マージもしません。

取得したインストーラーは月次ジョブでは実行しません。通常CIと同様、一時ホームと模擬インストーラーを使うテストで検証します。CIはUbuntuへの全導入や実際のSafe Chainによる通信保護を保証しません。

## GitHub側の設定

リポジトリの **Settings → Actions → General → Workflow permissions → Allow GitHub Actions to create and approve pull requests** を有効にしてください。追加の個人トークンは不要で、更新ジョブだけに `contents: write` と `pull-requests: write` を付けています。

自動作成PRのCIが承認待ちの場合はPR画面の **Approve workflows to run** から起動し、CIの成功とリリース内容を確認してから手動でマージしてください。[GitHubのイベント起動仕様](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)も参照してください。

## 確認や更新に失敗した場合

公式手順の形式変更、READMEと最新リリースの不一致、ハッシュ不一致、通信エラーでは、設定の更新を止めてWorkflowを失敗させます。Actionsの失敗通知を有効にしておいてください。

通信障害やリリース直後の不整合なら時間を置いて再実行します。公式手順が変わった場合は、公式READMEとインストーラーの変更内容を確認し、取得処理・検証処理・シェル設定のバックアップ対象も見直してください。ハッシュ照合を省略したり、取得した手順をそのまま評価したりしないでください。

PR作成の直前に失敗した場合、同じ設定のブランチがあれば上書きせず再利用します。異なる変更が入っていれば停止します。同じ更新PRがすでに閉じられている場合も、自動で再作成しません。

## 手元のUbuntuに反映する

```bash
bash ~/ubuntu-infra/update.sh
bash ~/ubuntu-infra/install.sh --only safe-chain
bash ~/ubuntu-infra/install.sh --only safe-chain --apply
```

`base` モジュールの依存パッケージ（curl、ca-certificates、Pythonなど）を先に適用してください。ターミナルの再起動後に `safe-chain --version` と `npm safe-chain-verify` を確認します。
