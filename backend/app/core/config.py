import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "阿里云资源看板"
    API_V1_STR: str = "/api/v1"
    
    # 数据库类型与配置 (支持 sqlite 与 mysql，默认若未配置 MYSQL_HOST 则为 sqlite)
    DB_TYPE: str = os.getenv("DB_TYPE", "auto")  # auto | sqlite | mysql
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "/app/data/aliyun.db")

    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "password")
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "")  # 为空时自动使用轻量 SQLite
    MYSQL_PORT: str = os.getenv("MYSQL_PORT", "3306")
    MYSQL_DB: str = os.getenv("MYSQL_DB", "assetvista")

    # 安全配置：加解密主密钥，必须在环境部署时注入
    MASTER_KEY: str = os.getenv("ASSETVISTA_MASTER_KEY", "")
    SETTINGS_ADMIN_PASSWORD: str = os.getenv("SETTINGS_ADMIN_PASSWORD", "")

    # 国务院办公厅 2026 年节假日安排，可在部署环境中覆盖。
    CHINA_HOLIDAY_RANGES: str = os.getenv(
        "CHINA_HOLIDAY_RANGES",
        "2026-01-01:2026-01-03,2026-02-15:2026-02-23,2026-04-04:2026-04-06,"
        "2026-05-01:2026-05-05,2026-06-19:2026-06-21,2026-09-25:2026-09-27,"
        "2026-10-01:2026-10-07",
    )
    CHINA_EXTRA_WORKDAYS: str = os.getenv(
        "CHINA_EXTRA_WORKDAYS",
        "2026-01-04,2026-02-14,2026-02-28,2026-05-09,2026-09-20,2026-10-10",
    )

    @property
    def is_sqlite(self) -> bool:
        if self.DB_TYPE.lower() == "sqlite":
            return True
        if self.DB_TYPE.lower() == "mysql":
            return False
        return not bool(self.MYSQL_HOST.strip())

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.is_sqlite:
            # 确保本地 sqlite 目录存在
            os.makedirs(os.path.dirname(os.path.abspath(self.SQLITE_DB_PATH)), exist_ok=True)
            return f"sqlite:///{self.SQLITE_DB_PATH}"

        from sqlalchemy.engine import URL
        return URL.create(
            drivername="mysql+pymysql",
            username=self.MYSQL_USER,
            password=self.MYSQL_PASSWORD,
            host=self.MYSQL_HOST,
            port=int(self.MYSQL_PORT),
            database=self.MYSQL_DB,
            query={"charset": "utf8mb4"}
        ).render_as_string(hide_password=False)

settings = Settings()
