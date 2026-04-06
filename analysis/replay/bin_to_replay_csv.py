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


def extract_obsv_with_window(input_path, output_path, start_time_sec=None, end_time_sec=None):
    """Extract OBSV records within a time window (in seconds)."""
    reader = DFReader.DFReader_binary(input_path, zero_time_base=False)
    fields = ["TimeUS", "PLX", "PLY", "PLZ", "SW", "F", "P"]

    # Convert window bounds to microseconds
    start_time_us = start_time_sec * 1e6 if start_time_sec is not None else 0
    end_time_us = end_time_sec * 1e6 if end_time_sec is not None else float('inf')

    count = 0
    start_time_origin_us = None
    with open(output_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(fields)

        while True:
            msg = reader.recv_match(type="OBSV")
            if msg is None:
                break

            time_us = to_int(getattr(msg, "TimeUS", None))
            if start_time_origin_us is None:
                # Treat the first OBSV sample as t=0 for window filtering.
                start_time_origin_us = time_us

            rel_time_us = time_us - start_time_origin_us
            if not (start_time_us <= rel_time_us <= end_time_us):
                continue

            row = [
                time_us,
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
    parser.add_argument("--start-time-sec", type=float, default=None, help="Start time in seconds (relative to log start)")
    parser.add_argument("--end-time-sec", type=float, default=None, help="End time in seconds (relative to log start)")
    args = parser.parse_args()

    if args.start_time_sec is not None or args.end_time_sec is not None:
        count = extract_obsv_with_window(args.input, args.output, args.start_time_sec, args.end_time_sec)
    else:
        count = extract_obsv(args.input, args.output)

    if count == 0:
        print(f"No OBSV records found in {args.input}", file=sys.stderr)
        return 1

    if args.start_time_sec is not None or args.end_time_sec is not None:
        print(f"Extracted {count} OBSV records (window {args.start_time_sec}s-{args.end_time_sec}s): {args.output}")
    else:
        print(f"Extracted {count} OBSV records: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
