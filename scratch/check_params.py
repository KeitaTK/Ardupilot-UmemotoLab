import sys
from pymavlink import DFReader

input_path = "/home/umemoto/Ardupilot-UmemotoLab/analysis/ekf_eval/flight/data/bin/00000078.BIN"
reader = DFReader.DFReader_binary(input_path, zero_time_base=False)

params = {}
while True:
    msg = reader.recv_match(type="PARM")
    if msg is None:
        break
    name = getattr(msg, "Name", "")
    if name.startswith("OBS_EKF"):
        params[name] = getattr(msg, "Value", 0.0)

for k, v in params.items():
    print(f"{k}: {v}")
