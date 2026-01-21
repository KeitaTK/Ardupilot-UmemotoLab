# GitHub Copilot カスタムインストラクション 使用ガイド

## 概要
このワークスペースには、ArduPilot開発に特化したGitHub Copilotカスタムインストラクションが設定されています。

## 設定ファイル
- **カスタムインストラクション**: `.github/copilot-instructions.md`
- **VS Code設定**: `.vscode/settings.json`

## Copilotの使い方

### 1. チャットでカスタムインストラクションを活用
Copilot Chatを開いて（`Ctrl+Shift+I` または `Cmd+Shift+I`）、以下のように質問してください：

```
AP_Observerの位相補正アルゴリズムを修正して、テストまで実行して
```

Copilotは自動的に以下を実行します：
1. コード修正
2. ビルド実行
3. オートテスト実行
4. 結果確認

### 2. インラインサジェスト
コードを書いている時、Copilotは自動的にプロジェクト固有のルールに従った提案をします：
- ArduPilotのコーディングスタイル
- ログフォーマット制約
- RLSアルゴリズムのパターン

### 3. よく使うプロンプト例

#### コード修正とテスト
```
RLS_LAMBDAパラメータを0.95に変更して、ビルド・テストを実行して
```

#### デバッグ
```
位相補正が動作しない原因を調査して、修正して
```

#### ログ分析
```
OBSV_data_*.csvのXカラムをプロットするスクリプトを作成して
```

## カスタムインストラクションに含まれる内容

### 開発ワークフロー
- 標準的な修正・検証フロー（修正→ビルド→テスト→確認）
- よく使うコマンド例

### プロジェクト固有のルール
- AP_Observerライブラリの開発ガイドライン
- コーディングスタイル（C++組み込み向け）
- ビルド制約（フラッシュメモリ、未使用変数など）

### よくある問題と解決策
- ログフォーマットエラー
- 未使用変数警告
- 位相補正の動作不良

### デバッグ手法
- ログ確認方法
- GCSメッセージの読み方

## カスタムインストラクションの更新

`.github/copilot-instructions.md` を編集すれば、Copilotの動作をカスタマイズできます。

### 更新後の確認
1. VS Codeを再起動（推奨）
2. Copilot Chatで新しい会話を開始
3. プロンプトで「プロジェクトの開発フローを教えて」と質問して、更新内容が反映されているか確認

## トラブルシューティング

### Copilotがカスタムインストラクションを使わない場合
1. `.github/copilot-instructions.md` が存在することを確認
2. VS Codeを再起動
3. Copilot拡張機能が最新版であることを確認
4. Copilot Chatで明示的に「プロジェクトのルールに従って」と指示

### 設定の確認
```bash
# カスタムインストラクションファイルの確認
cat .github/copilot-instructions.md

# VS Code設定の確認
cat .vscode/settings.json
```

## 参考リンク
- [GitHub Copilot ドキュメント](https://docs.github.com/en/copilot)
- [Copilot カスタムインストラクション](https://docs.github.com/en/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot)
