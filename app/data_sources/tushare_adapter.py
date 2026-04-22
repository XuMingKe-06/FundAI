"""
Tushare Pro API 数据源适配器
"""
import logging
import tushare as ts
from datetime import date, datetime
from typing import Dict, Any, List, Optional

from .base import BaseDataSource
from app.core.config import settings


logger = logging.getLogger(__name__)


class TushareAdapter(BaseDataSource):
    """Tushare Pro API 数据源适配器"""
    
    def __init__(self):
        """初始化 Tushare API 客户端"""
        super().__init__(name="tushare")
        
        self._token = settings.TUSHARE_TOKEN
        self._pro = None
        
        if self._token:
            try:
                ts.set_token(self._token)
                self._pro = ts.pro_api()
                
                # 验证是否有权限访问 fund_basic 接口
                try:
                    test_df = self._pro.fund_basic(market='O', limit=1)
                    if test_df is not None and not test_df.empty:
                        self.is_available = True
                        logger.info("Tushare API 客户端初始化成功，fund_basic 接口可用")
                    else:
                        self.is_available = False
                        logger.warning("Tushare fund_basic 接口返回空数据，可能是权限不足")
                except Exception as api_err:
                    # 权限不足或其他 API 错误
                    self.is_available = False
                    logger.warning(f"Tushare fund_basic 接口不可用: {api_err}，将使用备用数据源")
                    
            except Exception as e:
                logger.error(f"Tushare API 客户端初始化失败: {e}")
                self.is_available = False
        else:
            logger.warning("未配置 TUSHARE_TOKEN，Tushare 数据源不可用")
            self.is_available = False
    
    def _ensure_available(self) -> None:
        """确保数据源可用"""
        if not self.is_available or not self._pro:
            raise RuntimeError("Tushare 数据源不可用，请检查 TUSHARE_TOKEN 配置")
    
    def _format_date(self, d: date) -> str:
        """将日期格式化为 Tushare API 所需的格式 (YYYYMMDD)"""
        return d.strftime("%Y%m%d")
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """将 Tushare 返回的日期字符串解析为 date 对象"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y%m%d").date()
        except ValueError:
            return None
    
    async def get_fund_info(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """
        获取基金基础信息
        
        Args:
            fund_code: 基金代码
            
        Returns:
            包含基金基础信息的字典，包括：
            - fund_code: 基金代码
            - fund_name: 基金名称
            - fund_type: 基金类型
            - fund_manager: 基金经理
            - establish_date: 成立日期
            - scale: 基金规模（亿元）
            - management_fee: 管理费率
            - custody_fee: 托管费率
        """
        self._ensure_available()
        
        try:
            # 获取基金基本信息
            df = self._pro.fund_basic(ts_code=fund_code, fields=[
                'ts_code', 'name', 'fund_type', 'manager', 'found_date',
                'm_fee', 'c_fee', 'issue_amount', 'invest_type'
            ])
            
            if df.empty:
                logger.warning(f"未找到基金 {fund_code} 的信息")
                return None
            
            row = df.iloc[0]
            
            # 获取基金规模（需要从其他接口获取最新规模）
            scale = None
            try:
                scale_df = self._pro.fund_share(ts_code=fund_code)
                if not scale_df.empty:
                    # 取最新份额并估算规模
                    latest_share = scale_df.iloc[0]['total_share']
                    if latest_share:
                        scale = float(latest_share) / 100000000  # 转换为亿元
            except Exception as e:
                logger.debug(f"获取基金规模失败: {e}")
            
            return {
                'fund_code': row['ts_code'],
                'fund_name': row['name'],
                'fund_type': row['fund_type'],
                'fund_manager': row['manager'],
                'establish_date': self._parse_date(row['found_date']),
                'scale': scale,
                'management_fee': float(row['m_fee']) if row['m_fee'] else None,
                'custody_fee': float(row['c_fee']) if row['c_fee'] else None,
                'invest_type': row['invest_type'],
                'issue_amount': float(row['issue_amount']) if row['issue_amount'] else None
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
            # 获取所有基金基本信息
            df = self._pro.fund_basic(market='E', fields=[
                'ts_code', 'name', 'fund_type', 'manager', 'found_date', 'status'
            ])
            
            if df.empty:
                return []
            
            # 根据关键词筛选
            keyword_lower = keyword.lower()
            mask = (
                df['name'].str.lower().str.contains(keyword_lower, na=False) |
                df['ts_code'].str.contains(keyword, na=False)
            )
            filtered_df = df[mask].head(limit)
            
            results = []
            for _, row in filtered_df.iterrows():
                results.append({
                    'fund_code': row['ts_code'],
                    'fund_name': row['name'],
                    'fund_type': row['fund_type'],
                    'fund_manager': row['manager'],
                    'establish_date': self._parse_date(row['found_date']),
                    'status': row['status']
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
            净值历史数据列表，每条记录包含：
            - trade_date: 交易日期
            - nav: 单位净值
            - nav_acc: 累计净值
            - daily_return: 日涨跌幅
        """
        self._ensure_available()
        
        try:
            df = self._pro.fund_nav(
                ts_code=fund_code,
                start_date=self._format_date(start_date),
                end_date=self._format_date(end_date),
                fields=['ts_code', 'nav_date', 'nav', 'nav_acc', 'daily_return']
            )
            
            if df.empty:
                logger.warning(f"未找到基金 {fund_code} 在指定时间段的净值数据")
                return []
            
            results = []
            for _, row in df.iterrows():
                results.append({
                    'fund_code': row['ts_code'],
                    'trade_date': self._parse_date(row['nav_date']),
                    'nav': float(row['nav']) if row['nav'] else None,
                    'nav_acc': float(row['nav_acc']) if row['nav_acc'] else None,
                    'daily_return': float(row['daily_return']) if row['daily_return'] else None
                })
            
            # 按日期排序（升序）
            results.sort(key=lambda x: x['trade_date'] if x['trade_date'] else date.min)
            
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
            持仓信息字典，包含：
            - report_date: 报告日期
            - stock_holdings: 股票持仓列表
            - bond_holdings: 债券持仓列表
        """
        self._ensure_available()
        
        try:
            # 获取股票持仓
            stock_holdings = []
            try:
                stock_df = self._pro.fund_portfolio(ts_code=fund_code, fields=[
                    'ts_code', 'ann_date', 'end_date', 'symbol', 'name',
                    'amount', 'mkv', 'proportion'
                ])
                
                if not stock_df.empty:
                    # 取最新一期报告
                    latest_date = stock_df['end_date'].max()
                    latest_holdings = stock_df[stock_df['end_date'] == latest_date]
                    
                    for _, row in latest_holdings.iterrows():
                        stock_holdings.append({
                            'stock_code': row['symbol'],
                            'stock_name': row['name'],
                            'shares': float(row['amount']) if row['amount'] else None,
                            'market_value': float(row['mkv']) if row['mkv'] else None,
                            'proportion': float(row['proportion']) if row['proportion'] else None
                        })
            except Exception as e:
                logger.debug(f"获取股票持仓失败: {e}")
            
            # 获取债券持仓
            bond_holdings = []
            try:
                bond_df = self._pro.fund_portfolio(ts_code=fund_code, asset_type='b', fields=[
                    'ts_code', 'ann_date', 'end_date', 'symbol', 'name',
                    'amount', 'mkv', 'proportion'
                ])
                
                if not bond_df.empty:
                    latest_date = bond_df['end_date'].max()
                    latest_holdings = bond_df[bond_df['end_date'] == latest_date]
                    
                    for _, row in latest_holdings.iterrows():
                        bond_holdings.append({
                            'bond_code': row['symbol'],
                            'bond_name': row['name'],
                            'amount': float(row['amount']) if row['amount'] else None,
                            'market_value': float(row['mkv']) if row['mkv'] else None,
                            'proportion': float(row['proportion']) if row['proportion'] else None
                        })
            except Exception as e:
                logger.debug(f"获取债券持仓失败: {e}")
            
            if not stock_holdings and not bond_holdings:
                return None
            
            return {
                'fund_code': fund_code,
                'report_date': self._parse_date(latest_date) if stock_holdings or bond_holdings else None,
                'stock_holdings': stock_holdings,
                'bond_holdings': bond_holdings
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
            基金经理信息字典，包含：
            - manager_name: 基金经理姓名
            - tenure_days: 任职天数
            - tenure_return: 任职回报
        """
        self._ensure_available()
        
        try:
            # 获取基金公司信息，包含基金经理
            df = self._pro.fund_basic(ts_code=fund_code, fields=[
                'ts_code', 'name', 'manager', 'management'
            ])
            
            if df.empty:
                return None
            
            row = df.iloc[0]
            manager_name = row['manager']
            
            if not manager_name:
                return None
            
            # 尝试获取基金经理详细信息
            manager_info = {
                'fund_code': fund_code,
                'manager_name': manager_name,
                'management_company': row['management'],
                'tenure_days': None,
                'tenure_return': None
            }
            
            # 尝试从 fund_manager 接口获取更详细信息
            try:
                mgr_df = self._pro.fund_manager(ts_code=fund_code, fields=[
                    'ts_code', 'name', 'begin_date', 'end_date', 'tenure'
                ])
                
                if not mgr_df.empty:
                    # 取当前在任的基金经理
                    current_mgr = mgr_df[mgr_df['end_date'].isna()]
                    if not current_mgr.empty:
                        mgr_row = current_mgr.iloc[0]
                        manager_info['manager_name'] = mgr_row['name']
                        
                        if mgr_row['begin_date']:
                            begin_date = self._parse_date(mgr_row['begin_date'])
                            if begin_date:
                                manager_info['tenure_days'] = (date.today() - begin_date).days
                        
                        if mgr_row['tenure']:
                            manager_info['tenure_return'] = float(mgr_row['tenure'])
            except Exception as e:
                logger.debug(f"获取基金经理详细信息失败: {e}")
            
            return manager_info
            
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 基金经理信息失败: {e}")
            return None
    
    async def get_fund_fees(self, fund_code: str) -> Optional[Dict[str, Any]]:
        """
        获取费率信息
        
        Args:
            fund_code: 基金代码
            
        Returns:
            费率信息字典，包含：
            - management_fee: 管理费率
            - custody_fee: 托管费率
            - purchase_fee: 申购费率
            - redemption_fee: 赎回费率
            - service_fee: 销售服务费率
        """
        self._ensure_available()
        
        try:
            df = self._pro.fund_basic(ts_code=fund_code, fields=[
                'ts_code', 'name', 'm_fee', 'c_fee', 'p_fee', 'r_fee', 's_fee'
            ])
            
            if df.empty:
                return None
            
            row = df.iloc[0]
            
            return {
                'fund_code': row['ts_code'],
                'fund_name': row['name'],
                'management_fee': float(row['m_fee']) if row['m_fee'] else None,
                'custody_fee': float(row['c_fee']) if row['c_fee'] else None,
                'purchase_fee': float(row['p_fee']) if row['p_fee'] else None,
                'redemption_fee': float(row['r_fee']) if row['r_fee'] else None,
                'service_fee': float(row['s_fee']) if row['s_fee'] else None
            }
            
        except Exception as e:
            logger.error(f"获取基金 {fund_code} 费率信息失败: {e}")
            return None
    
    async def check_health(self) -> bool:
        """
        检查数据源健康状态
        
        Returns:
            True 表示健康，False 表示不健康
        """
        if not self.is_available or not self._pro:
            return False
        
        try:
            # 尝试获取交易日历来验证 API 是否正常
            df = self._pro.trade_cal(
                exchange='SSE',
                start_date=self._format_date(date.today()),
                end_date=self._format_date(date.today())
            )
            
            # 如果能成功调用，则认为健康
            self.is_available = True
            logger.info("Tushare 数据源健康检查通过")
            return True
            
        except Exception as e:
            logger.error(f"Tushare 数据源健康检查失败: {e}")
            self.is_available = False
            return False
