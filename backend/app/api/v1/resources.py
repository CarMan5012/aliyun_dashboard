import json
from typing import Literal, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.resource import ResponseModel, DbStatusResponse
from app.crud import crud_resource
from app.tasks.aliyun_sync import sync_all_accounts_task

router = APIRouter()

@router.get("/db-status", response_model=DbStatusResponse)
def api_get_db_status(db: Session = Depends(get_db)):
    """
    检查数据库中是否有资源数据
    """
    try:
        count = crud_resource.get_resources_count(db)
        return {"status": "success", "is_empty": count == 0}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"数据库连接/查询异常，服务暂不可用: {str(e)}"
        )

def format_iso_time(dt):
    if not dt:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

@router.get("/resources", response_model=ResponseModel)
def api_get_resources(
    type: Literal["ECS", "EIP", "Domain", "SSL"] = Query(...),
    account: Optional[str] = Query(None), 
    account_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db)
):
    """
    返回指定账号下的资源数据（如果账号为空或为“全部账号”，则返回全部）
    """
    try:
        resources = crud_resource.get_resources(db, resource_type=type, account_name=account, account_id=account_id)
        
        result = []
        for r in resources:
            try:
                details = json.loads(r.details)
            except Exception:
                details = {}
            
            result.append({
                "id": r.id,
                "account_id": r.account_id,
                "account_name": r.account_name,
                "resource_type": r.resource_type,
                "search_key": r.search_key,
                "update_time": format_iso_time(r.update_time),
                "details": details
            })
            
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"获取 [{type}] 资源列表失败: {str(e)}"
        )

@router.get("/search", response_model=ResponseModel)
def api_search_resources(
    keyword: str = Query(..., min_length=1, max_length=255),
    account_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    """
    全局搜索接口，对 search_key & details 进行模糊搜索
    """
    try:
        resources = crud_resource.search_resources(db, keyword=keyword, account_id=account_id)
        
        result = []
        for r in resources:
            try:
                details = json.loads(r.details)
            except Exception:
                details = {}
                
            result.append({
                "id": r.id,
                "account_id": r.account_id,
                "account_name": r.account_name,
                "resource_type": r.resource_type,
                "search_key": r.search_key,
                "update_time": format_iso_time(r.update_time),
                "details": details
            })
            
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"全局检索失败: {str(e)}"
        )

@router.post("/sync")
def api_manual_sync():
    """
    手动触发全量账号资源同步（通过 Celery 异步任务执行）
    """
    try:
        # 触发 Celery 异步任务
        task = sync_all_accounts_task.delay()
        if not task or not task.id:
            raise RuntimeError("未能从 Celery 任务队列中获取有效 Task ID")
            
        return {
            "status": "success", 
            "task_id": task.id,
            "message": f"同步任务已提交后台，任务ID: {task.id}"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"同步队列服务不可用，任务投递失败: {str(e)}"
        )

from celery.result import AsyncResult
from app.tasks.celery_app import celery_app
from app.models.account import CloudAccount

@router.get("/tasks/{task_id}")
def api_get_task_status(
    task_id: str,
    account_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    查询 Celery 异步任务状态（带 Redis 记录超时后自动回退至 MySQL 数据库校验）
    """
    res = AsyncResult(task_id, app=celery_app)
    task_status = res.status
    result_data = None
    traceback_data = None
    ready = res.ready()

    if ready:
        if task_status == 'SUCCESS':
            result_data = res.result
        elif task_status == 'FAILURE':
            result_data = str(res.result)
            traceback_data = res.traceback
    elif task_status == 'PENDING':
        # Celery 对不存在或超时 24h 被 Redis 自动清理的 task_id 默认返回 PENDING
        # 兜底查询 MySQL 数据库持久化同步状态
        account = None
        if account_id:
            account = db.query(CloudAccount).filter(CloudAccount.id == account_id).first()
        else:
            account = db.query(CloudAccount).filter(CloudAccount.last_synced_at.isnot(None)).order_by(CloudAccount.last_synced_at.desc()).first()

        if account and account.last_synced_at:
            task_status = "SUCCESS"
            ready = True
            try:
                details = json.loads(account.last_sync_details) if account.last_sync_details else {}
            except Exception:
                details = {}
            result_data = {
                "status": account.last_sync_status or "success",
                "source": "mysql_database",
                "message": "任务已完成，已从 MySQL 数据库读取持久化同步记录",
                "last_synced_at": format_iso_time(account.last_synced_at),
                "services": details
            }

    return {
        "status": "success",
        "task_id": task_id,
        "task_status": task_status,
        "ready": ready,
        "result": result_data,
        "traceback": traceback_data
    }
