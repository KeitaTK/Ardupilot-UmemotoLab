# AP_Observer ライブラリ設定・実装まとめ

最終更新日: 2026年1月25日

## 📋 概要
AP_Observerは外力推定と姿勢補正を行うArduPilot用ライブラリです。
RLS（Recursive Least Squares）アルゴリズムにより周期的外力（振り子荷物など）を推定し、機体の姿勢補正に利用します。

---

## ⚙️ パラメータ一覧

### 基本パラメータ

| パラメータ名 | デフォルト値 | 範囲 | 説明 |
|------------|------------|------|------|
| `OBS_CORR_GAIN` | 0.004 | 0.0-1.0 | 姿勢補正ゲイン |
| `OBS_FILT_CUTOFF` | 20.0 | 1.0-100.0 | ローパスフィルタのカットオフ周波数 [Hz] |

### RLS推定パラメータ

| パラメータ名 | デフォルト値 | 範囲 | 説明 |
|------------|------------|------|------|
| `OBS_RLS_LAMBDA` | 0.98 | 0.9-0.9999 | RLS忘却係数（大きいほど過去データを重視） |
| `OBS_RLS_COV_INIT` | 100.0 | 0.001-1000.0 | RLS初期共分散値 |
| `OBS_DIST_FREQ` | 0.6 | 0.35-0.91 | 外乱周波数の初期値 [Hz] |
| `OBS_PRED_TIME` | 0.01 | 0.0-0.5 | 予測時間（先読み時間） [秒] |

### 位相補正パラメータ

| パラメータ名 | デフォルト値 | 範囲 | 説明 |
|------------|------------|------|------|
| `OBS_PHASE_CORR` | 1 | 0/1 | 位相補正の有効/無効 |
| `OBS_PHASE_THRESH` | 0.0 | 0.0-5.0 | 位相補正閾値 [rad]（現在は実質無効化） |

### RC制御パラメータ

| パラメータ名 | デフォルト値 | 範囲 | 説明 |
|------------|------------|------|------|
| `OBS_FREQ_EST_CH` | 8 | 0-16 | 周波数推定制御用RCチャンネル番号（0=無効） |

### テストパラメータ

| パラメータ名 | デフォルト値 | 範囲 | 説明 |
|------------|------------|------|------|
| `OBS_TEST_INJECT` | 0 | 0/1 | テスト用外力注入の有効/無効 |
| `OBS_TEST_FREQ` | 0.7 | 0.35-0.91 | テスト用外力の周波数 [Hz] |
| `OBS_TEST_AMP` | 1.0 | 0.0-10.0 | テスト用外力の振幅 [N] |

---

## 🎛️ 周波数推定のRC制御

### 動作仕様
- **RC8スイッチ（`OBS_FREQ_EST_CH`）** で周波数推定のオン/オフを制御
- **PWM閾値**:
  - 1700以上: スイッチオン（推定実行中）
  - 1300以下: スイッチオフ（推定停止・結果保持）

### テストモードの特別動作
`OBS_TEST_INJECT = 1` の場合、RC8スイッチの状態に関わらず、常にRLS更新と位相補正が実行されます。
これによりオートテスト（TestRLSBasicEstimation等）が正常に動作します。

### 動作フロー

```
[初期状態]
  ↓
  周波数 = OBS_DIST_FREQ（初期設定値）

[RC8スイッチ: オフ→オン]
  ↓
  推定開始
  - RLSパラメータリセット
  - 位相補正リセット
  - 周波数を初期値に戻す
  ↓
[推定実行中]
  - RLS更新を実行
  - 位相補正を実行
  - estimated_frequencyを更新
  ↓
[RC8スイッチ: オン→オフ]
  ↓
  推定終了
  - 推定周波数を保持（_freq_estimation_result）
  - RLS更新停止
  - 保持された周波数で予測を継続

[RC8スイッチ: 再びオフ→オン]
  ↓
  推定再開（周波数を初期値にリセット）
```

