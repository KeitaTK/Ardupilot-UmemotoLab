# Copilot カスタムインストラクション セットアップ完了

## ✅ 作成されたファイル

1. **`.github/copilot-instructions.md`** (4,986 bytes)
   - ArduPilot開発ワークフロー
   - AP_Observer固有のルール
   - ビルド・テスト手順
   - デバッグ手法
   - よくある問題と解決策

2. **`.github/COPILOT_USAGE.md`** (3,308 bytes)
   - Copilotの使い方ガイド
   - プロンプト例
   - トラブルシューティング

3. **`.vscode/settings.json`** (更新済み)
   - Copilot有効化設定
   - プロジェクトテンプレート使用設定

## 🚀 使い方

### 基本的な使用方法
1. VS CodeでCopilot Chatを開く: `Ctrl+Shift+I` (Linux/Windows) または `Cmd+Shift+I` (Mac)
2. プロンプトを入力:
   ```
   AP_Observerの位相補正を修正して、ビルド・テストまで実行して
   ```
3. Copilotが自動的に以下を実行:
   - コード修正
   - `./waf -j$(nproc) copter` でビルド
   - `Tools/autotest/autotest.py` でテスト
   - 結果確認

### よく使うプロンプト例

#### 標準的な開発フロー
```
RLS_LAMBAパラメータを0.95に変更して、ビルド・テストを実行して
```

#### デバッグ
```
位相補正が動作しない原因を調べて修正して
```

#### ログ分析
```
OBSV_data_00000404.csvのXとPカラムをプロットして
```

## 📋 カスタムインストラクションの主な内容

### 開発ワークフロー
- **修正 → ビルド → テスト → 確認** の標準フロー
- コマンド例とショートカット

### プロジェクト固有のルール
- ログフォーマット制約（フィールド名は2-3文字）
- 位相推定アルゴリズム（A/B係数から観測位相）
- RLS実装パターン（X軸位相を全軸に使用）

### よくある問題
- ログラベル長エラー → フィールド名短縮
- 未使用変数警告 → 変数削除
- 位相補正が0 → `ab_phase_unwrapped[0]`をバッファに格納

## 🔧 設定確認

```bash
# カスタムインストラクションの確認
cat .github/copilot-instructions.md

# VS Code設定の確認
cat .vscode/settings.json

# 使い方ガイドの確認
cat .github/COPILOT_USAGE.md
```

## 📝 更新方法

カスタムインストラクションを更新する場合:
1. `.github/copilot-instructions.md` を編集
2. VS Codeを再起動（推奨）
3. Copilot Chatで動作確認

## 🎯 次のステップ

1. VS Codeを再起動してCopilotに設定を読み込ませる
2. Copilot Chatを開いて試してみる:
   ```
   プロジェクトの開発フローを教えて
   ```
3. 実際のコード修正タスクで試す

## 📚 詳細ドキュメント

- カスタムインストラクション: `.github/copilot-instructions.md`
- 使い方ガイド: `.github/COPILOT_USAGE.md`
