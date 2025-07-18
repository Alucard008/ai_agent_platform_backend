# backend/main.py
import importlib
from fastapi import FastAPI, Depends, HTTPException, Path, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend import crud, schemas, models
from backend.database import init_db, get_db
from backend.services.agent_runner import AgentRunner
from backend.auth import router as auth_router, get_current_user

# bring in only the pydantic parts we need
from backend.schemas import AgentInput, AgentOutput
from backend.models  import Agent, Tool, User

# 1) Create all tables in Postgres
init_db()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# mount authentication (/signup, /login, etc.)
app.include_router(auth_router, tags=["auth"])


# --- Tools & Agents management (all protected by JWT) ---

@app.post("/tools", response_model=schemas.ToolOut)
def register_tool(
    payload: schemas.ToolCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    return crud.create_tool(db, payload)

@app.get("/tools", response_model=list[schemas.ToolOut])
def list_tools(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    return crud.list_tools(db)

@app.post("/agents")
def create_agent(
    payload: schemas.AgentCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    return crud.create_agent(db, payload)

@app.put("/agents/{agent_id}")
def update_agent(
    agent_id: int = Path(...),
    payload: schemas.AgentUpdate = Body(...),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    db_agent = crud.get_agent_by_id(db, agent_id)
    if not db_agent:
        raise HTTPException(404, "Agent not found")
    return crud.update_agent(db, db_agent, payload)

@app.get("/agents")
def list_my_agents(
    current_user: models.User = Depends(get_current_user),
    db: Session                = Depends(get_db),
):
    """
    Return all agents belonging to the authenticated user.
    """
    agents = crud.get_agents(db, current_user.id)
    return [
        {
            "id":         a.id,
            "agent_name": a.agent_name,
            "workflow":   a.workflow,
        }
        for a in agents
    ]


# --- Running your agent by name ---

@app.post("/run-task", response_model=AgentOutput)
def run_task(
    payload: AgentInput,
    db:      Session = Depends(get_db),
    me:      User    = Depends(get_current_user),
):
    # 1) fetch the agent for this user
    agent = (
        db.query(Agent)
          .filter_by(agent_name=payload.agent_name, user_id=me.id)
          .first()
    )
    if not agent:
        raise HTTPException(404, detail="Agent not found")

    # 2) pull every tool row & build name→class dict
    rows: list[Tool] = db.query(Tool).all()
    dynamic_registry: dict[str, type] = {}
    print("🔧 Loading tools from DB:")
    for row in rows:
        try:
            module = importlib.import_module(row.module_path)
            klass  = getattr(module, row.class_name)
            dynamic_registry[row.name] = klass
            print(f"  ✅ Loaded tool '{row.name}' → {row.module_path}.{row.class_name}")
        except Exception as e:
            print(f"  ❌ Failed to load tool '{row.name}': {e}")

    # 3) instantiate & inject
    runner = AgentRunner()
    runner.tool_registry = dynamic_registry

    # 4) run
    output = runner.run_agent_from_config(
        agent.workflow,
        query=payload.query,
        session_id=payload.session_id,
    )

    return AgentOutput(output=output, session_id=payload.session_id)


# --- Running your agent by ID (query‐params style) ---

@app.post("/run-agent", response_model=AgentOutput)
def run_agent_by_id(
    agent_id:    int,
    query:       str,
    session_id:  str,
    db:          Session = Depends(get_db),
    _:           User    = Depends(get_current_user),
):
    # 1) fetch by ID
    db_agent = crud.get_agent_by_id(db, agent_id)
    if not db_agent:
        raise HTTPException(404, "Agent not found")

    # 2) load tools again
    rows = db.query(Tool).all()
    registry: dict[str, type] = {}
    print(f"🔧 Loading tools for agent_id={agent_id}:")
    for row in rows:
        try:
            mod   = importlib.import_module(row.module_path)
            klass = getattr(mod, row.class_name)
            registry[row.name] = klass
            print(f"  ✅ Loaded tool '{row.name}' → {row.module_path}.{row.class_name}")
        except Exception as e:
            print(f"  ❌ Failed to load tool '{row.name}': {e}")

    # 3) inject & run
    runner = AgentRunner()
    runner.tool_registry = registry

    result = runner.run_agent_from_config(
        db_agent.workflow, query=query, session_id=session_id
    )
    return AgentOutput(output=result, session_id=session_id)
