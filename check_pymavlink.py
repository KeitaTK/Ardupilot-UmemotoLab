#!/usr/bin/env python3
"""Check pymavlink AUTOPILOT_VERSION message fields"""

from pymavlink import mavutil
import pymavlink.dialects.v20.ardupilotmega as apm

print("Checking pymavlink AUTOPILOT_VERSION message structure...")
print("")

# Get the message class
msg_class = getattr(apm, 'MAVLink_autopilot_version_message', None)
if msg_class:
    # Create a dummy instance
    msg = msg_class()
    
    # Get all fields
    fields = [f for f in dir(msg) if not f.startswith('_') and not callable(getattr(msg, f))]
    fields = [f for f in fields if f not in ['get_msgId', 'pack', 'unpack', 'to_dict', 'to_json', 'get_type']]
    
    print("AUTOPILOT_VERSION message fields in pymavlink:")
    for f in sorted(fields):
        print(f"  - {f}")
    
    # Check if 'uid' or 'uid_taki' exists
    print("")
    if 'uid' in fields:
        print("✅ 'uid' field EXISTS in pymavlink")
    else:
        print("❌ 'uid' field NOT FOUND in pymavlink")
    
    if 'uid_taki' in fields:
        print("⚠️  'uid_taki' field EXISTS in pymavlink (custom)")
    else:
        print("✅ 'uid_taki' field NOT FOUND (good - standard)")
else:
    print("ERROR: Could not find AUTOPILOT_VERSION message class")

print("")
print("pymavlink version:", apm.WIRE_PROTOCOL_VERSION if hasattr(apm, 'WIRE_PROTOCOL_VERSION') else 'unknown')
print("pymavlink file:", apm.__file__)
