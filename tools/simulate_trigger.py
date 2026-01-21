import logging

from pymodbus.datastore import ModbusDeviceContext, ModbusSequentialDataBlock, ModbusServerContext
from pymodbus.server import StartTcpServer

# Configure logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)


import random
import threading
import time


def update_values(context):
    """Updates context values periodically"""
    print("Starting dynamic value updates...")
    slave_id = 0x01  # default slave id

    counter = 0
    while True:
        try:
            # Get slave context
            slave_ctx = context[slave_id]

            # Update registers 0-10
            # Register 0: 0-100 counter
            # Register 1: Random value 100-200
            # Register 2: Sine-ish wave

            vals = [
                counter % 100,  # Reg 0
                random.randint(100, 200),  # Reg 1
                int((counter % 20) * 5),  # Reg 2
                1000 + counter,  # Reg 3
                1,  # Reg 4 (Keep as 1 if used for trigger logic)
            ]

            # Write to Holding Registers (40001...) which are mapped to 0-offset in memory
            slave_ctx.setValues(3, 0, vals)  # 3 = Holding Register, 0 = Start Address

            # Also update a specific high register if they use 40001+
            # Let's update 0-10 just to be safe

            print(f"Updated Registers: {vals}")

            counter += 1
            time.sleep(2)
        except Exception as e:
            print(f"Update error: {e}")
            time.sleep(2)


def run_server():
    print("Preparing Mock PLC (Foolproof - Sequential + Keywords)...")

    # All registers = 1
    # Ensures Address 4 is 1. Address 0 is 1.
    registers = [1] * 100

    # Create block
    block = ModbusSequentialDataBlock(0, registers)

    # Store: MUST USE KEYWORDS!
    store = ModbusDeviceContext(hr=block, ir=block, co=block, di=block)

    # Server Context
    context = ModbusServerContext(devices=store, single=True)

    print("-" * 40)
    print("MOCK PLC RUNNING ON PORT 5020")
    print("ALL REGISTERS SET TO 1")
    print("-" * 40)

    address = ("0.0.0.0", 5020)

    # Start updater thread
    t = threading.Thread(target=update_values, args=(context,))
    t.daemon = True
    t.start()

    StartTcpServer(context=context, address=address)


if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("Server stopped")
    except Exception as e:
        print(f"Error: {e}")
