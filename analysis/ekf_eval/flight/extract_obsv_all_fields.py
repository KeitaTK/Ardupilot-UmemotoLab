#!/usr/bin/env python3
"""
OBSV メッセージの全フィールドを動的に抽出するスクリプト。

既存の bin_to_obsv_csv.py はフィールドをハードコードしているため、
PRX/PRY など追加フィールドを含む BIN に対応できない。
本スクリプトは最初の OBSV メッセージから全フィールド名を動的に取得し、
全 OBSV レコードを CSV に書き出す。
"""

import argparse
import csv
import sys
from pathlib import Path

from pymavlink import DFReader


def to_float(value, default=0.0):
    if value is None:
        return default
    return float(value)


def to_int(value, default=0):
    if value is None:
        return default
    return int(value)


def extract_obsv_all_fields(input_path: str, output_path: str) -> int:
    """OBSV メッセージの全フィールドを動的に抽出して CSV に書き出す。"""
    reader = DFReader.DFReader_binary(input_path, zero_time_base=False)

    # 最初の OBSV メッセージから全フィールド名を取得
    first_msg = reader.recv_match(type="OBSV")
    if first_msg is None:
        print(f"No OBSV messages found in {input_path}", file=sys.stderr)
        return 0

    # 全フィールド名を動的に取得（mavfield から）
    field_names = sorted(first_msg._fieldnames)  # type: ignore
    # TimeUS が先頭に来るように並べ替え
    if "TimeUS" in field_names:
        field_names.remove("TimeUS")
        field_names.insert(0, "TimeUS")

    print(f"Detected OBSV fields: {field_names}")

    count = 0
    with open(output_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        # ヘッダー行 + Time_s 列
        header = field_names + ["Time_s"]
        writer.writerow(header)

        # 最初のメッセージを書き出し
        first_time_us = to_int(getattr(first_msg, "TimeUS", None))
        row = []
        for fn in field_names:
            val = getattr(first_msg, fn, None)
            if isinstance(val, int):
                row.append(to_int(val))
            else:
                row.append(to_float(val))
        row.append(0.0)  # Time_s = 0 for first sample
        writer.writerow(row)
        count += 1

        # 残りの OBSV メッセージを走査
        while True:
            msg = reader.recv_match(type="OBSV")
            if msg is None:
                break

            time_us = to_int(getattr(msg, "TimeUS", None))
            row = []
            for fn in field_names:
                val = getattr(msg, fn, None)
                if isinstance(val, int):
                    row.append(to_int(val))
                else:
                    row.append(to_float(val))
            row.append((time_us - first_time_us) / 1e6)
            writer.writerow(row)
            count += 1

    return count


def main():
    parser = argparse.ArgumentParser(
        description="Extract all OBSV fields from a DataFlash BIN log to CSV"
    )
    parser.add_argument("--input", required=True, help="Path to input BIN file")
    parser.add_argument("--output", required=True, help="Path to output CSV file")
    args = parser.parse_args()

    count = extract_obsv_all_fields(args.input, args.output)
    if count == 0:
        print(f"No OBSV records found in {args.input}", file=sys.stderr)
        return 1

    print(f"Extracted {count} OBSV records: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
