from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from common_core.config import settings


class Base(DeclarativeBase):
    pass


def make_engine(db_url: str):
    return create_engine(db_url, pool_pre_ping=True, future=True)


def make_session(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


plant_engine = make_engine(settings.plant_db_url)
hq_engine = make_engine(settings.hq_db_url)

PlantSessionLocal = make_session(plant_engine)
HQSessionLocal = make_session(hq_engine)
