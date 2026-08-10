from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class ResourceOut(BaseModel):
    id: int
    account_id: Optional[int] = None
    account_name: str
    resource_type: str
    search_key: Optional[str] = None
    update_time: Optional[str] = None
    details: Dict[str, Any]

    class Config:
        from_attributes = True


class ResponseModel(BaseModel):
    status: str
    data: List[ResourceOut]

class DbStatusResponse(BaseModel):
    status: str
    is_empty: bool
    message: Optional[str] = None
