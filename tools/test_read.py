import logging

from pymodbus.client import ModbusTcpClient

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)


def test_read():
    print("Connecting to localhost:5020...")
    client = ModbusTcpClient("localhost", port=5020)
    client.connect()

    # Read Address 4
    # Try different slave IDs or offsets if needed
    print("Reading Address 4...")
    rr = client.read_holding_registers(4, count=1, device_id=1)
    if rr.isError():
        print(f"Error: {rr}")
    else:
        print(f"Address 4 Value: {rr.registers[0]}")

    # Read Address 0 just in case
    print("Reading Address 0...")
    rr = client.read_holding_registers(0, count=1, device_id=1)
    if not rr.isError():
        print(f"Address 0 Value: {rr.registers[0]}")

    client.close()


if __name__ == "__main__":
    test_read()
