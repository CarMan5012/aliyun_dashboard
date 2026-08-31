from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

if settings.is_sqlite:
    engine = create_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        connect_args={"check_same_thread": False},
    )

    # 启用 SQLite WAL (Write-Ahead Logging) 模式，大幅提升高并发读写性能与防死锁
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.close()
else:
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
