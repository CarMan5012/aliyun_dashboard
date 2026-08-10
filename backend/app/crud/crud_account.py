from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.account import CloudAccount
from app.models.resource import Resource
from app.schemas.account import CloudAccountCreate, CloudAccountUpdate

def clean_credential(val: str) -> str:
    if not val:
        return val
    val = val.strip()
    # 移除诸如 'ak:', 'sk:' 等 YAML 配置或 CLI 拷贝前缀
    for prefix in ['ak:', 'sk:', 'ak：', 'sk：']:
        if val.lower().startswith(prefix):
            val = val[len(prefix):].strip()
    # 移除首尾引号
    if val.startswith('"') and val.endswith('"'):
        val = val[1:-1].strip()
    elif val.startswith("'") and val.endswith("'"):
        val = val[1:-1].strip()
    return val

def get_account(db: Session, account_id: int) -> Optional[CloudAccount]:
    return db.query(CloudAccount).filter(CloudAccount.id == account_id).first()

def get_account_by_alias(db: Session, alias: str) -> Optional[CloudAccount]:
    return db.query(CloudAccount).filter(CloudAccount.account_alias == alias).first()

def get_accounts(db: Session, skip: int = 0, limit: Optional[int] = None) -> List[CloudAccount]:
    query = db.query(CloudAccount).offset(skip)
    return (query.limit(limit) if limit is not None else query).all()

def create_account(db: Session, obj_in: CloudAccountCreate) -> CloudAccount:
    clean_ak = clean_credential(obj_in.access_key_id)
    clean_sk = clean_credential(obj_in.access_key_secret)
    clean_alias = obj_in.account_alias.strip() if obj_in.account_alias else ""
    
    db_obj = CloudAccount(
        account_alias=clean_alias,
        access_key_id=clean_ak,
        sync_interval=obj_in.sync_interval if obj_in.sync_interval is not None else 24
    )
    db_obj.set_secret(clean_sk)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update_account(db: Session, db_obj: CloudAccount, obj_in: CloudAccountUpdate) -> CloudAccount:
    new_alias = obj_in.account_alias.strip() if obj_in.account_alias is not None else None
    
    if new_alias is not None:
        db_obj.account_alias = new_alias
        # 别名仅用于显示，已改由 account_id 外键关联，无需修改资源表
        
    if obj_in.access_key_id is not None:
        db_obj.access_key_id = clean_credential(obj_in.access_key_id)
    if obj_in.access_key_secret is not None:
        db_obj.set_secret(clean_credential(obj_in.access_key_secret))
    if obj_in.sync_interval is not None:
        db_obj.sync_interval = obj_in.sync_interval
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_account(db: Session, account_id: int) -> Optional[CloudAccount]:
    db_obj = db.query(CloudAccount).filter(CloudAccount.id == account_id).first()
    if db_obj:
        # 由数据库级联外键 ON DELETE CASCADE 自动物理删除关联资源
        db.delete(db_obj)
        db.commit()
    return db_obj
