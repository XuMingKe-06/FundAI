-- =============================================
-- 迁移脚本: 添加 previous_session_id 字段
-- 描述: analysis_sessions 表增加自引用外键，支持重新分析功能
-- 日期: 2026-04-29
-- =============================================

-- 添加 previous_session_id 列（允许为空）
ALTER TABLE analysis_sessions
ADD COLUMN previous_session_id UUID REFERENCES analysis_sessions(id);

-- 创建索引
CREATE INDEX IF NOT EXISTS ix_analysis_sessions_previous_session_id
ON analysis_sessions(previous_session_id);
