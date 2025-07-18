
TRACE_LOG = []

def trace_event(session_id: str, step: str, detail: str):
    print(f"[{session_id}] {step}: {detail}")
    TRACE_LOG.append({"session_id": session_id, "step": step, "detail": detail})
