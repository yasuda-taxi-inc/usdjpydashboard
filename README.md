# USD/JPY デイトレード モニター

完全クライアントサイドで動作する、USD/JPYデイトレード向けダッシュボード。
Twelve Data APIから価格・出来高を取得し、値幅予測・セッション分析・SBI証券向けロット計算機・
[usdjpy-signal-bot](https://github.com/) のシグナル履歴表示を統合しています。

サーバー不要の単一HTMLファイルです(`index.html`)。

## このリポジトリについて

- 本リポジトリは**公開(public)でも問題ありません**。含まれるのはダッシュボードのUIとロジックのみで、
  トレード戦略の具体的な条件式は含まれていません(それらは`usdjpy-signal-bot`リポジトリ側にあり、そちらは非公開推奨のままです)。
- 「シグナル履歴(監視ボット)」パネルは、ブラウザ側でご自身のGitHub Personal Access Token(PAT)を
  入力・保存(localStorageのみ、コードには含まれません)することで、`usdjpy-signal-bot`リポジトリの
  `signals_history.json`を読みに行きます。このトークンはこのリポジトリを公開してもコードとして
  漏れることはありません。

## デプロイ方法

### 方法A: GitHub Pages(推奨・追加費用なし)

1. GitHubで新しいリポジトリを作成(public)し、このフォルダの中身をpush
   ```bash
   cd usdjpy-dashboard
   git init
   git add .
   git commit -m "initial commit"
   git branch -M main
   git remote add origin https://github.com/<あなたのユーザー名>/<リポジトリ名>.git
   git push -u origin main
   ```
2. リポジトリの `Settings > Pages` を開く
3. 「Source」を `Deploy from a branch` にし、ブランチ `main` / フォルダ `/ (root)` を選択して保存
4. 数分後 `https://<あなたのユーザー名>.github.io/<リポジトリ名>/` で公開されます
5. 以降は `git push` するだけで自動的に反映されます(手動でのNetlify Dropが不要になります)

### 方法B: 既存のNetlify Dropを継続

GitHubはソース管理のみに使い、デプロイは今までどおりNetlify Dropで行うことも可能です。
その場合は本リポジトリをNetlifyの「Import from Git」機能で連携すると、pushするたびに
自動デプロイされるようになり、毎回のドラッグ&ドロップが不要になります。

## シグナル履歴パネルの設定手順

1. ダッシュボード右上の「シグナル履歴(監視ボット)」パネルを開き、⚙ボタンをクリック
2. GitHubユーザー名、`usdjpy-signal-bot`のリポジトリ名を入力
3. 読み取り専用PATを発行して入力:
   - [GitHub Developer settings](https://github.com/settings/personal-access-tokens) にアクセス
   - 「Fine-grained tokens」→「Generate new token」
   - Repository access: `usdjpy-signal-bot` のみを選択
   - Permissions: `Contents` を `Read-only` に設定(それ以外は付与しない)
   - 有効期限はお好みで(90日など。切れたら再発行してください)
4. 「保存して再取得」をクリック

以降、5分おきに自動更新されます。

## 制限事項

- Twelve Data APIキーはコード内に直接埋め込まれています(無料プランの範囲での個人利用のため)。他人に知られたくない場合はご自身のキーに差し替えてください。
- GitHub Fine-grained PATには有効期限があります。切れると「取得失敗」と表示されるので、その際は再発行してください。
