from sqlmodel import SQLModel, create_engine, Session, select
import models
import os

DB_FILE = os.environ.get("DB_FILE", "data.db")
DATABASE_URL = f"sqlite:///{DB_FILE}"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

def init_db():
    SQLModel.metadata.create_all(engine)
    # seed defaults if not present
    default = {
        "quadcopter": ("Quadcopter", "Versatile multi-rotor for photography and agility."),
        "fixedwing": ("Fixed-Wing", "Efficient for long-range flights and mapping."),
        "hexacopter": ("Hexacopter", "Six rotors for heavy lifting."),
        "octocopter": ("Octocopter", "Maximum payload and redundancy."),
        "delivery": ("Delivery", "Cargo bays for logistics."),
        "agricultural": ("Agricultural", "Sprayers & crop monitoring."),
        "swarm": ("Swarm", "Coordinated group operations."),
        "nano": ("Nano/Micro", "Compact indoor operations."),
        "military": ("Military", "Armored with advanced sensors."),
        "hybrid": ("Hybrid", "VTOL + fixed-wing capabilities."),
        "spherical": ("Spherical", "Omnidirectional orb."),
        "singlerotor": ("Single-Rotor", "Helicopter-style precise control."),
    }
    with Session(engine) as session:
        for k, (title, desc) in default.items():
            ex = session.get(models.DroneConfig, k)
            if not ex:
                cfg = models.DroneConfig(key=k, title=title, desc=desc)
                session.add(cfg)
        session.commit()