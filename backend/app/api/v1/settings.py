import hmac
from typing import Optional
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.db.session import get_db
from app.models.domain_alert import DomainAlertSetting
from app.tasks.domain_alert import trigger_domain_alert_check, send_dingtalk_markdown

router = APIRouter()


class DomainAlertPublic(BaseModel):
    enabled: bool
    reminder_days: int
    warning_days: int
    critical_days: int
    keyword: str
    webhook_configured: bool
    secret_configured: bool


class DomainAlertResponse(BaseModel):
    status: str
    data: DomainAlertPublic


class DomainAlertCredentials(BaseModel):
    webhook: Optional[str]
    secret: Optional[str]


class DomainAlertCredentialsResponse(BaseModel):
    status: str
    data: DomainAlertCredentials


class DomainAlertUpdate(BaseModel):
    enabled: bool
    reminder_days: int = Field(ge=1, le=365)
    warning_days: int = Field(ge=1, le=365)
    critical_days: int = Field(ge=0, le=365)
    keyword: str = Field(min_length=1, max_length=100)
    webhook: Optional[str] = Field(None, max_length=2048)
    secret: Optional[str] = Field(None, max_length=512)

    @field_validator("webhook")
    @classmethod
    def validate_webhook(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        parsed = urlparse(value)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "oapi.dingtalk.com"
            or parsed.path.rstrip("/") != "/robot/send"
            or not parse_qs(parsed.query).get("access_token")
        ):
            raise ValueError("必须填写钉钉自定义机器人的 HTTPS Webhook")
        return value

    @field_validator("secret")
    @classmethod
    def clean_secret(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("钉钉加签 Secret 不能为空")
        return value

    @field_validator("keyword")
    @classmethod
    def clean_keyword(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("钉钉自定义关键词不能为空")
        return value

    @model_validator(mode="after")
    def validate_thresholds(self):
        if not self.reminder_days > self.warning_days > self.critical_days:
            raise ValueError("阈值必须满足：提醒天数 > 告警天数 > 严重天数")
        return self


def require_settings_admin(x_settings_password: Optional[str] = Header(None)) -> None:
    expected = (app_settings.SETTINGS_ADMIN_PASSWORD or "").strip()
    if not expected:
        # 服务端未配置口令时，默认允许内网管理操作（免密模式）
        return
    if not x_settings_password or not hmac.compare_digest(x_settings_password.strip(), expected):
        raise HTTPException(status_code=403, detail="设置管理口令错误")


def get_or_create_setting(db: Session) -> DomainAlertSetting:
    config = db.query(DomainAlertSetting).filter(DomainAlertSetting.id == 1).first()
    if config is None:
        config = DomainAlertSetting(id=1)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def public_setting(config: DomainAlertSetting) -> dict:
    return {
        "enabled": config.enabled,
        "reminder_days": config.reminder_days,
        "warning_days": config.warning_days,
        "critical_days": config.critical_days,
        "keyword": config.keyword,
        "webhook_configured": bool(config.webhook_encrypted),
        "secret_configured": bool(config.secret_encrypted),
    }


@router.get("/domain-alert", response_model=DomainAlertResponse)
def get_domain_alert_setting(db: Session = Depends(get_db)):
    return {"status": "success", "data": public_setting(get_or_create_setting(db))}


@router.get(
    "/domain-alert/credentials",
    response_model=DomainAlertCredentialsResponse,
    dependencies=[Depends(require_settings_admin)],
)
def get_domain_alert_credentials(response: Response, db: Session = Depends(get_db)):
    config = get_or_create_setting(db)
    response.headers["Cache-Control"] = "no-store"
    return {
        "status": "success",
        "data": {
            "webhook": config.get_webhook(),
            "secret": config.get_secret(),
        },
    }


@router.put(
    "/domain-alert",
    response_model=DomainAlertResponse,
    dependencies=[Depends(require_settings_admin)],
)
def update_domain_alert_setting(payload: DomainAlertUpdate, db: Session = Depends(get_db)):
    config = get_or_create_setting(db)
    if payload.enabled and payload.webhook is None and not config.webhook_encrypted:
        raise HTTPException(status_code=422, detail="启用告警前必须配置钉钉 Webhook")

    config.enabled = payload.enabled
    config.reminder_days = payload.reminder_days
    config.warning_days = payload.warning_days
    config.critical_days = payload.critical_days
    config.keyword = payload.keyword
    if payload.webhook is not None:
        config.set_webhook(payload.webhook)
    if payload.secret is not None:
        config.set_secret(payload.secret)
    db.commit()
    db.refresh(config)
    if config.enabled:
        trigger_domain_alert_check()
    return {"status": "success", "data": public_setting(config)}


@router.post(
    "/domain-alert/test",
    dependencies=[Depends(require_settings_admin)],
)
def test_domain_alert_setting(db: Session = Depends(get_db)):
    config = get_or_create_setting(db)
    webhook = config.get_webhook()
    if not webhook:
        raise HTTPException(status_code=422, detail="请先保存钉钉 Webhook")
    try:
        send_dingtalk_markdown(
            webhook,
            config.get_secret(),
            f"{config.keyword}｜域名告警测试",
            f"#### {config.keyword}｜域名告警测试\n\n**配置状态**\n\n- Webhook 连接正常\n- 测试消息发送成功",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"钉钉测试消息发送失败: {exc}",
        ) from exc
    return {"status": "success", "message": "测试消息已发送"}
