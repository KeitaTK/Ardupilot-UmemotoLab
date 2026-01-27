# ArduPilot Project - Copilot Custom Instructions

## 📋 プロジェクト概要
このプロジェクトはArduPilotベースのドローン制御システムです。
- 実装はArduPilotの公式実装方法に準拠してください
- 必要に応じてWeb検索やリソースを活用し、ArduPilot公式情報を参照してください

---

## 🚀 開発ワークフロー

### 標準的な修正・検証フロー
コード修正を行う際は、以下の手順を**必ず順番通りに**実行してください。

#### ⚡ フェーズ1: SITL開発・検証

1. **コード修正**
   - 必要な変更を実装

2. **コード検証**
   - 変数名・型が数学的に正しいか確認
   - プログラムのお作法（C++、組み込み）に準拠しているか確認
   - ArduPilotのコーディング規約に準拠しているか確認

3. **仮想環境有効化**（**必須・毎回実行**）
   ```bash
   source venv_ardupilot/bin/activate
   ```

4. **SITLビルド**
   ```bash
   ./waf -j$(nproc) copter
   ```

5. **オートテスト実行**（下記の必須テストを実行）
   - **必須オートテスト一覧**:
     - `test.Copter.ArmFeatures` - アーミング機能のテスト
     - `test.Copter.TestRLSBasicEstimation` - RLS推定テスト（カスタム）
     - `test.Copter.TestRLSFrequencyEstimation` - RLS周波数推定テスト（カスタム、実験的）
   
   - 実行例（利用可能な必須テストのみを順次実行）:
     ```bash
     # 利用可能なサブテスト一覧を取得し、必須テストのみ順次実行します
     available=$(Tools/autotest/autotest.py --list-subtests-for-vehicle Copter)
     for t in ArmFeatures TestRLSBasicEstimation TestRLSFrequencyEstimation; do
       if echo "$available" | tr ' ' '\n' | grep -xq "$t"; then
         echo "Running test.Copter.$t"
         timeout $([ "$t" = "TestRLSBasicEstimation" ] && echo 600 || echo 300) Tools/autotest/autotest.py --no-clean build.Copter test.Copter.$t || exit 1
       else
         echo "Skipping test.Copter.$t (not available)"
       fi
     done
     ```

6. **バグ修正ループ**
   - テストが失敗する場合、ステップ1に戻って修正を繰り返す
   - **すべてのテストがPASSするまで次のフェーズに進まないこと**

---

#### 🎯 フェーズ2: ハードウェアターゲット（Pixhawk6C）ビルド

**前提条件**: フェーズ1のすべてのオートテストがPASSしていること

1. **Pixhawk6C向け完全クリーンビルド**（推奨）
   ```bash
   cd /home/umemoto/UMEMOTO2
   rm -rf build/
   ./waf configure --board Pixhawk6C
   ./waf -j$(nproc) copter
   ```

2. **ビルドエラー対応**
   - エラーが出た場合、フェーズ1に戻って修正

**⚠️ 重要**: フェーズ1がクリアするまで、フェーズ2には進まないこと

---

### 📝 よく使うコマンド集

#### フェーズ1: SITL開発
```bash
# 仮想環境有効化（各セッション毎に必須）
cd /home/memoto/Ardupilot-UmemotoLab && source venv_ardupilot/bin/activate

# SITLビルド
./waf -j$(nproc) copter

# 必須オートテストをすべて実行（存在するテストのみを実行）
available=$(Tools/autotest/autotest.py --list-subtests-for-vehicle Copter)
for t in ArmFeatures TestRLSBasicEstimation; do
  if echo "$available" | tr ' ' '\n' | grep -xq "$t"; then
    echo "Running test.Copter.$t"
    timeout $([ "$t" = "TestRLSBasicEstimation" ] && echo 600 || echo 300) Tools/autotest/autotest.py --no-clean build.Copter test.Copter.$t || exit 1
  else
    echo "Skipping test.Copter.$t (not available)"
  fi
done

# エラー確認用（出力を絞る）
./waf -j$(nproc) copter 2>&1 | tail -30
timeout 300 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.ArmFeatures 2>&1 | grep -E "(PASSED|FAILED)" | tail -10
```

