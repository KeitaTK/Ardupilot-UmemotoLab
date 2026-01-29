#!/usr/bin/env python3
import sys
from pymavlink import mavutil
import csv

def extract_obs_data(bin_path, csv_path):
    print(f"Opening log file: {bin_path}")
    mlog = mavutil.mavlink_connection(bin_path)

    print(f"Writing to CSV: {csv_path}")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["TimeUS", "PLX", "PLY", "PLZ", "SW", "RealFreq", "RealPhase"])

        count = 0
        while True:
            m = mlog.recv_match(type='OBSV', blocking=False)
            if m is None:
                # Assuming EOF if None returned repeatedly, but recv_match without blocking returns None if no msg immediately available?
                # For file parsing, generic wait?
                # Actually recv_match on file returns None on EOF.
                break
            
            writer.writerow([m.TimeUS, m.PLX, m.PLY, m.PLZ, m.SW, m.F, m.P])
            count += 1
            if count % 10000 == 0:
                print(f"Processed {count} records...")

    print(f"Extraction complete. {count} records written.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: extract_csv.py <input.bin> <output.csv>")
        sys.exit(1)
    
    extract_obs_data(sys.argv[1], sys.argv[2])
