from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,       # 每次从连接池获取连接前测试连通性，防止 MySQL 连接被杀
    pool_size=10,             # 基础连接池大小
    max_overflow=20           # 允许的最大超出连接数
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """获取数据库 Session 依赖"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
