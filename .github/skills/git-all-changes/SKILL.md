---
name: git-all-changes
summary: |
  ワークスペース内の全ての変更ファイル（新規・修正・削除）を一括でgit add/commit/pushするワークフロースキル。
description: |
  このスキルは、VS Code上で「全ての変更をgitに反映したい」場合に利用します。
  - git add .
  - git commit -m "<メッセージ>"
  - git push
  を自動で実行し、未管理ファイルも含めて全ての変更をリモートリポジトリに反映します。
  
  ## 使い方
  1. 変更内容を確認したい場合は git status を先に実行してください。
  2. このスキルを呼び出すと、全ての変更がadd/commit/pushされます。
  3. コミットメッセージは自動生成または指定可能です。

  ## 注意
  - .gitignoreで除外されたファイルはaddされません。
  - 大容量バイナリや不要な一時ファイルが含まれていないか注意してください。
  - push前に内容を確認したい場合は、手動でgit status/diffを推奨します。

parameters:
  - name: commit_message
    type: string
    required: false
    description: コミットメッセージ（省略時は自動生成）

examples:
  - description: "全ての変更を一括でgitに反映する"
    params:
      commit_message: "replay: add all changes (auto skill)"
---

# git-all-changes スキル

このスキルを使うと、ワークスペース内の全ての変更（新規・修正・削除）を一括でgit add/commit/pushできます。

## ワークフロー
1. `git add .`
2. `git commit -m "<メッセージ>"`
3. `git push`

## 利用例
- 大量のCSVやBIN、diagnostics配下の新規ファイルを一括で反映したい場合
- レポートやスクリプト、画像など複数ファイルをまとめてコミットしたい場合

## 注意点
- .gitignoreで除外されたファイルはaddされません
- push前に内容を確認したい場合は、手動でgit status/diffを推奨します
