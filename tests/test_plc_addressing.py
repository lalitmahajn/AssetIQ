import sys
import os

sys.path.append(os.getcwd())
import unittest
from unittest.mock import MagicMock
from apps.plant_backend.plc_service import read_tag_value


class TestPLCAddressing(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock()
        self.slave_id = 1

    def test_read_coil(self):
        # 0xxxx -> read_coils
        tag = MagicMock()
        tag.address = 100
        tag.data_type = "BOOL"
        tag.multiplier = 1.0
        tag.tag_name = "test_coil"

        # Mock return
        res = MagicMock()
        res.isError.return_value = False
        res.bits = [True]
        self.client.read_coils.return_value = res

        val = read_tag_value(self.client, tag, self.slave_id)

        self.client.read_coils.assert_called_with(100, count=1, device_id=1)
        self.assertEqual(val, 1)

    def test_read_discrete_input(self):
        # 1xxxx -> read_discrete_inputs (offset 10000)
        tag = MagicMock()
        tag.address = 10005
        tag.data_type = "BOOL"
        tag.multiplier = 1.0
        tag.tag_name = "test_di"

        res = MagicMock()
        res.isError.return_value = False
        res.bits = [False]
        self.client.read_discrete_inputs.return_value = res

        val = read_tag_value(self.client, tag, self.slave_id)

        self.client.read_discrete_inputs.assert_called_with(5, count=1, device_id=1)
        self.assertEqual(val, 0)

    def test_read_input_register(self):
        # 3xxxx -> read_input_registers (offset 30000)
        tag = MagicMock()
        tag.address = 30010
        tag.data_type = "INT16"
        tag.multiplier = 0.1
        tag.tag_name = "test_ir"

        res = MagicMock()
        res.isError.return_value = False
        res.registers = [1234]
        self.client.read_input_registers.return_value = res

        val = read_tag_value(self.client, tag, self.slave_id)

        self.client.read_input_registers.assert_called_with(10, count=1, device_id=1)
        self.assertAlmostEqual(val, 123.4)

    def test_read_holding_register(self):
        # 4xxxx -> read_holding_registers (offset 40001)
        tag = MagicMock()
        tag.address = 40020
        tag.data_type = "INT16"
        tag.multiplier = 1.0
        tag.tag_name = "test_hr"

        res = MagicMock()
        res.isError.return_value = False
        res.registers = [555]
        self.client.read_holding_registers.return_value = res

        val = read_tag_value(self.client, tag, self.slave_id)

        self.client.read_holding_registers.assert_called_with(19, count=1, device_id=1)
        self.assertEqual(val, 555)

    def test_read_raw_holding_register(self):
        # >= 50000 -> read_holding_registers (raw)
        tag = MagicMock()
        tag.address = 50000
        tag.data_type = "INT16"
        tag.multiplier = 1.0
        tag.tag_name = "test_raw"

        res = MagicMock()
        res.isError.return_value = False
        res.registers = [999]
        self.client.read_holding_registers.return_value = res

        val = read_tag_value(self.client, tag, self.slave_id)

        self.client.read_holding_registers.assert_called_with(50000, count=1, device_id=1)
        self.assertEqual(val, 999)


if __name__ == "__main__":
    unittest.main()
