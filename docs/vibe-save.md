# VibeCoding セッション保存（ローカル）

このドキュメントは、VibeCoding のチャット内容をローカルに保存する方法と運用手順をまとめたものです。

## 概要

- チャットのコピーをローカルに保存し、必要に応じてブランチにコミットして履歴として残せるようにするためのツールが `tools/` にあります。

## 提供ファイル

- `tools/save-vibe.ps1` — クリップボードや対話的エディタから `.vibe/sessions/<branch>-<ts>.md` に保存します。`-commit` を付けると自動で `git add` + `git commit` します。
- `tools/git-hooks/pre-push` — `.vibe` 下の未コミットファイルを検出してプッシュを中止するテンプレート（ローカルで `.git/hooks/pre-push` にコピーして利用）。
- `.vscode/tasks.json` / `.vscode/keybindings.json` — VSCode のタスクとキー割当の雛形（例: `Ctrl+Alt+X` で保存＋コミット）。

## クイックセットアップ

1. 実行ポリシーの一時回避（推奨、1回だけ）:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\save-vibe.ps1
```

2. pre-push フックを有効にする（任意）:

```powershell
copy .\tools\git-hooks\pre-push .git\hooks\pre-push
# Git Bash/WSL の場合: chmod +x .git/hooks/pre-push
```

3. VSCode でタスクを使うか、キー割り当てを追加します（例）:

```json
{
  "key": "ctrl+alt+x",
  "command": "workbench.action.tasks.runTask",
  "args": "Save Vibe session (commit from clipboard)"
}
```

## 使い方

1. チャットで `Copy All` を押す。
2. VSCode で `Ctrl+Alt+X` を押す（タスクが実行され、会話が `.vibe/sessions` に保存されます）。

## 注意

- デフォルトで `.vibe/` は `.gitignore` に追加されています。会話をブランチに残す場合は `-commit` を使ってください（機密情報が含まれていないことを確認してください）。
- チームで運用する場合は、`.vscode/keybindings.json` を共有するよりも README に手順を記載し、各自でキーを設定することを推奨します。

