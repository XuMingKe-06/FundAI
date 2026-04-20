"""
情绪分析师智能体
负责分析基金相关的市场情绪、新闻舆情、资金流向等
"""
from typing import Dict, Any, Optional
from decimal import Decimal
import asyncio
import random

from app.agents.base import BaseAgent


class SentimentAgent(BaseAgent):
    """情绪分析师智能体"""
    
    def __init__(self):
        super().__init__("sentiment", "情绪分析师")
        
        # 基金类型对应的默认情绪评分基准（-5到+5）
        self._type_sentiment_base = {
            "股票型": 0.5,
            "混合型": 0.3,
            "债券型": -0.2,
            "货币型": 0.0,
            "指数型": 0.4,
            "QDII": 0.2,
            "FOF": 0.1,
            "其他": 0.0
        }
        
        # 基金规模对应的情绪调整系数
        self._scale_adjustment = {
            "large": 0.3,      # 大型基金，市场关注度高
            "medium": 0.1,     # 中型基金
            "small": -0.1      # 小型基金，关注度较低
        }
    
    async def analyze(self, fund_code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行情绪分析
        
        Args:
            fund_code: 基金代码
            context: 分析上下文，包含基金信息等
            
        Returns:
            包含 score, summary, details 的分析结果字典
        """
        try:
            fund_info = context.get("fund_info", {})
            
            # 获取基金基本信息
            fund_name = fund_info.get("name", "未知基金")
            fund_type = fund_info.get("type", "其他")
            fund_scale = fund_info.get("scale", 0)
            
            self.add_thinking(f"开始分析基金 {fund_code} ({fund_name}) 的市场情绪...")
            await asyncio.sleep(0.2)
            
            # Step 1: 获取新闻舆情数据
            self.add_thinking("正在获取新闻舆情数据...")
            await asyncio.sleep(0.3)
            news_data = await self._get_news_sentiment(fund_code)
            self.add_thinking(f"新闻舆情分析完成：共{news_data['total']}条新闻，正面{news_data['positive']}条，负面{news_data['negative']}条")
            
            # RAG检索：检索行业新闻和研究报告
            try:
                news_knowledge = await self.retrieve_knowledge(
                    query=f"基金情绪分析 市场情绪 新闻舆情",
                    collection_name="fund_knowledge",
                    top_k=3
                )
                if news_knowledge:
                    self._rag_context.extend([
                        item.get("content", "") for item in news_knowledge if item.get("content")
                    ])
            except Exception as e:
                self.add_thinking(f"行业新闻检索失败: {str(e)}")
            
            # Step 2: 获取资金流向数据
            self.add_thinking("正在分析相关板块资金流向...")
            await asyncio.sleep(0.3)
            flow_data = await self._get_fund_flow(fund_code)
            self.add_thinking(f"资金流向分析完成：近5日净流入{flow_data['net_inflow_5d']}亿，近20日净流入{flow_data['net_inflow_20d']}亿")
            
            # Step 3: 获取社交媒体热度
            self.add_thinking("正在分析社交媒体热度...")
            await asyncio.sleep(0.3)
            social_data = await self._get_social_heat(fund_code)
            heat_level = "高" if social_data["heat_ratio"] > 1.5 else ("中" if social_data["heat_ratio"] > 0.8 else "低")
            self.add_thinking(f"社交热度分析完成：热度为历史均值的{social_data['heat_ratio']:.1f}倍，处于{heat_level}水平")
            
            # Step 4: 获取机构观点
            self.add_thinking("正在汇总机构观点...")
            await asyncio.sleep(0.3)
            institution_data = await self._get_institutional_views(fund_code)
            self.add_thinking(f"机构观点汇总：买入{institution_data['buy']}篇，增持{institution_data['overweight']}篇，中性{institution_data['neutral']}篇")
            
            # Step 5: 综合计算情绪评分
            self.add_thinking("正在综合计算情绪评分...")
            await asyncio.sleep(0.2)
            
            sentiment_score = self._calculate_sentiment_score(
                fund_type=fund_type,
                fund_scale=fund_scale,
                news_data=news_data,
                flow_data=flow_data,
                social_data=social_data,
                institution_data=institution_data
            )
            
            # 生成摘要
            summary = self._generate_summary(sentiment_score, news_data, flow_data)
            
            # 设置结果
            self.score = sentiment_score
            self.summary = summary
            self.details = {
                "sentiment_score": round(sentiment_score, 1),
                "news_analysis": news_data,
                "fund_flow": flow_data,
                "social_heat": social_data["heat_ratio"],
                "institutional_views": institution_data,
                "key_news": self._get_key_news_summary(news_data),
                "data_source": "模拟数据（真实数据源待集成）"
            }
            
            self.add_thinking(f"综合评估完成：情绪评分{sentiment_score:.1f}。{summary}")
            
            return self.to_dict()
            
        except Exception as e:
            self.add_thinking(f"情绪分析过程中发生错误: {str(e)}")
            # 返回默认的中性结果
            self.score = 0.0
            self.summary = "情绪分析暂时不可用，默认为中性"
            self.details = {
                "sentiment_score": 0,
                "error": str(e),
                "data_source": "错误回退"
            }
            return self.to_dict()
    
    async def _get_news_sentiment(self, fund_code: str) -> Dict[str, Any]:
        """
        获取新闻舆情数据
        
        TODO: 集成真实新闻数据源
        - 可接入财经新闻API（如新浪财经、东方财富等）
        - 使用NLP模型进行情感分析
        - 支持关键词过滤和相关性排序
        
        Args:
            fund_code: 基金代码
            
        Returns:
            新闻舆情分析结果
        """
        await asyncio.sleep(0.1)
        
        # TODO: 替换为真实新闻数据获取逻辑
        # 当前使用模拟数据框架
        total = random.randint(5, 20)
        positive = random.randint(1, total - 2)
        negative = random.randint(0, min(3, total - positive - 1))
        neutral = total - positive - negative
        
        return {
            "total": total,
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "sentiment_ratio": round(positive / max(negative, 1), 2)
        }
    
    async def _get_fund_flow(self, fund_code: str) -> Dict[str, Any]:
        """
        获取资金流向数据
        
        TODO: 集成真实资金流向数据源
        - 可接入交易所资金流向数据
        - 分析相关ETF/板块资金动向
        - 支持北向资金、南向资金追踪
        
        Args:
            fund_code: 基金代码
            
        Returns:
            资金流向分析结果
        """
        await asyncio.sleep(0.1)
        
        # TODO: 替换为真实资金流向数据获取逻辑
        # 当前使用模拟数据框架
        net_inflow_5d = round(random.uniform(-5.0, 10.0), 2)
        net_inflow_20d = round(net_inflow_5d + random.uniform(-3.0, 15.0), 2)
        
        return {
            "net_inflow_5d": net_inflow_5d,
            "net_inflow_20d": net_inflow_20d,
            "trend": "流入" if net_inflow_5d > 0 else "流出"
        }
    
    async def _get_social_heat(self, fund_code: str) -> Dict[str, Any]:
        """
        获取社交媒体热度数据
        
        TODO: 集成真实社交媒体数据源
        - 可接入微博、雪球、股吧等平台数据
        - 分析讨论热度和情感倾向
        - 追踪大V观点和散户情绪
        
        Args:
            fund_code: 基金代码
            
        Returns:
            社交热度分析结果
        """
        await asyncio.sleep(0.1)
        
        # TODO: 替换为真实社交媒体数据获取逻辑
        # 当前使用模拟数据框架
        heat_ratio = round(random.uniform(0.5, 2.0), 2)
        
        return {
            "heat_ratio": heat_ratio,
            "level": "high" if heat_ratio > 1.5 else ("medium" if heat_ratio > 0.8 else "low")
        }
    
    async def _get_institutional_views(self, fund_code: str) -> Dict[str, Any]:
        """
        获取机构观点数据
        
        TODO: 集成真实机构观点数据源
        - 可接入券商研报数据库
        - 分析机构评级变化趋势
        - 支持目标价和投资建议追踪
        
        Args:
            fund_code: 基金代码
            
        Returns:
            机构观点分析结果
        """
        await asyncio.sleep(0.1)
        
        # TODO: 替换为真实机构观点数据获取逻辑
        # 当前使用模拟数据框架
        buy = random.randint(0, 8)
        overweight = random.randint(0, 5)
        neutral = random.randint(0, 4)
        underweight = random.randint(0, 2)
        sell = random.randint(0, 1)
        
        return {
            "buy": buy,
            "overweight": overweight,
            "neutral": neutral,
            "underweight": underweight,
            "sell": sell,
            "total_reports": buy + overweight + neutral + underweight + sell
        }
    
    def _calculate_sentiment_score(
        self,
        fund_type: str,
        fund_scale: float,
        news_data: Dict[str, Any],
        flow_data: Dict[str, Any],
        social_data: Dict[str, Any],
        institution_data: Dict[str, Any]
    ) -> float:
        """
        综合计算情绪评分
        
        评分范围：-5 到 +5
        
        Args:
            fund_type: 基金类型
            fund_scale: 基金规模（亿元）
            news_data: 新闻舆情数据
            flow_data: 资金流向数据
            social_data: 社交热度数据
            institution_data: 机构观点数据
            
        Returns:
            情绪评分
        """
        # 基于基金类型的基准评分
        base_score = self._type_sentiment_base.get(fund_type, 0.0)
        
        # 新闻舆情评分贡献（权重0.3）
        news_ratio = news_data.get("sentiment_ratio", 1.0)
        news_score = min(2.0, max(-2.0, (news_ratio - 1) * 0.5))
        
        # 资金流向评分贡献（权重0.3）
        flow_5d = flow_data.get("net_inflow_5d", 0)
        flow_score = min(1.5, max(-1.5, flow_5d * 0.15))
        
        # 社交热度评分贡献（权重0.2）
        heat_ratio = social_data.get("heat_ratio", 1.0)
        heat_score = min(1.0, max(-0.5, (heat_ratio - 1) * 0.5))
        
        # 机构观点评分贡献（权重0.2）
        total_reports = institution_data.get("total_reports", 0)
        if total_reports > 0:
            positive_views = institution_data.get("buy", 0) + institution_data.get("overweight", 0)
            negative_views = institution_data.get("sell", 0) + institution_data.get("underweight", 0)
            institution_score = (positive_views - negative_views) / total_reports * 2
        else:
            institution_score = 0.0
        
        # 规模调整
        if fund_scale > 50:
            scale_adj = self._scale_adjustment["large"]
        elif fund_scale > 10:
            scale_adj = self._scale_adjustment["medium"]
        else:
            scale_adj = self._scale_adjustment["small"]
        
        # 综合评分
        final_score = (
            base_score +
            news_score * 0.3 +
            flow_score * 0.3 +
            heat_score * 0.2 +
            institution_score * 0.2 +
            scale_adj
        )
        
        # 限制在 -5 到 +5 范围内
        return max(-5.0, min(5.0, final_score))
    
    def _generate_summary(
        self,
        sentiment_score: float,
        news_data: Dict[str, Any],
        flow_data: Dict[str, Any]
    ) -> str:
        """
        生成情绪分析摘要
        
        Args:
            sentiment_score: 情绪评分
            news_data: 新闻舆情数据
            flow_data: 资金流向数据
            
        Returns:
            情绪分析摘要文本
        """
        if sentiment_score >= 3.0:
            level = "非常正面"
        elif sentiment_score >= 1.0:
            level = "偏正面"
        elif sentiment_score >= -1.0:
            level = "中性"
        elif sentiment_score >= -3.0:
            level = "偏负面"
        else:
            level = "非常负面"
        
        # 新闻舆情描述
        news_ratio = news_data.get("sentiment_ratio", 1.0)
        if news_ratio > 1.5:
            news_desc = "舆情偏正面"
        elif news_ratio < 0.7:
            news_desc = "舆情偏负面"
        else:
            news_desc = "舆情相对中性"
        
        # 资金流向描述
        flow_5d = flow_data.get("net_inflow_5d", 0)
        if flow_5d > 2:
            flow_desc = "资金持续流入"
        elif flow_5d < -2:
            flow_desc = "资金持续流出"
        else:
            flow_desc = "资金流向平稳"
        
        return f"市场情绪{level}，{news_desc}，{flow_desc}"
    
    def _get_key_news_summary(self, news_data: Dict[str, Any]) -> list:
        """
        获取关键新闻摘要
        
        TODO: 集成真实新闻标题提取逻辑
        
        Args:
            news_data: 新闻舆情数据
            
        Returns:
            关键新闻标题列表
        """
        # TODO: 替换为真实新闻标题提取逻辑
        # 当前返回模拟的关键新闻标题
        if news_data.get("positive", 0) > news_data.get("negative", 0):
            return [
                "相关板块迎来投资机会",
                "基金经理看好后市表现"
            ]
        elif news_data.get("negative", 0) > news_data.get("positive", 0):
            return [
                "市场波动加剧需谨慎",
                "短期调整压力较大"
            ]
        else:
            return [
                "市场维持震荡格局",
                "投资者情绪相对平稳"
            ]
