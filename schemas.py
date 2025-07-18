# backend/schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any , Union

# --- auth ---
class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str

    model_config = { "from_attributes": True }

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None


# --- tools & agents remain unchanged except User references removed ---


class ToolCreate(BaseModel):
    name: str
    description: str
    module_path: str
    class_name: str

class ToolOut(BaseModel):
    id: int
    name: str
    description: str
    module_path: str
    class_name: str

    model_config = { "from_attributes": True }


class ToolStep(BaseModel):
    name: str
    input_from: str = "query"
    config: Dict[str, Any] = Field(default_factory=dict)

class AgentCreate(BaseModel):
    agent_name: str
    user_email: str          # <-- renamed from user_id
    workflow: Dict[str, List[ToolStep]]

class AgentUpdate(BaseModel):
    agent_name: str | None = None
    workflow: Dict[str, List[ToolStep]]


class WebSearchResult(BaseModel):
    type: str
    title: str
    snippet: Optional[str]
    link: str
    extra: Dict[str, Any] = Field(default_factory=dict)

class WebSearchOutput(BaseModel):
    query: str
    results: List[WebSearchResult]
    
# ----- running an agent -----
class AgentInput(BaseModel):
    query: str
    session_id: str
    agent_name: str
    user_id: int

class AgentOutput(BaseModel):
    # <-- allow either a plain string or a full WebSearchOutput
    output: Union[str, WebSearchOutput]
    session_id: str

    model_config = {
        "arbitrary_types_allowed": True,
        "from_attributes": True,
    }


