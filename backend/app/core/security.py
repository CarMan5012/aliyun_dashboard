from cryptography.fernet import Fernet
from app.core.config import settings

if not settings.MASTER_KEY:
    raise ValueError("CRITICAL: ASSETVISTA_MASTER_KEY 环境变量未配置！系统拒绝启动。")

# 初始化加密套件
try:
    _cipher_suite = Fernet(settings.MASTER_KEY.encode())
except Exception as e:
    raise ValueError(f"CRITICAL: ASSETVISTA_MASTER_KEY 格式不正确，初始化 Fernet 失败: {e}")

def encrypt_secret(raw_secret: str) -> str:
    """加密明文密钥为密文"""
    return _cipher_suite.encrypt(raw_secret.encode()).decode()

def decrypt_secret(encrypted_secret: str) -> str:
    """将密文解密为明文 (用完即焚)"""
    return _cipher_suite.decrypt(encrypted_secret.encode()).decode()
