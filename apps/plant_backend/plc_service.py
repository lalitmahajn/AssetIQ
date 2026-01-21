import logging
import time
import traceback
from datetime import datetime

from pymodbus.client import ModbusSerialClient, ModbusTcpClient
from sqlalchemy import String, cast, select

from apps.plant_backend import services
from apps.plant_backend.models import PLCConfig, PLCTag, StopQueue
from common_core.db import PlantSessionLocal

# Basic logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("plc_service")

# Global cache for latest values: {plc_id: {tag_name: value}}
LATEST_VALUES = {}


def get_client(config):
    if config.protocol == "MODBUS_TCP":
        return ModbusTcpClient(config.ip_address, port=config.port or 502)
    elif config.protocol == "MODBUS_RTU":
        return ModbusSerialClient(
            port=config.serial_port, baudrate=config.baud_rate or 9600, framer="rtu"
        )
    return None


def read_tag_value(client, tag, slave_id):
    try:
        # Simplification: Assume Holding Registers for now.
        # Ideally, we should support Coil/Input/Holding based on address range or config
        # Here: Address 0-9999 = Output Coils (1), 10000-19999 = Input (2), 30000 = Input Reg (4), 40000 = Holding (3)
        # For simplicity in this v1: We assume Holding Registers (40000 offset or just raw address)

        # Read 1 register for FLOAT might need 2 registers, but let's assume BOOL/INT16 is 1 reg
        count = 1
        if tag.data_type == "FLOAT32":
            count = 2

        # Modbus address usually 0-indexed in pymodbus, but users might enter 1-indexed (e.g. 40001)
        # We will assume user enters raw address 0-65535

        # We will assume user enters raw address 0-65535

        # Pymodbus 3.11+ uses 'device_id' instead of 'slave' or 'unit'.
        # We also need to retrieve 'count' as keyword argument
        rr = client.read_holding_registers(tag.address, count=count, device_id=slave_id)

        if rr.isError():
            logger.error(f"Error reading tag {tag.tag_name}: {rr}")
            return None

        val = rr.registers[0]

        # TODO: Handle Float/32-bit conversion if needed
        # For now, just multiplier scaling
        scaled_val = val * (tag.multiplier or 1.0)
        return scaled_val
    except Exception as e:
        logger.error(f"Exception reading tag {tag.tag_name}: {e}")
        return None


def process_plc(db, config):
    client = get_client(config)
    if not client:
        return

    if not client.connect():
        logger.error(f"Failed to connect to PLC {config.name}")
        return

    try:
        # Get all tags for this PLC
        tags = db.execute(select(PLCTag).where(PLCTag.plc_id == config.id)).scalars().all()
        tag_values = {}

        # 1. Read all tags
        # logger.info(f"Found {len(tags)} tags for PLC {config.name}")
        for tag in tags:
            val = read_tag_value(client, tag, config.slave_id)
            if val is not None:
                tag_values[tag.tag_name] = val
            if val is not None:
                tag_values[tag.tag_name] = val
                # logger.debug(f"Tag {tag.tag_name}: {val}")

        # Update global cache
        LATEST_VALUES[config.id] = tag_values

        # 2. Check Triggers
        for tag in tags:
            if tag.is_stop_trigger and tag.trigger_value is not None:
                curr_val = tag_values.get(tag.tag_name)

                # Check for active match (Simple equality/truthiness for now)
                # If trigger val is 1, and curr val is 1 => STOP
                is_active = curr_val == tag.trigger_value

                # Find if stop is already open for this specific trigger
                # We identify it by existing open stop for this asset with this specific reason template??
                # Ideally we need a better correlation, maybe add 'trigger_tag_id' to StopQueue?
                # For now, we query open stops for asset and see if reason matches partially or we store context

                # We need to construct the reason string with variable sub
                reason_text = tag.stop_reason_template or f"PLC Trigger: {tag.tag_name}"

                # Substitute values
                # Substitute values
                for t_name, t_val in tag_values.items():
                    # Format value: remove decimals if whole number
                    display_val = str(t_val)
                    if isinstance(t_val, float) and t_val.is_integer():
                        display_val = str(int(t_val))

                    # Try $NAME$ first (explicit delimiter)
                    placeholder_explicit = f"${t_name}$"
                    if placeholder_explicit in reason_text:
                        reason_text = reason_text.replace(placeholder_explicit, display_val)

                    # Try $NAME (simple prefix)
                    placeholder_simple = f"${t_name}"
                    if placeholder_simple in reason_text:
                        reason_text = reason_text.replace(placeholder_simple, display_val)

                existing_stop = db.execute(
                    select(StopQueue).where(
                        StopQueue.asset_id == tag.asset_id,
                        StopQueue.is_open.is_(True),
                        # We use live_context to confirm this is THE stop from this trigger
                        # JSON lookup needs casting to compare with string tag.id
                        # Using cast(..., String) or just checking logic in python?
                        # Note: trigger_tag_id in json is string.
                        cast(StopQueue.live_context_json["trigger_tag_id"], String)
                        == f'"{tag.id}"',
                    )
                ).scalar_one_or_none()

                if is_active:
                    if not existing_stop:
                        logger.info(f"Opening Stop for {tag.tag_name} on {tag.asset_id}")
                        services.open_stop(
                            db,
                            asset_id=tag.asset_id,
                            reason=reason_text,
                            actor_user_id="plc_service",
                            actor_station_code=None,
                            request_id="plc_trigger",
                            extra_context={"trigger_tag_id": tag.id, "live_values": tag_values},
                        )
                    else:
                        # Update live values
                        existing_stop.live_context_json = {
                            "trigger_tag_id": tag.id,
                            "live_values": tag_values,
                            "last_updated": datetime.utcnow().isoformat(),
                        }
                        # Update reason text dynamically
                        existing_stop.reason = reason_text

                else:
                    if existing_stop:
                        logger.info(f"Closing Stop for {tag.tag_name} on {tag.asset_id}")
                        services.resolve_stop(
                            db,
                            stop_id=existing_stop.id,
                            resolution_text="Auto-cleared by PLC trigger reset",
                            actor_user_id="plc_service",
                            request_id="auto-close",
                        )

        db.commit()

    except Exception as e:
        logger.error(f"Error processing PLC {config.name}: {e}")
        traceback.print_exc()
    finally:
        client.close()


import threading


def run_loop():
    logger.info("PLC Service Started")
    while True:
        # DB Session per loop or long lived?
        # Better per loop or pass a session factory?
        # The original code used PlantSessionLocal() inside run_loop, so it's fine.
        # But wait, run_loop() in my view_file output used 'PlantSessionLocal' variable which was imported.
        # It didn't take an argument.

        # However, in main.py I passed 'PlantSessionLocal' as arg: plc_service.start_polling_thread(PlantSessionLocal)
        # So I should accept it or ignore it if I import it directly.
        # The file already imports 'PlantSessionLocal'.

        db = PlantSessionLocal()
        try:
            configs = (
                db.execute(select(PLCConfig).where(PLCConfig.is_active.is_(True))).scalars().all()
            )
            for config in configs:
                process_plc(db, config)
        except Exception as e:
            logger.error(f"Main Loop Error: {e}")
        finally:
            db.close()

        time.sleep(5)


def start_polling_thread(session_factory_ignored=None):
    """
    Starts the PLC polling in a background thread.
    session_factory_ignored is kept for compatibility if passed,
    but we use the imported PlantSessionLocal.
    """
    t = threading.Thread(target=run_loop, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    run_loop()
