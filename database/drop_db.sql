-- =============================================
-- FundAI 数据库清理脚本
-- 数据库: PostgreSQL 15+
-- 创建时间: 2026-04-18
-- 说明: 删除所有数据库对象
-- =============================================

-- 注意: 此脚本会删除所有表和数据，请谨慎使用!

-- =============================================
-- 1. 删除视图
-- =============================================

DROP VIEW IF EXISTS v_fund_overview CASCADE;

-- =============================================
-- 2. 删除表 (按依赖关系倒序删除)
-- =============================================

-- 系统监控指标表
DROP TABLE IF EXISTS system_metrics CASCADE;

-- 审计日志表
DROP TABLE IF EXISTS audit_logs CASCADE;

-- 决策报告表
DROP TABLE IF EXISTS decision_reports CASCADE;

-- 智能体输出表
DROP TABLE IF EXISTS agent_outputs CASCADE;

-- 分析会话表
DROP TABLE IF EXISTS analysis_sessions CASCADE;

-- 基金费率表
DROP TABLE IF EXISTS fund_fees CASCADE;

-- 基金持仓表
DROP TABLE IF EXISTS fund_holdings CASCADE;

-- 基金净值表
DROP TABLE IF EXISTS fund_nav CASCADE;

-- 基金基础信息表
DROP TABLE IF EXISTS funds CASCADE;

-- 用户设置表
DROP TABLE IF EXISTS user_settings CASCADE;

-- 用户表
DROP TABLE IF EXISTS users CASCADE;

-- =============================================
-- 3. 删除函数
-- =============================================

DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- =============================================
-- 4. 删除枚举类型
-- =============================================

DROP TYPE IF EXISTS risk_preference CASCADE;
DROP TYPE IF EXISTS user_role CASCADE;

-- =============================================
-- 完成
-- =============================================

-- 显示剩余的表 (应该为空)
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
