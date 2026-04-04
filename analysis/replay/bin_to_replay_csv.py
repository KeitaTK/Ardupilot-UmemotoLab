#!/usr/bin/env python3
"""Extract replay-ready OBSV CSV from a DataFlash BIN log."""

import argparse
import csv
import sys

from pymavlink import DFReader


def to_int(value, default=0):
    if value is None:
        return default
    return int(value)


def to_float(value, default=0.0):
    if value is None:
        return default
    return float(value)


def extract_obsv(input_path, output_path):
    reader = DFReader.DFReader_binary(input_path, zero_time_base=False)
    fields = ["TimeUS", "PLX", "PLY", "PLZ", "SW", "F", "P"]

    count = 0
    with open(output_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(fields)

        while True:
            msg = reader.recv_match(type="OBSV")
            if msg is None:
                break

            row = [
                to_int(getattr(msg, "TimeUS", None)),
                to_float(getattr(msg, "PLX", None)),
                to_float(getattr(msg, "PLY", None)),
                to_float(getattr(msg, "PLZ", None)),
                to_int(getattr(msg, "SW", None)),
                to_float(getattr(msg, "F", None)),
                to_float(getattr(msg, "P", None)),
            ]
            writer.writerow(row)
            count += 1

    return count


def main():
    parser = argparse.ArgumentParser(description="Convert DataFlash BIN OBSV records to replay CSV")
    parser.add_argument("--input", required=True, help="Path to input BIN file")
    parser.add_argument("--output", required=True, help="Path to output CSV file")
    args = parser.parse_args()

    count = extract_obsv(args.input, args.output)
    if count == 0:
        print(f"No OBSV records found in {args.input}", file=sys.stderr)
        return 1

    print(f"Extracted {count} OBSV records: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
