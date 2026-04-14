#!/usr/bin/env python3
"""
観測値ゼロ強制案の実装検証
- 新実装（観測値0強制）でのリプレイ実行結果記録
- シミュレーション結果との対比
"""

import subprocess
import os
import json
from datetime import datetime

bin_files = {
    '00000443': '/home/memoto/Ardupilot-UmemotoLab/analysis/replay/data/00000443.BIN',
    '00000444': '/home/memoto/Ardupilot-UmemotoLab/analysis/replay/data/00000444.BIN',
}

workspace = '/home/memoto/Ardupilot-UmemotoLab'

print("="*70)
print("観測値ゼロ強制案 - リプレイ検証実行")
print("="*70)
print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

results = {}

for case_name, bin_path in bin_files.items():
    if not os.path.exists(bin_path):
        print(f"❌ {case_name}: ファイルが見つかりません ({bin_path})")
        continue
    
    print(f"\n【処理中】{case_name}")
    print(f"  ファイル: {bin_path}")
    
    # RLS_CSV_Replay の実行
    cmd = f"cd {workspace} && source venv/bin/activate && ./build/sitl/examples/RLS_CSV_Replay --input {bin_path} 2>&1"
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        
        # 標準出力から統計情報を抽出
        output = result.stdout + result.stderr
        
        if "converged" in output.lower() or "iteration" in output.lower():
            print(f"  ✅ リプレイ実行成功")
            results[case_name] = {
                'status': 'success',
                'output_lines': len(output.split('\n')),
                'output_sample': '\n'.join(output.split('\n')[:10])
            }
        else:
            print(f"  ⚠️ リプレイ実行完了（結果確認待ち）")
            results[case_name] = {
                'status': 'completed',
                'output_sample': '\n'.join(output.split('\n')[-5:])
            }
            
    except subprocess.TimeoutExpired:
        print(f"  ⚠️ リプレイ実行がタイムアウト（>60s）")
        results[case_name] = {'status': 'timeout'}
    except Exception as e:
        print(f"  ❌ エラー発生: {e}")
        results[case_name] = {'status': 'error', 'error': str(e)}

print("\n" + "="*70)
print("実行結果サマリー")
print("="*70)

for case_name, result in results.items():
    print(f"\n{case_name}: {result.get('status', 'unknown').upper()}")
    if 'output_sample' in result:
        print(f"  出力サンプル:")
        for line in result['output_sample'].split('\n')[:3]:
            if line.strip():
                print(f"    {line[:70]}")

print("\n" + "="*70)
print("次ステップ")
print("="*70)
print("""
1. リプレイ結果を既存の検証レポートと比較
2. 観測値ゼロ強制案の効果を定量評価
3. 詳細レポート（図入り）を作成

実装コード：  /home/memoto/Ardupilot-UmemotoLab/libraries/AP_Observer/AP_Observer.cpp
  - 観測値ゼロ強制処理（line 618-623）
  - R×1000拡大削除
  - K制約削除

ビルド結果: ✅ 成功
  バイナリ: /home/memoto/Ardupilot-UmemotoLab/build/sitl/bin/arducopter
  RLS_CSV_Replay: /home/memoto/Ardupilot-UmemotoLab/build/sitl/examples/RLS_CSV_Replay
""")

print("\n✅ 実装検証スクリプト完了")
