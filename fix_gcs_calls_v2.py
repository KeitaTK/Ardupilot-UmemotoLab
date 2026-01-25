#!/usr/bin/env python3
"""
AP_Observer.cppの全てのgcs().send_text()呼び出しを#if HAL_GCS_ENABLEDでガードする（改良版）
"""
import re

def is_already_guarded(lines, current_idx):
    """
    現在の行が既にHAL_GCS_ENABLEDでガードされているかチェック
    """
    # 前方向に最大10行チェック
    for i in range(max(0, current_idx - 10), current_idx):
        line = lines[i].strip()
        if '#if HAL_GCS_ENABLED' in line:
            # #endifが間にないかチェック
            for j in range(i + 1, current_idx):
                if '#endif' in lines[j].strip():
                    return False
            return True
    return False

def find_matching_endif(lines, start_idx):
    """
    対応する#endifの位置を見つける
    """
    depth = 1
    for i in range(start_idx + 1, len(lines)):
        line = lines[i].strip()
        if line.startswith('#if'):
            depth += 1
        elif line.startswith('#endif'):
            depth -= 1
            if depth == 0:
                return i
    return None

def fix_gcs_calls(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    result = []
    skip_until = -1
    
    for i in range(len(lines)):
        # スキップ範囲内ならスキップ
        if i < skip_until:
            continue
        
        line = lines[i]
        
        # コメント行はそのまま
        if line.strip().startswith('//'):
            result.append(line)
            continue
        
        # gcs().send_text()呼び出しを検出
        if 'gcs().send_text(' in line and not line.strip().startswith('//'):
            # 既にガードされているかチェック
            if is_already_guarded(result + lines[i:], len(result)):
                result.append(line)
                continue
            
            # インデントを取得
            indent_match = re.match(r'^(\s*)', line)
            indent = indent_match.group(1) if indent_match else ''
            
            # gcs().send_text()の終わりを見つける（;まで）
            gcs_lines = [line]
            j = i + 1
            while j < len(lines) and ');' not in lines[j-1]:
                gcs_lines.append(lines[j])
                j += 1
            
            # ガードを追加
            result.append(f'{indent}#if HAL_GCS_ENABLED\n')
            result.extend(gcs_lines)
            result.append(f'{indent}#endif\n')
            
            # スキップ位置を更新
            skip_until = j
        else:
            result.append(line)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(result)
    
    print(f"Fixed GCS calls in {input_file} -> {output_file}")

if __name__ == '__main__':
    fix_gcs_calls(
        '/home/memoto/Ardupilot-UmemotoLab/libraries/AP_Observer/AP_Observer.cpp.backup',
        '/home/memoto/Ardupilot-UmemotoLab/libraries/AP_Observer/AP_Observer.cpp'
    )
