"""
Akshare 数据源适配器 - 作为备用数据源
"""
import logging
import asyncio
import akshare as ak
import pandas as pd
from datetime import date, datetime
from typing import Dict, Any, List, Optional

from .base import BaseDataSource


logger = logging.getLogger(__name__)


class AkshareAdapter(BaseDataSource):
    """Akshare 数据源适配器，作为 Tushare 的备用数据源"""
    
    def __init__(self):
        """初始化 Akshare（无需 token）"""
        super().__init__(name="akshare")
        
        try:
            # Akshare 是同步库，初始化时直接调用（在事件循环外）
            test_df = ak.fund_name_em()
            if test_df is not None and not test_df.empty:
                self.is_available = True
                logger.info("Akshare 数据源初始化成功")
            else:
                self.is_available = False
                logger.warning("Akshare 数据源初始化失败：无法获取数据")
        except Exception as e:
            logger.error(f"Akshare 数据源初始化失败: {e}")
            self.is_available = False
    
    def _ensure_available(self) -> None:
        """确保数据源可用"""
        if not self.is_available:
            raise RuntimeError("Akshare 数据源不可用，请检查网络连接")
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """将日期字符串解析为 date 对象"""
        if not date_str or pd.isna(date_str):
            return None
        try:
            # 尝试多种日期格式
            date_str = str(date_str).strip()
            for fmt in ["%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"]:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            return None
        except Exception:
            return None
    
    def _format_date_str(self, d: date) -> str:
        """将日期格式化为字符串 (YYYY-MM-DD)"""
        return d.strftime("%Y-%m-%d")
    
    def _safe_float(self, value) -> Optional[float]:
        """安全转换为浮点数"""
        if value is None or pd.isna(value):
            return None
        try:
            # 处理百分比字符串
            if isinstance(value, str):
                value = value.replace("%", "").strip()
            return float(value)
        except (ValueError, TypeError):
            return None
    
    async def get_fund_info(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """
        获取基金基础信息
        
        Args:
            fund_code: 基金代码
            
        Returns:
            包含基金基础信息的字典
        """
        self._ensure_available()
        
        try:
            # 使用 to_thread 包装同步的 Akshare 调用
            fund_name_df = await asyncio.to_thread(ak.fund_name_em)
            
            # 筛选指定基金
            fund_row = fund_name_df[fund_name_df["基金代码"] == fund_code]
            
            if fund_row.empty:
                logger.warning(f"未找到基金 {fund_code} 的基本信息")
                return None
            
            basic_info = fund_row.iloc[0]
            fund_name = basic_info.get("基金简称", "")
            fund_type = basic_info.get("基金类型", "")
            
            # 尝试从雪球获取更详细的信息
            detailed_info = {}
            try:
                xq_df = await asyncio.to_thread(ak.fund_individual_basic_info_xq, symbol=fund_code)
                if xq_df is not None and not xq_df.empty:
                    # 将 DataFrame 转换为字典
                    info_dict = dict(zip(xq_df["item"], xq_df["value"]))
                    
                    detailed_info = {
                        "fund_manager": info_dict.get("基金经理", ""),
                        "management_company": info_dict.get("基金公司", ""),
                        "custody_bank": info_dict.get("托管银行", ""),
                    }
                    
                    # 解析成立时间
                    establish_date_str = info_dict.get("成立时间", "")
                    if establish_date_str:
                        detailed_info["establish_date"] = self._parse_date(establish_date_str)
                    
                    # 解析规模
                    scale_str = info_dict.get("最新规模", "")
                    if scale_str:
                        # 处理类似 "27.30亿" 的格式
                        scale_str = str(scale_str).replace("亿", "").strip()
                        detailed_info["scale"] = self._safe_float(scale_str)
            except Exception as e:
                logger.debug(f"从雪球获取基金详细信息失败: {e}")
            
            return {
                "fund_code": fund_code,
                "fund_name": fund_name,
                "fund_type": fund_type,
                "fund_manager": detailed_info.get("fund_manager"),
                "management_company": detailed_info.get("management_company"),
                "custody_bank": detailed_info.get("custody_bank"),
                "establish_date": detailed_info.get("establish_date"),
                "scale": detailed_info.get("scale"),
            }
            
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 信息失败: {e}")
            return None
    
    async def search_funds(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        搜索基金
        
        Args:
            keyword: 搜索关键词（基金名称或代码）
            limit: 返回结果数量限制
            
        Returns:
            匹配的基金列表
        """
        self._ensure_available()
        
        try:
            # 使用 to_thread 包装同步调用
            fund_name_df = await asyncio.to_thread(ak.fund_name_em)
            
            if fund_name_df.empty:
                return []
            
            # 根据关键词筛选
            keyword_lower = keyword.lower()
            mask = (
                fund_name_df["基金简称"].str.lower().str.contains(keyword_lower, na=False) |
                fund_name_df["基金代码"].str.contains(keyword, na=False)
            )
            filtered_df = fund_name_df[mask].head(limit)
            
            results = []
            for _, row in filtered_df.iterrows():
                results.append({
                    "fund_code": row["基金代码"],
                    "fund_name": row["基金简称"],
                    "fund_type": row.get("基金类型", ""),
                })
            
            logger.info(f"搜索关键词 '{keyword}' 找到 {len(results)} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"搜索基金失败: {e}")
            return []
    
    async def get_nav_history(
        self,
        fund_code: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        获取净值历史数据
        
        Args:
            fund_code: 基金代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            净值历史数据列表
        """
        self._ensure_available()
        
        try:
            # 使用 to_thread 包装同步调用
            nav_df = await asyncio.to_thread(ak.fund_open_fund_info_em, symbol=fund_code, indicator="单位净值走势")
            
            if nav_df.empty:
                logger.warning(f"未找到基金 {fund_code} 的净值数据")
                return []
            
            # 重命名列
            nav_df.columns = ["净值日期", "单位净值", "日增长率"]
            
            results = []
            for _, row in nav_df.iterrows():
                try:
                    trade_date = self._parse_date(row["净值日期"])
                    
                    # 过滤日期范围
                    if trade_date is None:
                        continue
                    if trade_date < start_date or trade_date > end_date:
                        continue
                    
                    results.append({
                        "fund_code": fund_code,
                        "trade_date": trade_date,
                        "nav": self._safe_float(row["单位净值"]),
                        "nav_acc": None,  # 需要单独获取累计净值
                        "daily_return": self._safe_float(row["日增长率"]),
                    })
                except Exception as e:
                    logger.debug(f"解析净值记录失败: {e}")
                    continue
            
            # 尝试获取累计净值
            try:
                acc_nav_df = await asyncio.to_thread(ak.fund_open_fund_info_em, symbol=fund_code, indicator="累计净值走势")
                if not acc_nav_df.empty:
                    acc_nav_df.columns = ["净值日期", "累计净值"]
                    
                    # 创建日期到累计净值的映射
                    acc_nav_map = {}
                    for _, row in acc_nav_df.iterrows():
                        acc_date = self._parse_date(row["净值日期"])
                        if acc_date:
                            acc_nav_map[acc_date] = self._safe_float(row["累计净值"])
                    
                    # 更新累计净值
                    for item in results:
                        if item["trade_date"] in acc_nav_map:
                            item["nav_acc"] = acc_nav_map[item["trade_date"]]
            except Exception as e:
                logger.debug(f"获取累计净值失败: {e}")
            
            # 按日期排序（升序）
            results.sort(key=lambda x: x["trade_date"] if x["trade_date"] else date.min)
            
            logger.info(f"获取基金 {fund_code} 净值历史数据 {len(results)} 条")
            return results
            
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 净值历史失败: {e}")
            return []
    
    async def get_holdings(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """
        获取持仓信息
        
        Args:
            fund_code: 基金代码
            
        Returns:
            持仓信息字典
        """
        self._ensure_available()
        
        try:
            # 获取当前年份
            current_year = date.today().year
            
            # 尝试获取最近几年的持仓数据
            stock_holdings = []
            bond_holdings = []
            report_date = None
            
            for year in range(current_year, current_year - 3, -1):
                try:
                    # 使用 to_thread 包装同步调用
                    stock_df = await asyncio.to_thread(ak.fund_portfolio_hold_em, symbol=fund_code, year=str(year))
                    
                    if stock_df is not None and not stock_df.empty:
                        for _, row in stock_df.iterrows():
                            stock_holdings.append({
                                "stock_code": str(row.get("股票代码", "")),
                                "stock_name": str(row.get("股票名称", "")),
                                "shares": self._safe_float(row.get("持仓股数")),
                                "market_value": self._safe_float(row.get("持仓市值")),
                                "proportion": self._safe_float(row.get("占净值比例")),
                            })
                        
                        # 记录报告日期
                        if report_date is None and not stock_holdings:
                            # 尝试从数据中获取报告日期
                            pass
                        
                        if stock_holdings:
                            break
                except Exception as e:
                    logger.debug(f"获取 {year} 年股票持仓失败: {e}")
            
            # 尝试获取债券持仓
            try:
                bond_df = await asyncio.to_thread(ak.fund_portfolio_bond_hold_em, symbol=fund_code, year=str(current_year))
                
                if bond_df is not None and not bond_df.empty:
                    for _, row in bond_df.iterrows():
                        bond_holdings.append({
                            "bond_code": str(row.get("债券代码", "")),
                            "bond_name": str(row.get("债券名称", "")),
                            "amount": self._safe_float(row.get("持仓数量")),
                            "market_value": self._safe_float(row.get("持仓市值")),
                            "proportion": self._safe_float(row.get("占净值比例")),
                        })
            except Exception as e:
                logger.debug(f"获取债券持仓失败: {e}")
            
            if not stock_holdings and not bond_holdings:
                return None
            
            return {
                "fund_code": fund_code,
                "report_date": report_date,
                "stock_holdings": stock_holdings,
                "bond_holdings": bond_holdings,
            }
            
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 持仓信息失败: {e}")
            return None
    
    async def get_fund_manager(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """
        获取基金经理信息
        
        Args:
            fund_code: 基金代码
            
        Returns:
            基金经理信息字典
        """
        self._ensure_available()
        
        try:
            # 使用 to_thread 包装同步调用
            xq_df = await asyncio.to_thread(ak.fund_individual_basic_info_xq, symbol=fund_code)
            
            if xq_df is None or xq_df.empty:
                return None
            
            info_dict = dict(zip(xq_df["item"], xq_df["value"]))
            
            manager_name = info_dict.get("基金经理", "")
            if not manager_name:
                return None
            
            return {
                "fund_code": fund_code,
                "manager_name": manager_name,
                "management_company": info_dict.get("基金公司", ""),
                "custody_bank": info_dict.get("托管银行", ""),
                "fund_type": info_dict.get("基金类型", ""),
            }
            
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 基金经理信息失败: {e}")
            return None
    
    async def get_fund_fees(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """
        获取费率信息
        
        Args:
            fund_code: 基金代码
            
        Returns:
            费率信息字典
        """
        self._ensure_available()
        
        try:
            # 使用 to_thread 包装同步调用
            fee_df = await asyncio.to_thread(ak.fund_fee_em, symbol=fund_code)
            
            if fee_df is None or fee_df.empty:
                logger.warning(f"未找到基金 {fund_code} 的费率信息")
                return None
            
            # 解析费率数据
            result = {
                "fund_code": fund_code,
                "management_fee": None,
                "custody_fee": None,
                "purchase_fee": None,
                "redemption_fee": None,
                "service_fee": None,
            }
            
            # 尝试从 DataFrame 中提取费率
            if isinstance(fee_df, pd.DataFrame):
                # 检查是否是键值对格式
                if "item" in fee_df.columns and "value" in fee_df.columns:
                    fee_dict = dict(zip(fee_df["item"], fee_df["value"]))
                    result["management_fee"] = self._safe_float(fee_dict.get("管理费率"))
                    result["custody_fee"] = self._safe_float(fee_dict.get("托管费率"))
                    result["service_fee"] = self._safe_float(fee_dict.get("销售服务费率"))
                else:
                    # 尝试从列名中提取
                    for col in fee_df.columns:
                        col_lower = col.lower()
                        if "管理费" in col or "management" in col_lower:
                            result["management_fee"] = self._safe_float(fee_df[col].iloc[0])
                        elif "托管费" in col or "custody" in col_lower:
                            result["custody_fee"] = self._safe_float(fee_df[col].iloc[0])
                        elif "申购费" in col or "purchase" in col_lower:
                            result["purchase_fee"] = self._safe_float(fee_df[col].iloc[0])
                        elif "赎回费" in col or "redemption" in col_lower:
                            result["redemption_fee"] = self._safe_float(fee_df[col].iloc[0])
                        elif "服务费" in col or "service" in col_lower:
                            result["service_fee"] = self._safe_float(fee_df[col].iloc[0])
            
            # 获取基金名称
            try:
                fund_info = await self.get_fund_info(fund_code)
                if fund_info:
                    result["fund_name"] = fund_info.get("fund_name", "")
            except Exception:
                pass
            
            return result
            
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 费率信息失败: {e}")
            return None
    
    async def check_health(self) -> bool:
        """
        检查数据源健康状态
        
        Returns:
            True 表示健康，False 表示不健康
        """
        if not self.is_available:
            return False
        
        try:
            # 使用 to_thread 包装同步调用
            test_df = await asyncio.to_thread(ak.fund_name_em)
            
            if test_df is not None and not test_df.empty:
                self.is_available = True
                logger.info("Akshare 数据源健康检查通过")
                return True
            else:
                self.is_available = False
                logger.warning("Akshare 数据源健康检查失败：返回数据为空")
                return False
            
        except Exception as e:
            logger.error(f"Akshare 数据源健康检查失败: {e}")
            self.is_available = False
            return False
