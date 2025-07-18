# save_log.py
from models.db import WebSearchLog
from database import SessionLocal  # your SQLAlchemy session
from tools.web_search_tool import WebSearchTool

def log_search_result(query, session_id, agent_name, user_id):
    tool = WebSearchTool()
    result_obj = tool.run(query)

    session = SessionLocal()
    log_entry = WebSearchLog(
        query=query,
        results=result_obj.dict(),
        session_id=session_id,
        agent_name=agent_name,
        user_id=user_id
    )
    session.add(log_entry)
    session.commit()
    session.close()
