/**
 * 工具名称中文映射与结果格式化工具
 *
 * 将后端智能体调用的英文工具名映射为用户友好的中文名称，
 * 并提供工具执行结果的格式化展示功能
 */

/* 工具名 -> 中文名映射表 */
const TOOL_NAME_MAP: Record<string, string> = {
  /* 基金数据类 */
  get_fund_info: '获取基金基础信息',
  get_nav_history: '获取净值历史数据',
  get_holdings: '获取持仓信息',
  get_fund_manager: '获取基金经理信息',
  get_fund_fees: '获取费率信息',

  /* 市场数据类 */
  get_news_sentiment: '获取新闻舆情',
  get_fund_flow: '获取资金流向',
  get_social_heat: '获取社交媒体热度',
  get_institutional_views: '获取机构观点',
  get_market_index: '获取市场指数',

  /* 技术指标类 */
  calculate_ma: '计算移动平均线',
  calculate_macd: '计算MACD指标',
  calculate_rsi: '计算RSI指标',
  calculate_percentile: '计算估值分位数',

  /* 风险指标类 */
  calculate_volatility: '计算年化波动率',
  calculate_max_drawdown: '计算最大回撤',
  calculate_sharpe_ratio: '计算夏普比率',
  calculate_beta: '计算Beta系数',
}

/**
 * 获取工具的中文名称
 * @param toolName 英文工具名
 * @returns 中文名称，若未匹配则返回原始英文名
 */
export function getToolChineseName(toolName: string): string {
  return TOOL_NAME_MAP[toolName] || toolName
}

/**
 * 格式化工具执行结果为用户可读的中文描述
 * @param toolName 英文工具名
 * @param resultData 工具返回的 data 字段内容
 * @returns 格式化后的中文结果描述
 */
export function formatToolResult(toolName: string, resultData: Record<string, any>): string {
  if (!resultData || typeof resultData !== 'object') return ''

  const formatter = TOOL_RESULT_FORMATTERS[toolName]
  if (formatter) {
    return formatter(resultData)
  }

  return ''
}

/**
 * 将思考消息中的英文工具名替换为中文名
 * 用于处理后端推送的 thinking 事件中包含的 "调用工具: get_xxx" 等文本
 * @param text 原始思考文本
 * @returns 替换后的中文文本
 */
export function replaceToolNameInText(text: string): string {
  if (!text) return text

  let result = text

  /* 替换 "调用工具: xxx" 模式 */
  result = result.replace(
    /调用工具:\s*(\w+)/g,
    (_match, toolName: string) => {
      const chineseName = getToolChineseName(toolName)
      return chineseName !== toolName ? `正在${chineseName}...` : `调用工具: ${toolName}`
    }
  )

  /* 替换 "工具 xxx 执行成功" 模式 */
  result = result.replace(
    /工具\s*(\w+)\s*执行成功/g,
    (_match, toolName: string) => {
      const chineseName = getToolChineseName(toolName)
      return chineseName !== toolName ? `${chineseName}完成` : `工具 ${toolName} 执行成功`
    }
  )

  /* 替换 "工具 xxx 执行失败" 模式 */
  result = result.replace(
    /工具\s*(\w+)\s*执行失败/g,
    (_match, toolName: string) => {
      const chineseName = getToolChineseName(toolName)
      return chineseName !== toolName ? `${chineseName}失败` : `工具 ${toolName} 执行失败`
    }
  )

  return result
}

