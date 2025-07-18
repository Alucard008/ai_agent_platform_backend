from sqlalchemy.orm import Session
from passlib.context import CryptContext
from uuid import uuid4

from typing import Optional, List

from fastapi.encoders import jsonable_encoder

from . import models, schemas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")



# -- Users --

def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email).first()

def get_user(db: Session, user_id: str) -> models.User | None:
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed = pwd_context.hash(user.password)
    db_user = models.User(email=user.email, name=user.name, hashed_password=hashed)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str) -> models.User | None:
    user = get_user_by_email(db, email)
    if not user or not pwd_context.verify(password, user.hashed_password):
        return None
    return user

# -- Tools --

def create_tool(db: Session, tool_in: schemas.ToolCreate) -> models.Tool:
    db_tool = models.Tool(**tool_in.model_dump())
    db.add(db_tool)
    db.commit()
    db.refresh(db_tool)
    return db_tool

def list_tools(db: Session) -> list[models.Tool]:
    return db.query(models.Tool).all()

# -- Agents --

def get_agents(db: Session, user_id: int) -> List[models.Agent]:
    return db.query(models.Agent).filter(models.Agent.user_id == user_id).all()


def get_agent_by_id(db: Session, agent_id: int) -> models.Agent | None:
    return db.query(models.Agent).get(agent_id)


def get_agent(db: Session, user_id: int, agent_name: str) -> Optional[models.Agent]:
    return (
        db.query(models.Agent)
          .filter(
              models.Agent.user_id == user_id,
              models.Agent.agent_name == agent_name
          )
          .first()
    )


def create_agent(db: Session, a: schemas.AgentCreate) -> dict:
    # look up user by email (or ID), etc…
    user = db.query(models.User).filter_by(email=a.user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No such user")

    # convert the Pydantic ToolStep instances into plain dicts
    workflow_data = jsonable_encoder(a.workflow)

    db_agent = models.Agent(
        agent_name=a.agent_name,
        user_id=user.id,
        workflow=workflow_data,
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return {"status": "created", "agent_id": db_agent.id}


def update_agent(
    db: Session,
    db_agent: models.Agent,
    payload: schemas.AgentUpdate
) -> dict:
    if payload.agent_name is not None:
        db_agent.agent_name = payload.agent_name

    # again, encode ToolStep → dict
    db_agent.workflow = jsonable_encoder(payload.workflow)

    db.commit()
    db.refresh(db_agent)
    return {"status": "updated", "agent_id": db_agent.id}