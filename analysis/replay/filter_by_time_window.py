#!/usr/bin/env python3
"""Filter replay result CSV by time window and generate windowed results."""

import argparse
import csv
import os
from typing import List, Dict


def filter_csv_by_time_window(
    input_csv: str,
    output_csv: str,
    time_start_s: float,
    time_end_s: float,
) -> int:
    """Filter CSV rows by time window. Returns number of rows written."""
    rows_written = 0
    
    with open(input_csv, 'r', newline='') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_csv) or '.', exist_ok=True)
        
        with open(output_csv, 'w', newline='') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in reader:
                try:
                    time_s = float(row.get('Time_s', 0))
                    if time_start_s <= time_s <= time_end_s:
                        writer.writerow(row)
                        rows_written += 1
                except (ValueError, TypeError):
                    continue
    
    return rows_written


def main():
    parser = argparse.ArgumentParser(
        description='Filter replay result CSV by time window'
    )
    parser.add_argument('--input', required=True, help='Input CSV path')
    parser.add_argument('--output', required=True, help='Output CSV path')
    parser.add_argument(
        '--time-start',
        type=float,
        required=True,
        help='Start time in seconds'
    )
    parser.add_argument(
        '--time-end',
        type=float,
        required=True,
        help='End time in seconds'
    )
    
    args = parser.parse_args()
    
    rows = filter_csv_by_time_window(
        args.input,
        args.output,
        args.time_start,
        args.time_end,
    )
    print(f"Filtered {rows} rows to {args.output}")


if __name__ == '__main__':
    main()
