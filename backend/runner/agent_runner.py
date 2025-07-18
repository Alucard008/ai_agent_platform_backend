# backend/services/agent_runner.py

import importlib
from importlib.machinery import SourceFileLoader
from pathlib              import Path
from sqlalchemy.orm       import Session

from ..database           import SessionLocal
from ..models             import Tool as ToolModel
from .generic_agent       import GenericAgent

class AgentRunner:
    def __init__(self):
        self.tool_registry: dict[str, type] = {}

    def _reload_tool_registry(self) -> None:
        """Reload all tools from the DB, with a file-based fallback."""
        db: Session = SessionLocal()
        tools = db.query(ToolModel).all()
        db.close()

        registry: dict[str, type] = {}
        # backend_dir → PROJECT_ROOT/backend
        backend_dir = Path(__file__).parents[1]

        for t in tools:
            loaded = False
            # 1) Try normal import
            try:
                module = importlib.import_module(t.module_path)
                cls    = getattr(module, t.class_name)
                registry[t.name] = cls
                print(f"[✅ TOOL LOADED] {t.name} via import '{t.module_path}.{t.class_name}'")
                loaded = True
            except ModuleNotFoundError:
                # module_path not on PYTHONPATH—fall through
                pass
            except Exception as e:
                # e.g. class not found
                print(f"[❌ ERROR] loading '{t.name}' via import: {e!r}")
                loaded = True  # don’t retry fallback if import path exists but class missing

            if loaded:
                continue

            # 2) File-based fallback
            #    if module_path = "backend.tools.search_tool", we want backend_dir/"tools/search_tool.py"
            parts    = t.module_path.split(".")
            filename = parts[-1] + ".py"
            tool_file = backend_dir / "tools" / filename

            if tool_file.exists():
                try:
                    loader = SourceFileLoader(t.class_name, str(tool_file))
                    module = loader.load_module()
                    cls    = getattr(module, t.class_name)
                    registry[t.name] = cls
                    print(f"[✅ TOOL LOADED] {t.name} via file '{tool_file}'")
                    loaded = True
                except Exception as e:
                    print(f"[❌ ERROR] loading '{t.name}' from file: {e!r}")

            else:
                print(f"[❌ NOT FOUND] {t.name}: expected file at {tool_file}")

        if not registry:
            raise RuntimeError(
                "[❌ ERROR] No tools loaded from database – check your `tools` table and file layout!"
            )

        self.tool_registry = registry

    def run_agent_from_config(self, workflow_config: dict, query: str, session_id: str) -> str:
        # always pick up new tools
        self._reload_tool_registry()

        agent = GenericAgent.from_config(workflow_config, self.tool_registry)
        return agent.run(query, session_id)
