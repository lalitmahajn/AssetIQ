import logging

from pymodbus.datastore import ModbusDeviceContext, ModbusSequentialDataBlock

logging.basicConfig()

print("Testing ModbusDeviceContext Initialization...")
try:
    # Use Sequential with 1s to be sure
    regs = [1] * 10
    block = ModbusSequentialDataBlock(0, regs)
    print(f"Block Values: {block.getValues(0, 10)}")

    # Attempt 1: Positional
    print("\n--- Attempt 1: Positional (di, co, ir, hr) ---")
    store1 = ModbusDeviceContext(block, block, block, block)
    val = store1.getValues(3, 4, 1)  # HR
    print(f"getValues(3, 4, 1): {val}")

    # Attempt 2: Keywords
    print("\n--- Attempt 2: Keywords (hr=block) ---")
    store2 = ModbusDeviceContext(hr=block, ir=block)
    val = store2.getValues(3, 4, 1)  # HR
    print(f"getValues(3, 4, 1): {val}")

    # Attempt 3: Mixed/Defaults
    print("\n--- Attempt 3: Just HR ---")
    store3 = ModbusDeviceContext(hr=block)
    val = store3.getValues(3, 4, 1)  # HR
    print(f"getValues(3, 4, 1): {val}")

except Exception as e:
    print(f"Error: {e}")
