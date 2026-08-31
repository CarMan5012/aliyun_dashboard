import json
import time
import threading
from typing import Literal, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.resource import ResponseModel, DbStatusResponse
from app.crud import crud_resource
from app.tasks.aliyun_sync import sync_all_accounts_task, get_api_call_stats
from app.models.account import CloudAccount
from app.tasks.sync_lock import get_local_lock, local_account_locks
from app.core.config import settings

router = APIRouter()

def format_iso_time(dt) -> Optional[str]:
    """格式化时间为 ISO-8601 字符串并带 Z 时区标识"""
    if not dt:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

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


@router.get("/api-call-stats")
def api_get_api_call_stats(db: Session = Depends(get_db)):
    """
    返回阿里云 API 调用次数统计数据（近一周、今日、昨日、服务分类分布）
    """
    try:
        stats = get_api_call_stats(db=db)
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取 API 调用统计数据失败: {str(e)}"
        )


@router.get("/search")
@router.get("/search/global")
def api_search_resources(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    q: Optional[str] = Query(None, description="搜索关键词 (别名)"),
    account_id: Optional[int] = Query(None, description="云账号 ID"),
    accountId: Optional[int] = Query(None, description="云账号 ID (驼峰别名)"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    全量/分账号多资源类型统一搜索 (支持 /search 与 /search/global)
    """
    query_kw = keyword or q or ""
    if not query_kw.strip():
        return {"status": "success", "data": []}

    target_acc_id = account_id if account_id is not None else accountId
    try:
        resources = crud_resource.search_resources(db, keyword=query_kw.strip(), account_id=target_acc_id)
        if limit:
            resources = resources[:limit]

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


@router.get("/tasks/{task_id}")
def api_get_task_status(
    task_id: str,
    account_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    查询异步任务状态（基于本地内存锁与数据库持久化状态精准识别）
    """
    task_status = "PENDING"
    result_data = None
    ready = False

    if account_id:
        account = db.query(CloudAccount).filter(CloudAccount.id == account_id).first()
        loc_lock = get_local_lock(account_id)
        
        # 判断是否正在运行中
        if loc_lock.locked():
            task_status = "STARTED"
        elif account and account.last_sync_status in ("success", "partial_failure", "failure"):
            task_status = "SUCCESS" if account.last_sync_status == "success" else "FAILURE"
            ready = True
            try:
                details = json.loads(account.last_sync_details) if account.last_sync_details else {}
            except Exception:
                details = {}
            result_data = {
                "status": account.last_sync_status,
                "source": "database",
                "message": "同步已完成",
                "last_synced_at": format_iso_time(account.last_synced_at),
                "services": details
            }
        else:
            task_status = "PENDING"
    else:
        # 全局全量同步任务状态判断
        any_locked = any(l.locked() for l in local_account_locks.values())
        if any_locked:
            task_status = "STARTED"
        else:
            task_status = "SUCCESS"
            ready = True
            result_data = {"status": "success", "message": "全量资源同步已完成"}

    return {
        "status": "success",
        "task_id": task_id,
        "task_status": task_status,
        "ready": ready,
        "result": result_data,
        "traceback": None
    }


@router.post("/sync")
def api_manual_sync():
    """
    手动触发全量账号资源同步（原生异步守护线程执行）
    """
    task_id = f"local_sync_all_{int(time.time())}"
    threading.Thread(target=sync_all_accounts_task, daemon=True).start()
    return {
        "status": "success",
        "task_id": task_id,
        "message": "全量资源同步任务已在后台启动"
    }


def _fetch_resources_impl(
    resource_type: Optional[str],
    account_id: Optional[int],
    account_name: Optional[str],
    skip: int,
    limit: int,
    db: Session
):
    """内部通用资源查询逻辑"""
    try:
        resources = crud_resource.get_resources(
            db,
            resource_type=resource_type or "ECS",
            account_name=account_name,
            account_id=account_id
        )
        total = len(resources)
        paged_resources = resources[skip : skip + limit] if limit else resources[skip:]
        
        result = []
        for r in paged_resources:
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
            
        return {
            "status": "success",
            "total": total,
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"获取资源列表失败: {str(e)}"
        )


@router.get("/resources", response_model=ResponseModel)
def api_get_resources_query(
    type: Optional[str] = Query("ECS", description="资源类型 (ECS/EIP/Domain/SSL)"),
    resource_type: Optional[str] = Query(None, description="资源类型别名"),
    account: Optional[str] = Query(None, description="云账号别名"),
    account_id: Optional[int] = Query(None, description="云账号 ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    通过 Query 参数获取资源列表 (兼容 GET /api/v1/resources?type=ECS)
    """
    r_type = type or resource_type or "ECS"
    return _fetch_resources_impl(
        resource_type=r_type,
        account_id=account_id,
        account_name=account,
        skip=skip,
        limit=limit,
        db=db
    )


@router.get("/{resource_type}", response_model=ResponseModel)
def api_get_resources_path(
    resource_type: Literal['ECS', 'EIP', 'Domain', 'SSL'],
    account_id: Optional[int] = Query(None, description="按云账号 ID 筛选，不传则返回全部账号资源"),
    account: Optional[str] = Query(None, description="云账号别名"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    通过路径参数获取资源列表 (兼容 GET /api/v1/ECS 等)
    """
    return _fetch_resources_impl(
        resource_type=resource_type,
        account_id=account_id,
        account_name=account,
        skip=skip,
        limit=limit,
        db=db
    )
