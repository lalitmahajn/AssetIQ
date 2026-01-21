import logging

from pymodbus.datastore import ModbusDeviceContext, ModbusSparseDataBlock

logging.basicConfig()

print("Testing ModbusSparseDataBlock & ModbusDeviceContext...")
try:
    data = {4: 1, 0: 45}
    block = ModbusSparseDataBlock(data)
    print(f"Created block with data: {data}")

    # Check block directly
    print(f"block.getValues(0, 5): {block.getValues(0, 5)}")
    print(f"block.values: {block.values}")

    # Check DeviceContext
    # Positional args: di, co, ir, hr
    store = ModbusDeviceContext(block, block, block, block)

    # Check HR (function code 3)
    vals = store.getValues(3, 4, 1)
    print(f"DeviceContext.getValues(3, 4, 1): {vals}")

    # Try attribute access if it worked for others
    # (Step 545 said no attribute 'hr')

except Exception as e:
    print(f"Error: {e}")
