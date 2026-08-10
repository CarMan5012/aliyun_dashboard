import logging
from sqlalchemy import inspect, text
from app.db.session import engine

logger = logging.getLogger("app.db_migration")

def migrate_db():
    """
    检查并平滑升级数据库结构：
    1. cloud_accounts 增加 last_attempted_at 列
    2. resources 检查并增加 account_id 列
    3. 按 account_name 匹配回填 account_id，清理孤立数据
    4. 检查并强制设置 account_id 为 NOT NULL
    5. 检查并创建外键约束 (外键失败直接抛出异常中断启动)
    """
    logger.info("开始检查并执行数据库平滑迁移与结构校验...")
    inspector = inspect(engine)
    
    table_names = inspector.get_table_names()
    if "cloud_accounts" not in table_names or "resources" not in table_names:
        logger.info("数据库表尚未完全初始化，跳过增量迁移脚本（由 create_all 自动处理）。")
        return

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. 检查 cloud_accounts 是否缺少 last_attempted_at 列
            account_cols = [c["name"] for c in inspector.get_columns("cloud_accounts")]
            if "last_attempted_at" not in account_cols:
                logger.info("正在为 cloud_accounts 表添加 last_attempted_at 列...")
                conn.execute(text("ALTER TABLE cloud_accounts ADD COLUMN last_attempted_at DATETIME NULL;"))
            if "last_sync_status" not in account_cols:
                logger.info("正在为 cloud_accounts 表添加最近同步状态列...")
                conn.execute(text("ALTER TABLE cloud_accounts ADD COLUMN last_sync_status VARCHAR(20) NOT NULL DEFAULT 'never';"))
                conn.execute(text("UPDATE cloud_accounts SET last_sync_status = 'success' WHERE last_synced_at IS NOT NULL;"))
            if "last_sync_error" not in account_cols:
                conn.execute(text("ALTER TABLE cloud_accounts ADD COLUMN last_sync_error TEXT NULL;"))
            if "last_sync_details" not in account_cols:
                conn.execute(text("ALTER TABLE cloud_accounts ADD COLUMN last_sync_details TEXT NULL;"))
            if "active_regions" not in account_cols:
                logger.info("正在为 cloud_accounts 表添加 active_regions 列...")
                conn.execute(text("ALTER TABLE cloud_accounts ADD COLUMN active_regions TEXT NULL;"))
            
            default_regions_json = '["cn-hangzhou", "cn-beijing", "cn-shanghai", "cn-shenzhen"]'
            conn.execute(text(f"UPDATE cloud_accounts SET active_regions = '{default_regions_json}' WHERE active_regions IS NULL OR active_regions = '';"))

            if "domain_alert_settings" in table_names:
                alert_cols = [c["name"] for c in inspector.get_columns("domain_alert_settings")]
                if "keyword" not in alert_cols:
                    logger.info("正在为域名告警配置添加自定义关键词列...")
                    conn.execute(text(
                        "ALTER TABLE domain_alert_settings "
                        "ADD COLUMN keyword VARCHAR(100) NOT NULL DEFAULT '域名告警';"
                    ))

            # 2. 检查 resources 表 account_id 列是否存在
            resource_cols = {c["name"]: c for c in inspector.get_columns("resources")}
            if "account_id" not in resource_cols:
                logger.info("正在为 resources 表添加 account_id 列...")
                conn.execute(text("ALTER TABLE resources ADD COLUMN account_id INT NULL;"))
                
                # 回填数据
                logger.info("正在执行旧资源数据的 account_id 回填...")
                conn.execute(text("""
                    UPDATE resources r 
                    JOIN cloud_accounts a ON r.account_name = a.account_alias 
                    SET r.account_id = a.id;
                """))
                
                # 检查清理孤立数据
                orphaned_rows = conn.execute(text("""
                    SELECT id, account_name, resource_type, search_key 
                    FROM resources 
                    WHERE account_id IS NULL;
                """)).fetchall()
                
                if orphaned_rows:
                    logger.warning(f"【审计清单】发现 {len(orphaned_rows)} 条无法匹配到云账号的孤立资源数据:")
                    for row in orphaned_rows:
                        logger.warning(f"  - 孤立资源 ID={row[0]}, 旧账号别名='{row[1]}', 类型={row[2]}, 核心键={row[3]}")
                    
                    logger.info("正在清理无法关联账号的孤立旧资源数据...")
                    conn.execute(text("DELETE FROM resources WHERE account_id IS NULL;"))

            # 3. 重新检查并确保 account_id 不包含 NULL 后改设为 NOT NULL
            inspector_updated = inspect(conn)
            resource_cols_updated = {c["name"]: c for c in inspector_updated.get_columns("resources")}
            if "account_id" in resource_cols_updated:
                # 再次安全检查是否存在 NULL 的记录，有则清理
                del_res = conn.execute(text("DELETE FROM resources WHERE account_id IS NULL;"))
                if del_res.rowcount > 0:
                    logger.info(f"审计清理：消除了 {del_res.rowcount} 条未关联的旧资源数据。")
                if resource_cols_updated["account_id"].get("nullable", True) and engine.dialect.name == "mysql":
                    logger.info("正在强制设置 resources.account_id 列为 NOT NULL...")
                    conn.execute(text("ALTER TABLE resources MODIFY account_id INT NOT NULL;"))

            # 4. 独立检查并建立外键约束
            existing_fks = inspector_updated.get_foreign_keys("resources")
            has_account_fk = any(
                fk.get("referred_table") == "cloud_accounts" and "account_id" in fk.get("constrained_columns", [])
                for fk in existing_fks
            )

            dialect = engine.dialect.name
            if not has_account_fk and dialect == "mysql":
                logger.info("正在为 resources 表添加 account_id 外键约束 (ON DELETE CASCADE)...")
                try:
                    conn.execute(text("""
                        ALTER TABLE resources 
                        ADD CONSTRAINT fk_resources_account_id 
                        FOREIGN KEY (account_id) REFERENCES cloud_accounts(id) 
                        ON DELETE CASCADE;
                    """))
                    logger.info("成功建立 resources.account_id 外键约束。")
                except Exception as fke:
                    logger.error(f"严重错误：创建数据库外键约束失败: {fke}")
                    raise RuntimeError(f"外键约束创建失败，拒绝降级运行: {fke}") from fke

            trans.commit()
            logger.info("数据库平滑升级与迁移校验完成。")
        except Exception as e:
            trans.rollback()
            logger.error(f"数据库迁移过程中出错: {e}")
            raise e
