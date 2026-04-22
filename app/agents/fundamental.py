"""
基本面分析师智能体

负责基金经理能力评估、持仓结构分析、业绩表现评价
使用LLM进行推理分析，通过工具调用获取数据
"""
from typing import Dict, Any

from app.agents.base import BaseAgent


class FundamentalAgent(BaseAgent):
    """
    基本面分析师智能体
    
    分析维度：
    1. 基金经理能力评估 - 从业年限、历史业绩、管理规模
    2. 持仓结构分析 - 前十大持仓占比、行业分布集中度
    3. 业绩表现评价 - 累计收益率、超额收益、信息比率
    
    可用工具：
    - get_fund_info: 获取基金基础信息
    - get_nav_history: 获取净值历史数据
    - get_holdings: 获取持仓信息
    - get_fund_manager: 获取基金经理信息
    - get_fund_fees: 获取费率信息
    """
    
    def __init__(self):
        super().__init__("fundamental", "基本面分析师")
    
    async def analyze(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行基本面分析
        
        通过LLM驱动的分析流程，综合评估基金经理能力、持仓结构和业绩表现
        
        Args:
            fund_code: 基金代码
            context: 分析上下文，可包含预设的基金信息、持仓数据等
            
        Returns:
            分析结果字典，包含评分、摘要和详细信息
        """
        await self.add_thinking(f"开始对基金 {fund_code} 进行基本面分析...")
        
        result = await self.run_llm_analysis(
            fund_code=fund_code,
            context=context,
            use_rag=True,
            use_tools=True
        )
        
        await self.add_thinking(f"基本面分析完成，评分: {self.score}")
        
        return self.to_dict()
