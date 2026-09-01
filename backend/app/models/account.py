from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.core.security import encrypt_secret, decrypt_secret

class CloudAccount(Base):
    __tablename__ = "cloud_accounts"

    id = Column(Integer, primary_key=True, index=True)
    account_alias = Column(String(100), unique=True, nullable=False, comment="账号别名")
    access_key_id = Column(String(100), nullable=False, comment="AK 可以明文存储")
    encrypted_secret_key = Column(Text, nullable=False, comment="SK 密文存储")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    sync_interval = Column(Integer, default=168, nullable=False, comment="同步间隔(小时)，168表示每周一，0表示手动同步")
    last_synced_at = Column(DateTime(timezone=True), nullable=True, comment="上次成功同步时间")
    last_attempted_at = Column(DateTime(timezone=True), nullable=True, comment="上次尝试同步时间")
    last_sync_status = Column(String(20), default="never", nullable=False, comment="最近同步结果")
    last_sync_error = Column(Text, nullable=True, comment="最近同步失败摘要")
    last_sync_details = Column(Text, nullable=True, comment="最近各子服务同步结果(JSON)")
    active_regions = Column(Text, nullable=True, comment="包含资产的活跃地域列表(JSON)")

    resources = relationship("Resource", back_populates="account", cascade="all, delete-orphan")

    def set_secret(self, raw_sk: str):
        """写入时调用此方法加密"""
        self.encrypted_secret_key = encrypt_secret(raw_sk)

    def get_secret(self) -> str:
        """Celery Worker 执行同步任务时调用此方法获取明文"""
        return decrypt_secret(self.encrypted_secret_key)