---

## 📊 ログフォーマット

### OBSV ログ

| フィールド | 型 | 説明 | 単位 |
|-----------|---|------|------|
| TimeUS | uint64 | タイムスタンプ | μs |
| PLX | float | ペイロード外力 X軸 | N |
| PLY | float | ペイロード外力 Y軸 | N |
| PLZ | float | ペイロード外力 Z軸 | N |
| AX | float | RLS sin係数 X軸 | - |
| AY | float | RLS sin係数 Y軸 | - |
| BX | float | RLS cos係数 X軸 | - |
| BY | float | RLS cos係数 Y軸 | - |
| CX | float | RLS 定常偏差 X軸 | N |
| CY | float | RLS 定常偏差 Y軸 | N |
| F | float | 推定周波数（または設定周波数） | Hz |
| P | float | 位相補正量 | rad |
| X | float | 観測位相 X軸 | rad |
| Y | float | 観測位相 Y軸 | rad |
| **SW** | uint8 | **RC8スイッチ状態（0=オフ、1=オン）** | - |

**注意**: SW フィールドは新規追加されました。

---

## 🔧 主要な定数

### システム定数

| 定数名 | 値 | 説明 |
|--------|---|------|
| `TIMEOUT_MS` | 500 | 補正タイムアウト [ms] |
| `FORCE_THRESHOLD` | 0.2 | 外力閾値 [N] |
| `MAX_CORRECTION_ANGLE` | 0.5 | 最大補正角 [rad] |
| `g` | 9.7985 | 重力加速度 [m/s²] |
| `THRUST_SCALE` | 6.3157 | スラスト換算係数 |
| `THRUST_OFFSET` | -0.9995 | スラストオフセット |
| `UAV_mass` | 1.4 | 機体質量 [kg] |

### RLS定数

| 定数名 | 値 | 説明 |
|--------|---|------|
| `RLS_PARAM_SIZE` | 3 | RLSパラメータ数（A, B, C） |
| `RLS_NUM_AXES` | 3 | 軸数（X, Y, Z） |
| `RLS_MIN_LAMBDA` | 0.9 | 忘却係数最小値 |
| `RLS_MAX_LAMBDA` | 0.9999 | 忘却係数最大値 |
| `RLS_MIN_COVARIANCE` | 0.001 | 共分散最小値 |
| `RLS_MAX_COVARIANCE` | 1000.0 | 共分散最大値 |

### 周波数範囲

| 定数名 | 値 | 対応振り子長 | 説明 |
|--------|---|------------|------|
| `FREQ_MIN` | 0.35 Hz | 2.0 m | 最小周波数 |
| `FREQ_MAX` | 0.91 Hz | 0.3 m | 最大周波数 |

**周波数と振り子長の関係**: f = (1/2π)√(g/L)

### 位相補正定数

| 定数名 | 値 | 説明 |
|--------|---|------|
| `PHASE_BUFFER_SIZE` | 100 | 位相バッファサイズ（1.0秒分） |
| `AB_PHASE_MIN_AMP_INIT` | 1.0e-4 N | 位相unwrap初期化用最小振幅 |
| `AB_PHASE_MIN_AMP_BUF` | 1.0 N | 位相バッファ投入用最小振幅 |
| `FREQ_EST_ALPHA` | 0.20 | 周波数推定の追従速度（0-1） |

---

## 🧮 アルゴリズム詳細

### RLS推定モデル

推定モデル式:
```
y(t) = A·sin(ωt - φ) + B·cos(ωt - φ) + C
```

ここで:
- `y(t)`: 観測外力 [N]
- `A, B`: 正弦波・余弦波係数（振幅と位相に関連）
- `C`: 定常偏差
- `ω`: 角周波数 [rad/s] = 2πf
- `φ`: 位相補正量 [rad]

振幅と位相の関係:
```
振幅 R = √(A² + B²)
位相 φ_obs = atan2(B, A)
```

### 位相補正アルゴリズム

