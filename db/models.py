from sqlalchemy import Column, Integer, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Ping(Base):
    __tablename__ = "ping"
    id = Column(Integer, primary_key=True)
    ts = Column(TIMESTAMP(timezone=True), server_default=func.now())
