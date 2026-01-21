import inspect

from pymodbus.client import ModbusTcpClient

print("Inspecting ModbusTcpClient.read_holding_registers...")
sig = inspect.signature(ModbusTcpClient.read_holding_registers)
print(f"Signature: {sig}")

print("Parameters details:")
for name, param in sig.parameters.items():
    print(f" - {name}: {param.kind} (Default: {param.default})")
