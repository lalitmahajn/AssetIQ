import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.plant_backend.models import PLCConfig, PLCTag
from common_core.db import PlantSessionLocal

router = APIRouter(prefix="/plc", tags=["plc"])


# Pydantic Models
class PLCConfigCreate(BaseModel):
    site_code: str
    name: str
    protocol: str
    ip_address: str | None = None
    port: int | None = None
    serial_port: str | None = None
    baud_rate: int | None = 9600
    slave_id: int = 1
    scan_interval_sec: int = 5
    is_active: bool = True


class PLCTagCreate(BaseModel):
    plc_id: str
    tag_name: str
    address: int
    data_type: str
    multiplier: float = 1.0
    is_stop_trigger: bool = False
    trigger_value: float | None = None
    stop_reason_template: str | None = None
    asset_id: str | None = None


def get_db():
    db = PlantSessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/configs")
def list_configs(db: Session = Depends(get_db)):
    return db.execute(select(PLCConfig)).scalars().all()


@router.post("/configs")
def create_config(config: PLCConfigCreate, db: Session = Depends(get_db)):
    db_obj = PLCConfig(id=uuid.uuid4().hex, **config.model_dump(), created_at_utc=datetime.utcnow())
    db.add(db_obj)
    db.commit()
    return db_obj


@router.put("/configs/{config_id}")
def update_config(config_id: str, config: PLCConfigCreate, db: Session = Depends(get_db)):
    db_obj = db.get(PLCConfig, config_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Config not found")

    for k, v in config.model_dump().items():
        setattr(db_obj, k, v)

    db.commit()
    return db_obj


@router.delete("/configs/{config_id}")
def delete_config(config_id: str, db: Session = Depends(get_db)):
    db_obj = db.get(PLCConfig, config_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Config not found")
    db.delete(db_obj)
    db.commit()
    return {"ok": True}


@router.get("/tags/{plc_id}")
def list_tags(plc_id: str, db: Session = Depends(get_db)):
    return db.execute(select(PLCTag).where(PLCTag.plc_id == plc_id)).scalars().all()


@router.post("/tags")
def create_tag(tag: PLCTagCreate, db: Session = Depends(get_db)):
    db_obj = PLCTag(id=uuid.uuid4().hex, **tag.model_dump())
    db.add(db_obj)
    db.commit()
    return db_obj


@router.delete("/tags/{tag_id}")
def delete_tag(tag_id: str, db: Session = Depends(get_db)):
    db_obj = db.get(PLCTag, tag_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Tag not found")
    db.delete(db_obj)
    db.commit()
    return {"ok": True}


@router.put("/tags/{tag_id}")
def update_tag(tag_id: str, tag: PLCTagCreate, db: Session = Depends(get_db)):
    db_obj = db.get(PLCTag, tag_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Tag not found")

    data = tag.model_dump()
    for k, v in data.items():
        setattr(db_obj, k, v)

    db.commit()
    return db_obj


@router.post("/test-connection")
def test_connection(config: PLCConfigCreate):
    from pymodbus.client import ModbusSerialClient, ModbusTcpClient

    try:
        if config.protocol == "MODBUS_TCP":
            client = ModbusTcpClient(config.ip_address, port=config.port or 502)
        elif config.protocol == "MODBUS_RTU":
            client = ModbusSerialClient(
                port=config.serial_port, baudrate=config.baud_rate, framer="rtu"
            )
        else:
            return {"ok": False, "error": "Unknown protocol"}

        if client.connect():
            client.close()
            return {"ok": True}
        else:
            return {"ok": False, "error": "Could not connect"}
            return {"ok": False, "error": "Could not connect"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/values/{plc_id}")
def get_values(plc_id: str):
    from apps.plant_backend.plc_service import LATEST_VALUES

    return LATEST_VALUES.get(plc_id, {})
