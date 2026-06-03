"""
情绪分析师智能体
负责分析基金相关的市场情绪、新闻舆情、资金流向等
通过LLM进行推理分析
"""
from typing import Dict, Any

from app.agents.base import BaseAgent


class SentimentAgent(BaseAgent):
    """情绪分析师智能体"""
    
    def __init__(self):
        super().__init__("sentiment", "情绪分析师")
    
    async def analyze(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行情绪分析
        
        通过LLM驱动分析市场情绪、新闻舆情、资金流向等维度
        
        Args:
            fund_code: 基金代码
            context: 分析上下文，包含基金信息、新闻数据、资金流向等
            
        Returns:
            包含 score, summary, details 的分析结果字典
        """
        try:
            fund_info = context.get("fund_info", {})
            fund_name = fund_info.get("name", "未知基金")
            
            await self.add_thinking(f"开始分析基金 {fund_code} ({fund_name}) 的市场情绪...")
            
            result = await self.run_llm_analysis(
                fund_code=fund_code,
                context=context,
                use_rag=True,
                use_tools=True
            )

            if self.score is not None:
                self.confidence = self.confidence or 3
                self.data_sufficiency = self.data_sufficiency or "partial"

            await self.add_thinking(f"情绪分析完成：评分 {self.score}")
            
            return self.to_dict()
            
        except Exception as e:
            await self.add_thinking(f"情绪分析过程中发生错误: {str(e)}")
            self.score = None
            self.summary = "情绪分析数据源暂不可用，无法进行情绪分析"
            self.data_sufficient = False
            self.confidence = 1
            self.data_sufficiency = "insufficient"
            self.details = {
                "sentiment_score": 0,
                "error": str(e),
                "data_source": "错误回退"
            }
            return self.to_dict()