1. **位相バッファへの蓄積**: 100サンプル（約1秒分）
2. **線形回帰**: 時刻-位相データで傾き（角周波数差）を計算
3. **周波数差計算**: Δf = slope / (2π)
4. **周波数更新**: f_new = f_old + α·Δf（α=0.20）
5. **位相補正更新**: φ_correction -= phase_error

**注意**: 
- 閾値による自動リセット機能は無効化されています
- RC8スイッチによる手動制御を使用してください

---

## 🚀 使用方法

### 1. RC8スイッチの設定
Mission Plannerまたは地上局で:
```
OBS_FREQ_EST_CH = 8
```

RC送信機でRC8チャンネルを2ポジションスイッチに割り当て。

### 2. 推定の実行手順

1. **離陸前**: RC8スイッチをオフ位置
2. **離陸**: 機体をアーム・離陸
3. **推定開始**: RC8スイッチをオン
   - RLSパラメータがリセットされ、推定開始
4. **推定実行**: 十分な時間（30秒～1分程度）待つ
5. **推定終了**: RC8スイッチをオフ
   - 推定周波数が保持され、以降はその周波数で予測を継続

### 3. 再推定

再度推定したい場合:
1. RC8スイッチを再びオン
   - 周波数が初期値にリセットされ、新たに推定開始
2. 十分に待つ
3. RC8スイッチをオフ

---

## 🔍 デバッグメッセージ

### GCSメッセージ

| メッセージ | 意味 |
|-----------|------|
| `FreqEst: Started (init=X.XXXHz)` | 推定開始（初期周波数） |
| `FreqEst: Stopped (result=X.XXXHz)` | 推定終了（推定結果） |
| `PhaseCorr: f=X.XXX est=X.XXX (df=X.XXX)` | 周波数推定状況 |
| `PhaseCorr: err=X.XXXX est_freq=X.XXXX Hz corr=X.XXXX` | 位相補正実行 |
| `PhaseCorr: buffer X/100` | 位相バッファ状態 |

---

## ⚠️ 重要な注意事項

### 閾値リセット機能の無効化
- **以前の実装**: 周波数が範囲外になると自動的にリセット
- **現在の実装**: 範囲外でも警告のみ、リセットしない
- **理由**: RC8スイッチによる明示的な制御を優先

### RLS更新条件
RLS更新は以下の場合に実行されます：
1. **離陸後** かつ **RC8スイッチがオン**
2. **離陸後** かつ **テストモード有効（`OBS_TEST_INJECT=1`）**

通常運用ではRC8スイッチで制御し、テストモードではスイッチに関わらず常に更新されます。

### 推定の安定性
- 振幅が `AB_PHASE_MIN_AMP_BUF (1.0N)` 以上のサンプルのみ使用
- 外れ値の影響を抑制するため、周波数差を±0.5Hzに制限
- バッファが満杯（100サンプル）になるまで位相補正は実行されない

### RC8スイッチの動作
- チャンネルが0の場合は機能無効（常にオフ扱い）
- PWMが1700未満1300超の「中間」状態は、直前の状態を保持

---

## 📚 参考情報

### ファイル構成
```
libraries/AP_Observer/
├── AP_Observer.h           # ヘッダーファイル
├── AP_Observer.cpp         # 実装ファイル
├── wscript                 # ビルドスクリプト
└── README.md              # このファイル
```

### 依存ライブラリ
- AP_Common
- AP_Param
- AP_Math
- AP_InertialSensor
- AP_Motors
- GCS_MAVLink
- Filter (LowPassFilter2p)
- AP_Logger
- RC_Channel

### 更新履歴

#### 2026年1月25日
- RC8スイッチによる周波数推定制御機能を追加
- 閾値による自動リセット機能を無効化
- ログにスイッチ状態（SW）フィールドを追加
- `OBS_FREQ_EST_CH` パラメータを追加（デフォルト=8）
- **新規オートテスト追加**:
  - `TestRLSRC8SwitchControl`: RC8スイッチの動作を検証
  - `TestRLSWindowedEstimation`: 20-30秒の特定期間のみ推定する動作を検証

