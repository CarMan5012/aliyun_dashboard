from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.session import get_db
from app.schemas.account import CloudAccountCreate, CloudAccountUpdate, CloudAccountResponse
from app.crud import crud_account
from app.tasks.aliyun_sync import sync_single_account_task

router = APIRouter()

# 定义包装响应模型以适配前端
class AccountListResponse(BaseModel):
    status: str
    data: List[CloudAccountResponse]

class AccountSingleResponse(BaseModel):
    status: str
    data: CloudAccountResponse

@router.get("", response_model=AccountListResponse)
def list_accounts(
    skip: int = Query(0, ge=0),
    limit: Optional[int] = Query(None, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """获取所有已配置的阿里云账号列表 (不包含 AccessKeySecret)"""
    accounts = crud_account.get_accounts(db, skip=skip, limit=limit)
    return {"status": "success", "data": accounts}

import logging
from app.tasks.sync_lock import AccountSyncLock, AccountCooldown

logger = logging.getLogger(__name__)

from app.schemas.account import CloudAccountCreate, CloudAccountUpdate, CloudAccountResponse, AccountSaveResponse

@router.post("", status_code=status.HTTP_201_CREATED, response_model=AccountSaveResponse)
def create_account(account_in: CloudAccountCreate, db: Session = Depends(get_db)):
    """添加新的阿里云账号，并自动触发该账号的资源同步任务"""
    existing = crud_account.get_account_by_alias(db, alias=account_in.account_alias)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"账号别名 [{account_in.account_alias}] 已存在，请使用其他别名"
        )
    try:
        account = crud_account.create_account(db, obj_in=account_in)
    except IntegrityError as ie:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"账号别名 [{account_in.account_alias}] 数据库唯一约束冲突，请使用其他别名"
        )
    
    # 尝试触发同步任务，若 Celery/Redis 队列挂掉，不影响账号成功落库
    sync_queued = False
    task_id = None
    warning_msg = None
    try:
        task = sync_single_account_task.delay(account.id)
        if task and getattr(task, "id", None):
            sync_queued = True
            task_id = str(task.id)
    except Exception as e:
        sync_queued = False
        warning_msg = f"账号创建成功，但自动数据同步任务投递失败 ({str(e)})，请稍后手动同步。"
        logger.warning(warning_msg)

    return {
        "status": "success",
        "data": account,
        "sync_queued": sync_queued,
        "task_id": task_id,
        "warning": warning_msg
    }

@router.get("/{account_id}", response_model=AccountSingleResponse)
def read_account(account_id: int, db: Session = Depends(get_db)):
    """获取指定账号的配置详情 (不包含 AccessKeySecret)"""
    account = crud_account.get_account(db, account_id=account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="云账号未找到"
        )
    return {"status": "success", "data": account}

@router.put("/{account_id}", response_model=AccountSaveResponse)
def update_account(account_id: int, account_in: CloudAccountUpdate, db: Session = Depends(get_db)):
    """更新指定阿里云账号信息"""
    account = crud_account.get_account(db, account_id=account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="云账号未找到"
        )
    
    if account_in.account_alias and account_in.account_alias != account.account_alias:
        existing = crud_account.get_account_by_alias(db, alias=account_in.account_alias)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"账号别名 [{account_in.account_alias}] 已存在，请使用其他别名"
            )
            
    credential_changed = False
    if account_in.access_key_id and account_in.access_key_id != account.access_key_id:
        credential_changed = True
    if account_in.access_key_secret and account_in.access_key_secret.strip() != "":
        credential_changed = True

    try:
        updated = crud_account.update_account(db, db_obj=account, obj_in=account_in)
    except IntegrityError as ie:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"账号别名 [{account_in.account_alias}] 数据库唯一约束冲突，请使用其他别名"
        )
    
    # 仅当 AccessKey 凭证发生变化时才重新触发数据同步
    sync_queued = False
    task_id = None
    warning_msg = None
    if credential_changed:
        AccountCooldown.clear_cooldown(updated.id)
        updated.last_sync_status = "never"
        updated.last_sync_error = None
        updated.last_sync_details = None
        db.commit()
        try:
            task = sync_single_account_task.delay(updated.id)
            if task and task.id:
                sync_queued = True
                task_id = task.id
        except Exception as e:
            sync_queued = False
            warning_msg = f"账号凭证更新成功，但自动数据同步任务投递失败 ({str(e)})，请稍后手动同步。"
            logger.warning(warning_msg)

    return {
        "status": "success",
        "data": updated,
        "sync_queued": sync_queued,
        "task_id": task_id,
        "warning": warning_msg
    }

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    """删除指定的阿里云账号，不再管理其云资产"""
    account = crud_account.get_account(db, account_id=account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="云账号未找到"
        )
    crud_account.delete_account(db, account_id=account_id)
    return None

@router.post("/{account_id}/sync")
def sync_account(account_id: int, full_scan: bool = Query(True), db: Session = Depends(get_db)):
    """手动触发指定阿里云账号的全量深度资产同步"""
    account = crud_account.get_account(db, account_id=account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="云账号未找到"
        )
        
    # 手动点击“立即同步”时重置退避冷却，确保立即响应用户
    AccountCooldown.clear_cooldown(account_id)

    # 检查是否正在同步中
    running_task = AccountSyncLock.get_running_task_id(account_id)
    if running_task:
        return {
            "status": "already_running",
            "task_id": running_task,
            "message": f"账号 [{account.account_alias}] 正在同步中，请勿重复触发。"
        }

    try:
        task = sync_single_account_task.delay(account.id, full_scan=full_scan)
        if not task or not task.id:
            raise RuntimeError("未能从 Celery 任务队列中获取有效 Task ID")

        return {
            "status": "success",
            "task_id": task.id,
            "message": f"账号 [{account.account_alias}] 的同步任务已提交后台"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"同步服务不可用，任务投递失败: {str(e)}"
        )
