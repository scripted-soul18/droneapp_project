from typing import Optional
from sqlmodel import SQLModel, Field

class DroneConfig(SQLModel, table=True):
    key: str = Field(primary_key=True)
    title: str
    desc: Optional[str] = None
    style: str = "neon"        # neon | wire | crystal
    color: str = "#06e0ff"    # hex color string
    scale: float = 1.0
    animate: bool = False
    simulator: bool = False