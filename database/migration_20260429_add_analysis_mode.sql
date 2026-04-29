-- =============================================
-- 迁移脚本: 添加 analysis_mode 字段
-- 描述: analysis_sessions 表增加分析模式字段，支持串行/并行切换
-- 日期: 2026-04-29
-- =============================================

-- 添加 analysis_mode 列（默认并行模式）
ALTER TABLE analysis_sessions
ADD COLUMN analysis_mode VARCHAR(20) NOT NULL DEFAULT 'parallel';
