import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from app.db.base import Base

class ApiCallRecord(Base):
    """
    阿里云 API 调用统计持久化表（跨 SQLite 与 MySQL 通用）
    按 (日期, 账号ID, 服务类型) 聚合记录实际发生的 OpenAPI 请求次数
    """
    __tablename__ = "api_call_records"

    id = Column(Integer, primary_key=True, index=True)
    call_date = Column(String(10), index=True, nullable=False)  # 'YYYY-MM-DD'
    account_id = Column(Integer, ForeignKey("cloud_accounts.id", ondelete="CASCADE"), nullable=True, index=True)
    service_type = Column(String(20), index=True, nullable=False)  # 'ECS', 'EIP', 'Domain', 'SSL'
    call_count = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("call_date", "account_id", "service_type", name="uq_api_call_daily"),
    )
