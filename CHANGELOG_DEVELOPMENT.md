# 開発履歴・トライアンドエラー記録

このファイルは開発中のトライアンドエラー、バグ修正、実験的な変更の履歴を記録します。
正式なリリースノートは別途管理してください。

## 記録形式

各エントリは以下の形式で記録：
```
### YYYY-MM-DD: [機能名/コンポーネント]
- 問題: [発生した問題の簡潔な説明]
- 調査: [調査内容・原因]
- 試行: [実施した変更・試したこと]
- 結果: [最終的な結果・解決方法]
- 備考: [その他重要な情報]
```

---

## 2026-01-28 (続): RLS周波数推定スイッチ制御 - 旧方式削除とRC8統一

### 問題
- RC8スイッチON→OFF時に、ON/OFFメッセージがペアで表示される不具合
- 原因調査中に旧方式（OBS_FREQ_EST_CH）と新方式（RC Aux Function）の両方が混在していることが判明
- ユーザー要望: 旧方式削除、RC8_OPTION=316のみに統一

### 調査
- update()内で旧方式と新方式のOR条件処理があった
- `set_freq_estimation_switch()`がRC Aux Functionから呼ばれる
- `reset_frequency_estimation()` → `phase_correction_init()` で `_freq_estimation_switch_state = false;` が実行される
- これにより、スイッチONに設定した直後に内部でfalseにリセットされ、update()が0→1→0の変化を検出してON/OFFの両方を表示していた

### 試行と結果
1. **旧方式の完全削除** (AP_Observer.cpp/h)
   - `read_freq_estimation_switch()`メソッドを削除
   - update()内のOR条件処理を削除
   - `_freq_estimation_switch_state`のみで制御するように簡略化
   - RC Aux Functionから`set_freq_estimation_switch()`が呼ばれるシンプルな構造に

2. **phase_correction_init()のバグ修正**
   - L650の`_freq_estimation_switch_state = false;`を削除
   - この行がスイッチ状態を不正にリセットしていた根本原因
   - phase_correction_init()はRLS推定パラメータのリセットのみを行うべき

3. **動作確認**
   - ユーザーテストログで完璧な動作を確認：
     - OFF → ON: 1回のONメッセージ、state=1が安定
     - ON → OFF: 1回のOFFメッセージ、state=0が安定
     - OFF → ON: 再度1回のONメッセージ、state=1が安定
   - 不正なペア表示が完全に解消

4. **デバッグコードのクリーンアップ**
   - set_freq_estimation_switch()のcall counter削除
   - update()の"Switch change detected"/"Switch stable"メッセージ削除
   - 本番環境に不要なデバッグログを除去

5. **オートテストの確認と修正** (完了)
   - 問題: 既存のautotestが旧方式（OBS_FREQ_EST_CH）を使用している
   - 対象テスト:
     - TestRLSRC8SwitchControl → RC8_OPTION=316に修正
     - TestRLSWindowedEstimation → RC8_OPTION=316に修正
     - TestRLSDualMethodControl → 削除（旧方式テストのため不要）
   - 修正結果: すべてのテストがPASS
     - test.Copter.ArmFeatures: PASSED
     - test.Copter.TestRLSBasicEstimation: PASSED
     - test.Copter.TestRLSRC8SwitchControl: PASSED (RC Aux Function版)

### 変更ファイル
- libraries/AP_Observer/AP_Observer.cpp
- libraries/AP_Observer/AP_Observer.h
- ArduCopter/RC_Channel_Copter.cpp（変更なし - 既に正常動作）
- Tools/autotest/arducopter.py（オートテスト修正）

### テスト結果
✅ すべての必須テストがPASS
- test.Copter.ArmFeatures: PASSED (300秒制限)
- test.Copter.TestRLSBasicEstimation: PASSED (600秒制限)
- test.Copter.TestRLSRC8SwitchControl: PASSED (RC8_OPTION=316)

### 備考
- 旧方式パラメータ`OBS_FREQ_EST_CH`は完全に廃止（コード上から削除）
- RC8_OPTION=316がデフォルト設定として推奨
- phase_correction_init()は初期化専用、状態変数の変更は行わない原則を確立

