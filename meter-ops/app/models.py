from pydantic import BaseModel


class MeterReadingData(BaseModel):
    voltage: float
    current: float
    active_power: float
    active_energy: float
    frequency: float
    power_factor: float


class MeterReading(BaseModel):
    local_timestamptz: str
    data: MeterReadingData
