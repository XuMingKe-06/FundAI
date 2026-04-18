-- =============================================
-- FundAI 数据库初始化脚本
-- 数据库: PostgreSQL 15+
-- 创建时间: 2026-04-18
-- =============================================

-- 注意: 请先创建数据库
-- CREATE DATABASE fund_analysis;

-- =============================================
-- 1. 创建枚举类型
-- =============================================

-- 用户角色类型
CREATE TYPE user_role AS ENUM ('investor', 'advisor', 'admin');

-- 风险偏好类型
CREATE TYPE risk_preference AS ENUM ('conservative', 'neutral', 'aggressive');

-- =============================================
-- 2. 创建表结构
-- =============================================

-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(20) NOT NULL UNIQUE,
    username VARCHAR(50) UNIQUE,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    salt VARCHAR(64) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'investor',
    risk_preference VARCHAR(20) NOT NULL DEFAULT 'neutral',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- 用户设置表
CREATE TABLE user_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    default_display_preference VARCHAR NOT NULL DEFAULT '{}',
    notification_settings VARCHAR NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 基金基础信息表
CREATE TABLE funds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fund_code VARCHAR(6) NOT NULL UNIQUE,
    fund_name VARCHAR(200) NOT NULL,
    fund_type VARCHAR(50) NOT NULL,
    fund_manager VARCHAR(100),
    establish_date DATE NOT NULL,
    management_fee NUMERIC(5, 4),
    custody_fee NUMERIC(5, 4),
    current_scale NUMERIC(20, 2),
    purchase_status VARCHAR(20) NOT NULL DEFAULT 'normal',
    redemption_status VARCHAR(20) NOT NULL DEFAULT 'normal',
    benchmark VARCHAR(200),
    is_qdii BOOLEAN NOT NULL DEFAULT FALSE,
    share_class VARCHAR(1),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_funds_code ON funds(fund_code);
CREATE INDEX idx_funds_name ON funds(fund_name);
CREATE INDEX idx_funds_type ON funds(fund_type);

-- 基金净值表
CREATE TABLE fund_nav (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fund_code VARCHAR(6) NOT NULL,
    nav_date DATE NOT NULL,
    unit_nav NUMERIC(10, 4) NOT NULL,
    accumulated_nav NUMERIC(10, 4) NOT NULL,
    daily_growth_rate NUMERIC(8, 4),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (fund_code, nav_date),
    FOREIGN KEY (fund_code) REFERENCES funds(fund_code) ON DELETE CASCADE
);

CREATE INDEX idx_fund_nav_code ON fund_nav(fund_code);
CREATE INDEX idx_fund_nav_date ON fund_nav(nav_date);

-- 基金持仓表
CREATE TABLE fund_holdings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fund_code VARCHAR(6) NOT NULL,
    report_date DATE NOT NULL,
    stock_code VARCHAR(10),
    stock_name VARCHAR(100),
    holding_ratio NUMERIC(6, 2),
    holding_shares NUMERIC(20, 2),
    holding_value NUMERIC(20, 2),
    industry VARCHAR(50),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fund_code) REFERENCES funds(fund_code) ON DELETE CASCADE
);

CREATE INDEX idx_fund_holdings_code ON fund_holdings(fund_code);
CREATE INDEX idx_fund_holdings_date ON fund_holdings(report_date);

-- 基金费率表
CREATE TABLE fund_fees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fund_code VARCHAR(6) NOT NULL,
    fee_type VARCHAR(20) NOT NULL,
    min_holding_days INTEGER,
    max_holding_days INTEGER,
    fee_rate NUMERIC(5, 4) NOT NULL,
    is_discounted BOOLEAN NOT NULL DEFAULT FALSE,
    discount_rate NUMERIC(3, 2),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fund_code) REFERENCES funds(fund_code) ON DELETE CASCADE
);

CREATE INDEX idx_fund_fees_code ON fund_fees(fund_code);

-- 分析会话表
CREATE TABLE analysis_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    fund_code VARCHAR(6) NOT NULL,
    user_preference VARCHAR(20) NOT NULL DEFAULT 'neutral',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (fund_code) REFERENCES funds(fund_code)
);

CREATE INDEX idx_analysis_sessions_user ON analysis_sessions(user_id);
CREATE INDEX idx_analysis_sessions_fund ON analysis_sessions(fund_code);
CREATE INDEX idx_analysis_sessions_status ON analysis_sessions(status);

-- 智能体输出表
CREATE TABLE agent_outputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    agent_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    score NUMERIC(3, 1),
    summary TEXT,
    details JSONB,
    thinking_process TEXT,
    tools_called JSONB,
    error_message TEXT,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,
    FOREIGN KEY (session_id) REFERENCES analysis_sessions(id) ON DELETE CASCADE
);

CREATE INDEX idx_agent_outputs_session ON agent_outputs(session_id);
CREATE INDEX idx_agent_outputs_type ON agent_outputs(agent_type);

-- 决策报告表
CREATE TABLE decision_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL UNIQUE,
    short_term_decision JSONB NOT NULL,
    long_term_decision JSONB NOT NULL,
    cost_matrix JSONB NOT NULL,
    risk_alerts JSONB NOT NULL,
    agent_scores JSONB NOT NULL,
    trend_chart JSONB,
    disclaimer TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES analysis_sessions(id) ON DELETE CASCADE
);

-- 审计日志表
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    username VARCHAR(100),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(100),
    ip_address VARCHAR(45),
    user_agent TEXT,
    request_data JSONB,
    response_status INTEGER,
    response_data JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);

-- 系统监控指标表
CREATE TABLE system_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_type VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value VARCHAR(50) NOT NULL,
    unit VARCHAR(20),
    tags JSONB,
    recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_metrics_type ON system_metrics(metric_type);