#### フェーズ2: Pixhawk6Cビルド（SITLテストPASS後のみ）
```bash
# 完全クリーンビルド（推奨）
rm -rf build/ && ./waf configure --board Pixhawk6C && ./waf -j$(nproc) copter

# ビルドエラー確認用
cd /home/umemoto/UMEMOTO2 && ./waf -j$(nproc) copter 2>&1 | tail -50
```

---

## 🔧 プロジェクト固有のルール

### AP_Observer ライブラリの開発
- **ファイル場所**: `libraries/AP_Observer/`
- **主要ファイル**: `AP_Observer.cpp`, `AP_Observer.h`
- **ログフォーマット**: ArduPilotのログラベル長制限（厳格）に注意
  - ログラベル名: 最大4文字（厳守）
  - ログフィールド名: 2-3文字推奨
  - フィールド数は最小限に抑える

### コーディングスタイル
- C++11以降の機能は使用可能（組み込みシステム向けに最適化）
- **動的メモリ確保は避ける**（スタック配列または静的配列を使用）
- `constexpr`を積極的に使用
- デバッグメッセージは`gcs().send_text()`を使用
- ログ出力は`AP_Logger`の`Write()`メソッドを使用

### ビルド制約
- Pixhawk6Cボードをターゲットとする場合、フラッシュメモリ制約に注意
- **未使用変数は必ず削除**（コンパイル警告がエラー扱い）
- インクルードは必要最小限に

### テスト要件
- 修正後は**必ず全ての必須オートテストを実行**
- テストがすべてPASSするまでデバッグと修正を繰り返す
- ログ出力量は既存と同等レベルに維持

## 🐛 よくある問題と解決策

| 問題 | 症状 | 原因 | 解決策 |
|------|------|------|--------|
| **ログフォーマットエラー** | `Test Suite: test.Copter.ArmFeatures FAILED` | ログラベル長やフィールド数の制約違反 | フィールド名を短縮、不要なフィールドを削除 |
| **未使用変数警告** | `error: unused variable 'variable_name'` | 変数が定義されているが使用されていない | 変数の削除または`(void)variable_name;`で明示的に使用 |
| **位相補正が動作しない** | P（位相補正）が0のまま | phase_bufferに時間ベース位相ではなく観測位相を格納すべき | `ab_phase_unwrapped[0]`をバッファに格納 |

---

## 🔍 デバッグ手法

### ログ確認
- **ログファイル**: `logs/OBSV_data_*.csv`
- **重要カラム**: 
  - X（観測位相）
  - P（位相補正）
  - F（推定周波数）
  - SW（周波数推定スイッチ状態、0=OFF/1=ON）

### GCSメッセージ
- `PhaseCorr: err=X.XXXX est_freq=X.XXXX Hz corr=X.XXXX` で位相補正状態を確認
- `RLS[0]: A=X.XXX B=X.XXX C=X.XXX` でRLS推定パラメータを確認
- `RLS Freq Est: ON/OFF` でRC Aux Function経由のスイッチ状態確認（新方式）

---

## 🎛️ RLS周波数推定スイッチ設定

### 新方式（推奨）: RC Aux Function方式
ArduPilot標準の`RC_OPTION`パラメータを使用する方法です。

**設定手順:**
1. **パラメータ設定**（例: RC7チャンネルを使用する場合）
   ```
   RC7_OPTION = 316  # RLS Frequency Estimation
   ```

2. **スイッチ動作**
   - RC7のPWM値が中央値より高い（HIGH位置）: 周波数推定ON
   - RC7のPWM値が中央値より低い（LOW位置）: 周波数推定OFF

3. **動作確認**
   - GCSメッセージ: `RLS Freq Est: ON` または `RLS Freq Est: OFF`
   - ログの`OBSV.SW`フィールド: 1（ON）または 0（OFF）

