# predict-only 時の共分散爆発リスク - 修正案

## 問題の再確認
- predict-only フェーズが 20 秒以上続くと、共分散 P[0,0] が 5 倍以上増加
- いったん観測更新に戻ると、Kalman ゲイン K が 0.5~1.0 に達する
- 結果として、推定振幅が過度に更新される

## 推奨される修正案

### 修正案 A: Kalman ゲイン K の事前防御チェック（推奨）

**場所**: `ekf_update_axis()` の観測更新時（line ~620-625）

**実装概要**:
```cpp
// 観測更新前のゲインチェック
float K_max_mag = 0.0f;
for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
    K_max_mag = MAX(K_max_mag, fabsf(K[i]));
}

if (K_max_mag > K_GAIN_THRESHOLD) {
    // ゲインが大きすぎる場合は観測更新をスキップ
    // または強行的に K を制約
    for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
        K[i] = constrain_value(K[i], -0.1f, 0.1f);
    }
    // ログ出力
    gcs().send_text(MAV_SEVERITY_WARNING, 
        "EKF[%d]: K gain too large (max=%.3f), clamping", 
        axis, (double)K_max_mag);
}
```

**パラメータ**:
- `K_GAIN_THRESHOLD = 0.5f` (推奨)
- または、新しいパラメータ `_ekf_k_max_gain` を追加

**利点**:
- シンプルで実装が容易
- predict-only フェーズの共分散増加を許容しつつ、観測更新時の暴走を防止
- 既存コードへの変更が最小限

### 修正案 B: 共分散の最大値制約（追加対策）

**場所**: `ekf_update_axis()` の共分散更新時（line ~550-575）

**実装概要**:
```cpp
// 共分散に上限を設定（predict-only 中の無限増加を抑制）
const float P_MAX = 10.0f; // 例：最大分散 = 10.0
for (uint8_t i = 0; i < EKF_STATE_SIZE; i++) {
    for (uint8_t j = 0; j < EKF_STATE_SIZE; j++) {
        if (fabsf(P_pred[i][j]) > P_MAX) {
            P_pred[i][j] = (P_pred[i][j] > 0) ? P_MAX : -P_MAX;
        }
    }
}
```

**パラメータ**:
- `P_MAX` は パラメータ化またはハードコード

**利点**:
- predict-only フェーズでの共分散増加を root から防止
- より根本的な解決

**欠点**:
- 共分散の上限が固定されるため、長期飛行で有効性が失われるかもしれない

### 修正案 C: predict-only 継続時間の監視（オプション）

**場所**: `ekf_update_axis()` または新しい関数

**実装概要**:
```cpp
// predict-only 継続時間をカウント
static uint16_t predict_only_count[EKF_AXIS_COUNT] = {0};

if (predict_only_hold) {
    predict_only_count[axis]++;
    
    // 連続 predict-only が 5000 ステップ以上なら警告
    if (predict_only_count[axis] > 5000) {
        if (predict_only_count[axis] % 1000 == 0) {
            gcs().send_text(MAV_SEVERITY_WARNING,
                "EKF[%d]: predict-only for %.1f sec (P[0,0]=%.4f)",
                axis, predict_only_count[axis] * dt, P[0,0]);
        }
    }
} else {
    predict_only_count[axis] = 0;
}
```

**利点**:
- 運用上の問題を早期発見できる
- ログに記録されるため、実飛行での挙動を診断可能

## 最終推奨手順

### Phase 1: 即座の修正（修正案 A）
1. Kalman ゲイン K の事前チェック機能を追加
2. パラメータ `_ekf_k_max_gain` を定義（デフォルト 0.5）
3. 既存の 4 つのテストケースで検証

### Phase 2: 強化（修正案 B）
1. 共分散クリップ機能を追加
2. パラメータ `_ekf_p_max` を定義
3. extended テストで検証

### Phase 3: 運用サポート（修正案 C）
1. predict-only 監視ログを追加
2. ユーザーマニュアルに条件記載

## テスト戦略（修正後）

1. **単体テスト**:
   - predict-only 2000+ ステップで K が制約される確認
   - K が制約された後も推定値が安定している確認

2. **既存テストケースの回帰テスト**:
   - 00000443, 00000444 baseline/model-strong が依然パス
   - RMSE、相関が悪化していないか確認

3. **新規テストケース**:
   - predict-only が何千ステップも続くシナリオ
   - 観測更新に戻った後の推定振幅の安定性
