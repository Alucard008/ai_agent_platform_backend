# registry/tool_registry.py
from database import SessionLocal
from utils.tool_loader import load_tool
from models import Tool

def build_tool_registry():
    db = SessionLocal()
    tool_rows = db.query(Tool).all()
    registry = {}
    for row in tool_rows:
        try:
            registry[row.name] = load_tool(row.class_path)
        except Exception as e:
            print(f"[ERROR] Failed to load tool: {row.name} – {e}")
    db.close()
    return registry

TOOL_REGISTRY = build_tool_registry()
