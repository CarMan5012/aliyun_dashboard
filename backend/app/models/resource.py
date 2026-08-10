import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Resource(Base):
    """
    统一资源表，用于存储各账号下的云资源信息
    """
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("cloud_accounts.id", ondelete="CASCADE"), nullable=False, index=True, comment="关联账号ID")
    account_name_raw = Column("account_name", String(100), index=True, nullable=True, comment="账号别名(旧历史字段)")
    resource_type = Column(String(50), index=True, nullable=False, comment="资源类型(如 ECS, EIP, Domain, SSL)")
    search_key = Column(String(255), index=True, comment="用于全局搜索的核心词，如 IP 或域名")
    details = Column(Text, comment="JSON格式的详细信息")
    update_time = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, comment="更新时间")

    account = relationship("CloudAccount", back_populates="resources")

    @property
    def account_name(self) -> str:
        if self.account and self.account.account_alias:
            return self.account.account_alias
        return self.account_name_raw or ""

    @account_name.setter
    def account_name(self, value: str):
        self.account_name_raw = value

