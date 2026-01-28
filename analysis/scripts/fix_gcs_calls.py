#!/usr/bin/env python3
"""
AP_Observer.cppの全てのgcs().send_text()呼び出しを#if HAL_GCS_ENABLEDでガードする
"""
import re

def fix_gcs_calls(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # コメント行はスキップ
        if line.strip().startswith('//'):
            result.append(line)
            i += 1
            continue
        
        # gcs().send_text()呼び出しを検出
        if 'gcs().send_text(' in line:
            # 既にHAL_GCS_ENABLEDでガードされているかチェック
            # 前の行または前々行に#if HAL_GCS_ENABLEDがあればスキップ
            already_guarded = False
            if i >= 1 and '#if HAL_GCS_ENABLED' in lines[i-1]:
                already_guarded = True
            elif i >= 2 and '#if HAL_GCS_ENABLED' in lines[i-2]:
                already_guarded = True
            
            if already_guarded:
                result.append(line)
                i += 1
                continue
            
            # インデントを取得
            indent_match = re.match(r'^(\s*)', line)
            indent = indent_match.group(1) if indent_match else ''
            
            # gcs().send_text()が複数行に渡っているか確認
            if ')' not in line:
                # 複数行の場合
                gcs_block = [line]
                i += 1
                while i < len(lines) and ')' not in lines[i-1]:
                    gcs_block.append(lines[i])
                    i += 1
                
                # ガードを追加
                result.append(f'{indent}#if HAL_GCS_ENABLED\n')
                result.extend(gcs_block)
                result.append(f'{indent}#endif\n')
            else:
                # 単一行の場合
                result.append(f'{indent}#if HAL_GCS_ENABLED\n')
                result.append(line)
                result.append(f'{indent}#endif\n')
                i += 1
        else:
            result.append(line)
            i += 1
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(result)
    
    print(f"Fixed GCS calls in {input_file} -> {output_file}")

if __name__ == '__main__':
    fix_gcs_calls(
        '/home/memoto/Ardupilot-UmemotoLab/libraries/AP_Observer/AP_Observer.cpp.backup',
        '/home/memoto/Ardupilot-UmemotoLab/libraries/AP_Observer/AP_Observer.cpp'
    )