CREATE INDEX idx_system_metrics_recorded ON system_metrics(recorded_at);

-- =============================================
-- 3. 创建更新时间触发器
-- =============================================

-- 创建更新时间函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $BODY$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$BODY$ LANGUAGE plpgsql;

-- 为需要的表添加触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_settings_updated_at BEFORE UPDATE ON user_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_funds_updated_at BEFORE UPDATE ON funds
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fund_fees_updated_at BEFORE UPDATE ON fund_fees
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================
-- 4. 插入测试数据
-- =============================================

-- 插入测试用户
-- 密码: password123 (使用bcrypt加密)
INSERT INTO users (id, phone, username, email, password_hash, salt, role, risk_preference, is_active) VALUES
('00000000-0000-0000-0000-000000000001', '13800138000', 'testuser', 'test@example.com', 
 '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYqVqxqZ', 'test_salt_12345678', 'investor', 'neutral', TRUE),
('00000000-0000-0000-0000-000000000002', '13900139000', 'admin', 'admin@example.com',
 '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYqVqxqZ', 'admin_salt_12345678', 'admin', 'neutral', TRUE);

-- 插入用户设置
INSERT INTO user_settings (user_id, default_display_preference, notification_settings) VALUES
('00000000-0000-0000-0000-000000000001', '{"theme": "light", "language": "zh-CN"}', '{"email": true, "sms": true}'),
('00000000-0000-0000-0000-000000000002', '{"theme": "dark", "language": "zh-CN"}', '{"email": true, "sms": false}');

-- 插入测试基金数据
INSERT INTO funds (fund_code, fund_name, fund_type, fund_manager, establish_date, management_fee, custody_fee, current_scale, purchase_status, redemption_status, benchmark, is_qdii, share_class) VALUES
('000001', '华夏成长混合', 'mixed', '王某某', '2001-12-18', 0.0150, 0.0025, 8560000000.00, 'normal', 'normal', '沪深300指数收益率*80%+中证全债指数收益率*20%', FALSE, 'A'),
('110022', '易方达消费行业', 'stock', '张某某', '2010-08-20', 0.0150, 0.0025, 3280000000.00, 'normal', 'normal', '中证消费指数收益率*80%+中证全债指数收益率*20%', FALSE, 'A'),
('161725', '招商中证白酒', 'index', '李某某', '2015-05-27', 0.0075, 0.0020, 5680000000.00, 'normal', 'normal', '中证白酒指数收益率*95%+银行活期存款利率*5%', FALSE, NULL),
('519778', '交银定期支付双息', 'bond', '赵某某', '2013-06-05', 0.0060, 0.0015, 1250000000.00, 'normal', 'normal', '中证全债指数收益率', FALSE, 'A');

-- 插入净值历史数据 (近90天)
-- 使用generate_series生成日期序列
INSERT INTO fund_nav (fund_code, nav_date, unit_nav, accumulated_nav, daily_growth_rate)
SELECT 
    '000001' as fund_code,
    (CURRENT_DATE - INTERVAL '90 days' + (i || ' days')::INTERVAL)::DATE as nav_date,
    (1.2500 + ((i % 10 - 5) * 0.002) + (i * 0.001))::NUMERIC(10, 4) as unit_nav,
    (2.2500 + ((i % 10 - 5) * 0.002) + (i * 0.001))::NUMERIC(10, 4) as accumulated_nav,
    CASE WHEN i > 0 THEN (((i % 10 - 5) * 0.002) / 1.2500)::NUMERIC(8, 4) ELSE NULL END as daily_growth_rate
FROM generate_series(0, 89) as i;

-- 插入持仓数据
INSERT INTO fund_holdings (fund_code, report_date, stock_code, stock_name, holding_ratio, holding_value, industry) VALUES
('000001', '2026-03-31', '600519', '贵州茅台', 8.56, 732000000.00, '食品饮料'),
('000001', '2026-03-31', '000858', '五粮液', 6.23, 533000000.00, '食品饮料'),
('000001', '2026-03-31', '000333', '美的集团', 5.12, 438000000.00, '家用电器'),
('000001', '2026-03-31', '002475', '立讯精密', 4.85, 415000000.00, '电子'),
('000001', '2026-03-31', '300750', '宁德时代', 4.32, 370000000.00, '电气设备');

-- 插入费率数据
INSERT INTO fund_fees (fund_code, fee_type, min_holding_days, max_holding_days, fee_rate, is_discounted, discount_rate) VALUES
('000001', 'purchase', NULL, NULL, 0.0150, TRUE, 0.10),
('000001', 'redemption', 0, 7, 0.0150, FALSE, NULL),
('000001', 'redemption', 7, 30, 0.0075, FALSE, NULL),
('000001', 'redemption', 30, 365, 0.0050, FALSE, NULL),
('000001', 'redemption', 365, 730, 0.0025, FALSE, NULL),
('000001', 'redemption', 730, NULL, 0.0000, FALSE, NULL);

-- =============================================
-- 5. 创建视图 (可选)
-- =============================================

-- 基金概览视图
CREATE VIEW v_fund_overview AS
SELECT 
    f.fund_code,
    f.fund_name,
    f.fund_type,
    f.fund_manager,
    f.current_scale,
    fn.unit_nav,
    fn.accumulated_nav,
    fn.daily_growth_rate,
    fn.nav_date
FROM funds f
LEFT JOIN LATERAL (
    SELECT unit_nav, accumulated_nav, daily_growth_rate, nav_date
    FROM fund_nav fn
    WHERE fn.fund_code = f.fund_code
    ORDER BY fn.nav_date DESC
    LIMIT 1
) fn ON TRUE;

-- =============================================
-- 完成
-- =============================================

-- 显示创建的表
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
