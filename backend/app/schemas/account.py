import json
from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

def clean_val(val: Optional[str]) -> Optional[str]:
    if val is None:
        return None
    cleaned = val.strip()
    prefixes = ['ak:', 'sk:', 'ak：', 'sk：']
    for prefix in prefixes:
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()
    return cleaned

class CloudAccountBase(BaseModel):
    account_alias: str = Field(..., description="账号别名，用于标识账号，如 '生产账号'")
    access_key_id: str = Field(..., description="阿里云 AccessKey ID")
    sync_interval: Optional[int] = Field(24, description="同步间隔(小时)，0表示手动同步")

    @field_validator("account_alias", "access_key_id", mode="before")
    def validate_and_clean_base_fields(cls, v: str) -> str:
        cleaned = clean_val(v)
        if not cleaned:
            raise ValueError("输入参数清洗后不能为空白字符或纯前缀")
        if len(cleaned) > 100:
            raise ValueError("账号别名或 AccessKey ID 长度不能超过 100 个字符")
        return cleaned

    @field_validator("sync_interval")
    def validate_interval(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not 0 <= v <= 2147483647:
            raise ValueError("同步周期必须在数据库整数范围内")
        return v

class CloudAccountCreate(CloudAccountBase):
    access_key_secret: str = Field(..., max_length=4096, description="阿里云 AccessKey Secret")

    @field_validator("access_key_secret", mode="before")
    def validate_and_clean_secret(cls, v: str) -> str:
        cleaned = clean_val(v)
        if not cleaned:
            raise ValueError("AccessKey Secret 清洗后不能为空")
        return cleaned

class CloudAccountUpdate(BaseModel):
    account_alias: Optional[str] = Field(None, max_length=100)
    access_key_id: Optional[str] = Field(None, max_length=100)
    access_key_secret: Optional[str] = Field(None, max_length=4096)
    sync_interval: Optional[int] = None

    @field_validator("account_alias", "access_key_id", "access_key_secret", mode="before")
    def validate_and_clean_update_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = clean_val(v)
        if not cleaned:
            raise ValueError("更新字段清洗后不能为空")
        return cleaned

    @field_validator("sync_interval")
    def validate_update_interval(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not 0 <= v <= 2147483647:
            raise ValueError("同步周期必须在数据库整数范围内")
        return v

class CloudAccountResponse(CloudAccountBase):
    id: int
    last_synced_at: Optional[datetime] = None
    last_attempted_at: Optional[datetime] = None
    last_sync_status: str = "never"
    last_sync_error: Optional[str] = None
    last_sync_details: Optional[Dict[str, Any]] = None
    active_regions: Optional[Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("last_sync_status", mode="before")
    @classmethod
    def normalize_sync_status(cls, value: Optional[str]) -> str:
        return value or "never"

    @field_validator("last_sync_details", mode="before")
    @classmethod
    def parse_sync_details(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (TypeError, json.JSONDecodeError):
                return None
        return value

    @field_validator("active_regions", mode="before")
    @classmethod
    def parse_active_regions(cls, value):
        parsed = []
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except (TypeError, json.JSONDecodeError):
                parsed = []
        elif isinstance(value, (list, set)):
            parsed = list(value)
            
        if not parsed:
            return ["cn-hangzhou", "cn-beijing", "cn-shanghai", "cn-shenzhen"]
        return parsed

    class Config:
        from_attributes = True

class AccountSaveResponse(BaseModel):
    status: str
    data: CloudAccountResponse
    sync_queued: bool = False
    task_id: Optional[str] = None
    warning: Optional[str] = None