/* 各工具的结果格式化函数 */
const TOOL_RESULT_FORMATTERS: Record<string, (data: Record<string, any>) => string> = {
  /* 基金数据类 */
  get_fund_info: (data) => {
    const parts: string[] = []
    if (data.fund_name) parts.push(`基金名称：${data.fund_name}`)
    if (data.fund_type) parts.push(`类型：${data.fund_type}`)
    if (data.scale || data.current_scale) parts.push(`规模：${data.scale || data.current_scale}`)
    return parts.join('，')
  },

  get_nav_history: (data) => {
    if (Array.isArray(data)) {
      return `获取到 ${data.length} 条净值记录`
    }
    if (data.data_points) {
      return `获取到 ${data.data_points} 条净值记录`
    }
    return '净值历史数据获取成功'
  },

  get_holdings: (data) => {
    const parts: string[] = []
    if (data.stock_list && Array.isArray(data.stock_list)) {
      parts.push(`${data.stock_list.length} 只股票持仓`)
    }
    if (data.bond_list && Array.isArray(data.bond_list)) {
      parts.push(`${data.bond_list.length} 只债券持仓`)
    }
    if (data.industry_distribution) {
      parts.push('行业分布数据')
    }
    return parts.length > 0 ? parts.join('，') : '持仓数据获取成功'
  },

  get_fund_manager: (data) => {
    const parts: string[] = []
    if (data.name || data.manager_name) parts.push(`基金经理：${data.name || data.manager_name}`)
    if (data.work_years || data.tenure) parts.push(`从业年限：${data.work_years || data.tenure}`)
    return parts.length > 0 ? parts.join('，') : '基金经理信息获取成功'
  },

  get_fund_fees: (data) => {
    const parts: string[] = []
    if (data.purchase_fee !== undefined) parts.push(`申购费率：${data.purchase_fee}`)
    if (data.redemption_fee !== undefined) parts.push(`赎回费率：${data.redemption_fee}`)
    if (data.management_fee !== undefined) parts.push(`管理费：${data.management_fee}`)
    if (data.custody_fee !== undefined) parts.push(`托管费：${data.custody_fee}`)
    return parts.length > 0 ? parts.join('，') : '费率信息获取成功'
  },

  /* 市场数据类 */
  get_news_sentiment: (data) => {
    const parts: string[] = []
    if (data.positive !== undefined) parts.push(`正面：${data.positive}条`)
    if (data.negative !== undefined) parts.push(`负面：${data.negative}条`)
    if (data.neutral !== undefined) parts.push(`中性：${data.neutral}条`)
    if (data.sentiment_score !== undefined) parts.push(`情感得分：${data.sentiment_score}`)
    return parts.length > 0 ? parts.join('，') : '新闻舆情数据获取成功'
  },

  get_fund_flow: (data) => {
    const parts: string[] = []
    if (data.net_inflow_5d !== undefined) parts.push(`近5日净流入：${data.net_inflow_5d}`)
    if (data.net_inflow_20d !== undefined) parts.push(`近20日净流入：${data.net_inflow_20d}`)
    if (data.trend) parts.push(`趋势：${data.trend}`)
    return parts.length > 0 ? parts.join('，') : '资金流向数据获取成功'
  },

  get_social_heat: (data) => {
    const parts: string[] = []
    if (data.heat_ratio !== undefined) parts.push(`热度比率：${data.heat_ratio}`)
    if (data.level) parts.push(`热度等级：${data.level}`)
    if (data.trend) parts.push(`趋势：${data.trend}`)
    return parts.length > 0 ? parts.join('，') : '社交媒体热度数据获取成功'
  },

  get_institutional_views: (data) => {
    const parts: string[] = []
    if (data.buy !== undefined) parts.push(`买入：${data.buy}`)
    if (data.overweight !== undefined) parts.push(`增持：${data.overweight}`)
    if (data.neutral !== undefined) parts.push(`中性：${data.neutral}`)
    if (data.underweight !== undefined) parts.push(`减持：${data.underweight}`)
    if (data.sell !== undefined) parts.push(`卖出：${data.sell}`)
    if (data.consensus) parts.push(`共识：${data.consensus}`)
    return parts.length > 0 ? parts.join('，') : '机构观点数据获取成功'
  },

  get_market_index: (data) => {
    const parts: string[] = []
    if (data.index_name) parts.push(`指数：${data.index_name}`)
    if (data.data_points) parts.push(`${data.data_points} 条数据`)
    return parts.length > 0 ? parts.join('，') : '市场指数数据获取成功'
  },

  /* 技术指标类 */
  calculate_ma: (data) => {
    const parts: string[] = []
    if (data.ma_value !== undefined) parts.push(`MA${data.period || 20}：${data.ma_value}`)
    if (data.trend) parts.push(`趋势：${data.trend}`)
    if (data.ma_trend) parts.push(`均线方向：${data.ma_trend}`)
    if (data.current_position) parts.push(`当前位置：均线${data.current_position}`)
    return parts.join('，')
  },

  calculate_macd: (data) => {
    const parts: string[] = []
    if (data.dif !== undefined) parts.push(`DIF：${data.dif}`)
    if (data.dea !== undefined) parts.push(`DEA：${data.dea}`)
    if (data.macd_histogram !== undefined) parts.push(`MACD柱：${data.macd_histogram}`)
    if (data.signal_type) parts.push(`信号：${data.signal_type}`)
    return parts.join('，')
  },

  calculate_rsi: (data) => {
    const parts: string[] = []
    if (data.rsi_value !== undefined) parts.push(`RSI：${data.rsi_value}`)
    if (data.status) parts.push(`状态：${data.status}`)
    if (data.signal) parts.push(`信号：${data.signal}`)
    return parts.join('，')
  },

  calculate_percentile: (data) => {
    const parts: string[] = []
    if (data.percentile !== undefined) parts.push(`分位数：${data.percentile}%`)
    if (data.valuation_level) parts.push(`估值水平：${data.valuation_level}`)
    if (data.suggestion) parts.push(`建议：${data.suggestion}`)
    return parts.join('，')
  },

  /* 风险指标类 */
  calculate_volatility: (data) => {
    const parts: string[] = []
    if (data.annual_volatility !== undefined) parts.push(`年化波动率：${data.annual_volatility}%`)
    if (data.daily_volatility !== undefined) parts.push(`日波动率：${data.daily_volatility}%`)
    return parts.join('，')
  },

  calculate_max_drawdown: (data) => {
    const parts: string[] = []
    if (data.max_drawdown !== undefined) parts.push(`最大回撤：${data.max_drawdown}%`)
    if (data.peak_value !== undefined) parts.push(`峰值：${data.peak_value}`)
    if (data.trough_value !== undefined) parts.push(`谷值：${data.trough_value}`)
    return parts.join('，')
  },

  calculate_sharpe_ratio: (data) => {
    const parts: string[] = []
    if (data.sharpe_ratio !== undefined) parts.push(`夏普比率：${data.sharpe_ratio}`)
    if (data.annual_return !== undefined) parts.push(`年化收益率：${data.annual_return}%`)
    if (data.annual_volatility !== undefined) parts.push(`年化波动率：${data.annual_volatility}%`)
    return parts.join('，')
  },

  calculate_beta: (data) => {
    const parts: string[] = []
    if (data.beta !== undefined) parts.push(`Beta系数：${data.beta}`)
    if (data.correlation !== undefined) parts.push(`相关性：${data.correlation}`)
    return parts.join('，')
  },
}
