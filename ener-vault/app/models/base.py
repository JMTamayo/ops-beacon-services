from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

ENERGY_METERS_SCHEMA = "energy_meters"


class Base(DeclarativeBase):
    metadata = MetaData(schema=ENERGY_METERS_SCHEMA)
