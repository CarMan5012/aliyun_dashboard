from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from app.models.resource import Resource
from app.models.account import CloudAccount

def get_resources(
    db: Session, 
    resource_type: str, 
    account_name: Optional[str] = None,
    account_id: Optional[int] = None
) -> List[Resource]:
    query = db.query(Resource).options(joinedload(Resource.account)).filter(Resource.resource_type == resource_type)
    
    if account_id is not None:
        query = query.filter(Resource.account_id == account_id)
    elif account_name and account_name != "全部账号":
        query = query.join(Resource.account).filter(CloudAccount.account_alias == account_name)
        
    return query.all()

def search_resources(db: Session, keyword: str, account_id: Optional[int] = None) -> List[Resource]:
    search_pattern = f"%{keyword}%"
    query = db.query(Resource).options(joinedload(Resource.account)).filter(
        or_(
            Resource.search_key.like(search_pattern),
            Resource.details.like(search_pattern)
        )
    )
    if account_id is not None:
        query = query.filter(Resource.account_id == account_id)
    return query.all()

def get_resources_count(db: Session) -> int:
    return db.query(Resource).count()
