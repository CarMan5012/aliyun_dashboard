from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.core.security import decrypt_secret, encrypt_secret
from app.db.base import Base


class DomainAlertSetting(Base):
    __tablename__ = "domain_alert_settings"

    id = Column(Integer, primary_key=True)
    enabled = Column(Boolean, default=False, nullable=False)
    reminder_days = Column(Integer, default=14, nullable=False)
    warning_days = Column(Integer, default=7, nullable=False)
    critical_days = Column(Integer, default=3, nullable=False)
    keyword = Column(String(100), default="域名告警", nullable=False)
    webhook_encrypted = Column(Text, nullable=True)
    secret_encrypted = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def set_webhook(self, value: str) -> None:
        self.webhook_encrypted = encrypt_secret(value)

    def get_webhook(self) -> str | None:
        return decrypt_secret(self.webhook_encrypted) if self.webhook_encrypted else None

    def set_secret(self, value: str) -> None:
        self.secret_encrypted = encrypt_secret(value)

    def get_secret(self) -> str | None:
        return decrypt_secret(self.secret_encrypted) if self.secret_encrypted else None


class DomainAlertEvent(Base):
    __tablename__ = "domain_alert_events"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "domain_name",
            "expiration_date",
            "level",
            name="uq_domain_alert_event",
        ),
    )

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, nullable=False, index=True)
    account_alias = Column(String(100), nullable=False)
    domain_name = Column(String(255), nullable=False)
    expiration_date = Column(String(10), nullable=False)
    level = Column(String(20), nullable=False)
    first_sent_at = Column(DateTime(timezone=True), nullable=False)
    needs_workday_followup = Column(Boolean, default=False, nullable=False)
    workday_followup_sent_at = Column(DateTime(timezone=True), nullable=True)
