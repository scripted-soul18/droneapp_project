from typing import Optional
from pydantic import BaseModel, Field

class DroneConfigUpdate(BaseModel):
    style: Optional[str] = Field(None, description="neon|wire|crystal")
    color: Optional[str] = Field(None, description="#rrggbb")
    scale: Optional[float] = Field(None, description="scale factor")
    animate: Optional[bool] = None
    simulator: Optional[bool] = None

class DroneConfigOut(BaseModel):
    key: str
    title: str
    desc: Optional[str]
    style: str
    color: str
    scale: float
    animate: bool
    simulator: bool