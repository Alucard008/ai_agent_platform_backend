# backend/app/services/agent_runner.py

import importlib
from sqlalchemy.orm import Session
from ..database     import SessionLocal
from ..models       import Tool as ToolModel
from ..agents.generic import GenericAgent

class AgentRunner:
    def __init__(self):
        # we won't build a permanent registry here
        self.tool_registry = {}

    def _reload_tool_registry(self) -> None:
        """Fetch all tools from the DB and import them fresh."""
        db: Session = SessionLocal()
        tools = db.query(ToolModel).all()
        db.close()

        registry = {}
        for t in tools:
            try:
                module = importlib.import_module(t.module_path)
                cls    = getattr(module, t.class_name)
                registry[t.name] = cls
                print(f"[✅ TOOL LOADED] {t.name}: {t.module_path}.{t.class_name}")
            except Exception as e:
                print(f"[❌ TOOL LOAD FAILED] {t.name}: {e!r}")

        if not registry:
            # Warn early if DB was empty or module_paths were wrong
            raise RuntimeError("[❌ ERROR] No tools loaded from database!")
        self.tool_registry = registry

    def run_agent_from_config(self, config: dict, query: str, session_id: str) -> str:
        # reload *every* invocation so newly-registered tools show up immediately
        self._reload_tool_registry()

        agent = GenericAgent.from_config(config, self.tool_registry)
        return agent.run(query, session_id)