---

## 🧪 オートテスト

### 利用可能なテスト

AP_Observerライブラリには以下のオートテストが用意されています：

| テスト名 | 説明 | 実行時間 |
|---------|------|----------|
| `test.Copter.TestRLSBasicEstimation` | RLS基本推定テスト（既知周波数） | ~15秒 |
| `test.Copter.TestRLSFrequencyEstimation` | 周波数推定テスト（位相補正あり） | ~150秒 |
| `test.Copter.TestRLSFrequencyEstimationMulti` | 複数ケース周波数推定テスト | ~600秒 |
| **`test.Copter.TestRLSRC8SwitchControl`** | **RC8スイッチ制御テスト** | **~60秒** |
| **`test.Copter.TestRLSWindowedEstimation`** | **ウィンドウ推定テスト（20-30秒）** | **~60秒** |

### 新規テストの詳細

#### TestRLSRC8SwitchControl
RC8スイッチによる周波数推定の制御機能を検証します。

**テストシナリオ**:
1. RC8オフで離陸・10秒ホバリング（推定なし）
2. RC8をオンにして30秒推定
3. RC8をオフにして10秒ホバリング（推定停止、結果保持）

**検証項目**:
- 各フェーズでログの`SW`フィールドが正しく記録されているか
- RC8オン時に周波数推定が実行されているか
- RC8オフ時に推定が停止し、結果が保持されているか

#### TestRLSWindowedEstimation
特定の時間ウィンドウ（20-30秒）のみで推定を実行する機能を検証します。
実際のフライトログ（`logs/Pixhawk6CLogs/00000422.BIN`）を参考に設計されています。

**テストシナリオ**:
1. 0秒: 離陸（RC8オフ）
2. 0-20秒: RC8オフ（推定なし）
3. 20秒: RC8をオン
4. 20-30秒: 推定実行
5. 30秒: RC8をオフ
6. 30-40秒: 推定停止、結果保持

**検証項目**:
- 20-30秒の期間のみ`SW=1`が記録されているか
- 推定期間で周波数が変化しているか
- RLS振幅が適切か
- 保持期間で周波数が安定しているか

### テスト実行方法

```bash
# 仮想環境を有効化
cd /home/memoto/Ardupilot-UmemotoLab
source venv_ardupilot/bin/activate

# 個別テスト実行
timeout 600 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.TestRLSRC8SwitchControl
timeout 600 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.TestRLSWindowedEstimation

# 全テスト実行
timeout 300 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.ArmFeatures
timeout 600 Tools/autotest/autotest.py --no-clean build.Copter test.Copter.TestRLSBasicEstimation
```

### テスト結果（2026年1月25日）

すべてのテストが正常にPASSしました：
- ✅ `test.Copter.ArmFeatures` - PASSED
- ✅ `test.Copter.TestRLSBasicEstimation` - PASSED（RLS振幅10.0N確認）
- ✅ `test.Copter.TestRLSRC8SwitchControl` - PASSED（RC8制御正常動作確認）
- ✅ `test.Copter.TestRLSWindowedEstimation` - PASSED（20-30秒ウィンドウ推定確認）

---

## 🛠️ トラブルシューティング

### 推定が開始されない
- RC8スイッチが正しく接続されているか確認
- `OBS_FREQ_EST_CH` パラメータが正しく設定されているか確認
- 機体がアーム（離陸）しているか確認

### 推定周波数が不安定
- 振幅が十分大きいか確認（1.0N以上推奨）
- 推定時間を長くする（30秒～1分）
- 外乱が周期的かどうか確認

### ログにSWフィールドが表示されない
- 最新のビルドを使用しているか確認
- ログフォーマットが更新されているか確認

---

**作成者**: AP_Observer開発チーム  
**ライセンス**: ArduPilot License (GPLv3)