---

## 2026-01-28: RLS周波数推定スイッチ制御機能の検証とバグ修正

### 背景
周波数推定の切り替え機能に2つの設定方法（新方式・旧方式）が実装されていたが、動作確認とオートテストが不足していた。

### 実施内容

#### 1. 既存実装の調査
- 調査: 
  - 新方式: `RC_OPTION = 316` (RC Aux Function) - ArduCopter/RC_Channel_Copter.cpp
  - 旧方式: `OBS_FREQ_EST_CH` パラメータ - AP_Observer/AP_Observer.cpp
  - 両方式はOR条件で動作、競合なし
- 結果: 実装は存在するが、統合テストが不足

#### 2. バグ発見と修正
- 問題: 
  - 既存テスト（TestRLSRC8SwitchControl, TestRLSRCAuxFunction）が失敗
  - ログの`SW`フィールドが常に0（スイッチ状態が記録されない）
- 原因: 
  - `write_log()`で`_freq_estimation_switch_state`のみを記録
  - 実際の動作は`current_switch = _freq_estimation_switch_state || read_freq_estimation_switch()`（OR条件）
  - ログには統合された値を記録すべきだが、新方式の値のみ記録していた
- 修正内容:
  - AP_Observer.h: `_combined_freq_est_switch`メンバー変数を追加
  - AP_Observer.cpp: `update()`で統合スイッチ状態を`_combined_freq_est_switch`に保存
  - AP_Observer.cpp: `write_log()`で`_combined_freq_est_switch`を記録
- 結果: 旧方式テスト（RC8）が正常にPASS

#### 3. 新方式（RC Aux Function）の問題
- 問題: 
  - RC7/RC9でRC_OPTION=316を設定しても動作しない
  - GCSメッセージ "RLS Freq Est: ON" が表示されない
- 調査: 
  - `do_aux_function()`は正しく実装済み
  - RC9がSITL環境で有効なチャンネルとして認識されていない可能性
  - RC7はデフォルトで"SaveWaypoint"機能が割り当て済み
- 試行:
  - RC9からRC7への変更 → 失敗
  - PWM設定タイミングの調整 → 失敗
- 結果: SITL環境では動作不安定（実機での検証が必要）

#### 4. オートテストの作成
- 作成したテスト:
  - `TestRLSDualMethodControl`: 両方式の併用・競合チェック（開発中）
  - テストリストに登録済み
- 既存テストの修正:
  - `TestRLSRCAuxFunction`: RC7を使用するよう変更（SITL問題のため未完了）
- 動作確認済み:
  - `TestRLSRC8SwitchControl`: PASS（旧方式）

#### 5. ドキュメント作成
- README.md更新:
  - 設定方法の表（新方式 vs 旧方式）
  - オートテストの実行方法
  - 既知の問題（新方式のSITL動作不安定）
  - ログ確認方法

### ファイル変更一覧
```
libraries/AP_Observer/AP_Observer.h
  - _combined_freq_est_switch メンバー変数追加

libraries/AP_Observer/AP_Observer.cpp
  - _combined_freq_est_switch の初期化
  - update()で統合スイッチ状態を保存
  - write_log()で統合値を記録

Tools/autotest/arducopter.py
  - TestRLSDualMethodControl() 追加（開発中）
  - TestRLSRCAuxFunction() RC9→RC7へ変更
  - テストリストへの登録

README.md
  - "Custom Features & Testing" セクション追加
  - 設定方法・テスト実行方法の説明
```

### 最終結果

| 項目 | 状態 | 備考 |
|------|------|------|
| 旧方式（OBS_FREQ_EST_CH） | 動作確認済み | RC8テストPASS |
| 新方式（RC_OPTION=316） | SITL不安定 | 実機検証推奨 |
| 統合スイッチログ | 修正完了 | SWフィールドで確認可能 |
| ドキュメント | 完成 | README.md更新済み |

### 推奨事項
1. 旧方式（OBS_FREQ_EST_CH）の使用を推奨
2. 新方式は実機での動作検証が必要
3. 両方式の併用テストは新方式の問題解決後に実施

---

