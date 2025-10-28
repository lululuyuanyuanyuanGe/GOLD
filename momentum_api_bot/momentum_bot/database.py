from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class Trade(Base):
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False)
    action = Column(String, nullable=False) # BUY or SELL
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    entry_timestamp = Column(DateTime, default=datetime.datetime.now)
    exit_price = Column(Float, nullable=True)
    exit_timestamp = Column(DateTime, nullable=True)
    status = Column(String, default='OPEN') # OPEN, CLOSED
    pnl = Column(Float, nullable=True)

    def __repr__(self):
        return f"<Trade(id={self.id}, symbol='{self.symbol}', status='{self.status}')>"

class PositionRecord(Base):
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False, unique=True)
    quantity = Column(Integer, nullable=False)
    avg_entry_price = Column(Float, nullable=False)
    entry_timestamp = Column(DateTime, default=datetime.datetime.now)
    status = Column(String, default='OPEN') # OPEN, CLOSED

    def __repr__(self):
        return f"<PositionRecord(id={self.id}, symbol='{self.symbol}', quantity={self.quantity}, status='{self.status}')>"

def init_db(database_url: str):
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session
