# backend/models.py
from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import relationship, declarative_base
from .database import Base 

class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String, unique=True, nullable=False, index=True)
    name            = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)

    agents = relationship("Agent", back_populates="owner")


class Agent(Base):
    __tablename__ = "agents"

    id         = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String, index=True)
    workflow   = Column(JSON, nullable=False)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="agents")


class Tool(Base):
    __tablename__ = "tools"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, unique=True, nullable=False)
    description = Column(String)
    module_path = Column(String, nullable=False)
    class_name  = Column(String, nullable=False)