**対応RCチャンネル:**
- RC5_OPTION ～ RC16_OPTION のいずれかに `316` を設定可能
- **推奨**: RC7_OPTION（デフォルト設定）

---

### 旧方式（互換性維持）: OBS_FREQ_EST_CH パラメータ
直接RCチャンネル番号を指定する従来方式です。既存設定との互換性のため維持されています。

**設定手順:**
1. **パラメータ設定**（例: RC7チャンネルを使用する場合、デフォルト値）
   ```
   OBS_FREQ_EST_CH = 7  # RC7チャンネルを使用（デフォルト）
   ```

2. **スイッチ動作**
   - 指定チャンネルのPWM ≥ 1700: 周波数推定ON
   - 指定チャンネルのPWM < 1700: 周波数推定OFF

3. **動作確認**
   - ログの`OBSV.SW`フィールド: 1（ON）または 0（OFF）

**注意事項:**
- `OBS_FREQ_EST_CH = 0` で無効化（デフォルト）
- 有効なチャンネル番号: 1～16（RC1～RC16に対応）

---

### 両方式の併用
**重要**: 新方式と旧方式は**OR条件**で動作します。
- どちらか一方がONなら周波数推定が有効になります
- 両方式を同時に設定することも可能ですが、通常は新方式のみ推奨

**推奨設定:**
```
# 新方式のみ使用（推奨）
RC7_OPTION = 316
OBS_FREQ_EST_CH = 0  # 無効化

# または旧方式のみ使用（デフォルト設定）
OBS_FREQ_EST_CH = 7  # デフォルト値
RC7_OPTION = 0  # デフォルト（無効）
```

---

## ✅ 修正の原則

1. **段階的な変更** - 一度に多くを変更せず、小さな修正を積み重ねる
2. **即座の検証** - 各修正後、必ずビルド・テストを実行
3. **ログの保守** - ログ/メッセージの出力量は極力変更しない
4. **コメントの充実** - アルゴリズムの意図を明確にコメントで説明
5. **変数の整理** - 不要になった変数は定義・初期化含め完全に削除

---

## 📚 参考情報

### ArduPilotビルドシステム
- **ビルドツール**: wafビルドシステムを使用
- **ボード指定**: 
  - Pixhawk6C: `--board Pixhawk6C`
  - SITL: ボード指定不要
- **並列ビルド**: `-j$(nproc)` で高速化

### 主要なディレクトリ構造
```
Ardupilot-UmemotoLab/
├── libraries/AP_Observer/    # 外力推定ライブラリ（カスタム）
├── ArduCopter/               # コプター制御メインコード
├── Tools/autotest/           # オートテストスクリプト
├── logs/                     # ログファイル出力先
└── build/                    # ビルド成果物
```

---

## 🔄 Pixhawk6C向け完全クリーンビルド（2026/01/21検証済み）

### クリーンビルドのポイント
- `./waf clean` だけではキャッシュや一部生成物が残る場合がある
- **`rm -rf build/`でbuildディレクトリごと削除することが唯一確実なクリーンビルド手法**
- waf公式・ArduPilot開発でも推奨される手法
- 一回目から確実に全ファイルが再生成され、ビルド不整合や古い生成物の混入を防げる
- サブモジュールの不整合が疑われる場合は `git submodule update --init --recursive` も実行推奨
- 他ボードの場合は`--board`オプションを適宜変更

---

## 💡 追加のベストプラクティス

- ✅ 修正前に現在の動作を理解する
- ✅ 仮説を立ててから修正する
- ✅ 修正後の影響範囲を確認する
- ✅ テストでカバーされない部分は手動確認する
- ✅ 重要な変更はコミットメッセージに詳細を記載する

---

## 📖 ArduPilotコーディング規約

### ファイル構成と命名規則
- **ヘッダーファイル**: `#pragma once` を使用（includeガード代わり）
- **インクルード順序**:
  1. 標準ライブラリ（`<AP_Common/AP_Common.h>` など）
  2. ArduPilotライブラリ（`<AP_Math/AP_Math.h>` など）
  3. ローカルヘッダー（`"AP_Observer.h"` など）
- **クラス名**: `AP_` プレフィックス（例: `AP_Observer`, `AP_Motors`）
- **定数**: 全て大文字のスネークケース（例: `RLS_PARAM_SIZE`）

### パラメータ定義
- **パラメータテーブル**: `AP_Param::GroupInfo` を使用
- **パラメータコメント**: 以下のフォーマットに従う
  ```cpp
  // @Param: PARAM_NAME
  // @DisplayName: Human Readable Name
  // @Description: Detailed description
  // @Range: min max
  // @Units: unit
  // @User: Standard/Advanced
  ```

### メモリ管理
- **動的メモリ確保は避ける**: スタック配列または静的配列を使用
- **constexpr を積極的に使用**: コンパイル時定数には `static constexpr`
- **配列サイズ**: 明示的な定数で定義（マジックナンバー禁止）

### ログとデバッグ
- **ログフォーマット**: `logger->Write()` メソッドを使用
  - ラベル名: 最大4文字（厳守）
  - フィールド名: 2-3文字推奨
  - フォーマット文字列: "s" (時間), "f" (float), "Q" (uint64), など
- **デバッグメッセージ**: `gcs().send_text(MAV_SEVERITY_INFO, "message")` を使用
  - メッセージ出力頻度を制限（例: 100回に1回）
  - ログ出力量を最小限に抑える

### エラーハンドリング
- **ポインタチェック**: 必ず nullptr チェックを実行
  ```cpp
  AP_Motors* motors = AP::motors();
  if (!motors) {
      return;  // 静かに終了
  }
  ```
- **数値安定性**: ゼロ除算、オーバーフローを防ぐ
  ```cpp
  if (fabsf(denominator) < 1e-12f) {
      continue;
  }
  ```
- **制約関数**: `constrain_value()` で値を範囲内に制限

### コメント規則
- **アルゴリズムの説明**: 複雑な計算には数式と意図を記載
- **単位の明記**: 物理量には必ず単位をコメント（例: `[rad/s]`, `[Hz]`）
- **TODO/FIXME**: 将来の改善点を明記

### 具体例
```cpp
// 良い例
static constexpr float AB_PHASE_MIN_AMP = 1.0e-3f;  // 最小振幅 [N]
float omega = _disturbance_freq.get() * 2.0f * M_PI;  // 角周波数 [rad/s]

// 悪い例
#define MIN_AMP 0.001  // マクロではなくconstexprを使用
float omega = freq * 6.28;  // 2*PIをマジックナンバーで書かない
```

---

## 🎯 必須オートテスト一覧（まとめ）

コード修正後は、以下のテストを実行し、**すべてPASSすることを確認**してください（リポジトリの現在の利用状況に応じて増減します）。

| テスト名 | 説明 | タイムアウト |
|---------|------|-------------|
| `test.Copter.ArmFeatures` | アーミング機能のテスト | 300秒 |
| `test.Copter.TestRLSBasicEstimation` | RLS推定テスト（カスタム） | 600秒 |
| `test.Copter.TestRLSFrequencyEstimation` | RLS周波数推定テスト（カスタム、実験的） | 800秒 |

### 一括実行スクリプト例
```bash
#!/bin/bash
cd /home/memoto/Ardupilot-UmemotoLab
source venv_ardupilot/bin/activate

# 必須テストを順次実行
timeout 300 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.ArmFeatures || exit 1
timeout 600 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.TestRLSBasicEstimation || exit 1
timeout 800 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.TestRLSFrequencyEstimation || { echo "⚠️  TestRLSFrequencyEstimation failed (experimental)"; }

echo "✅ すべての必須テストが完了しました"
```

**⚠️ 注意**: `TestRLSFrequencyEstimation` は実験的な機能で、タイミングによって不安定な場合があります。

**⚠️ 重要**: すべてのテストがPASSするまで、Pixhawk6Cビルドには進まないこと。
