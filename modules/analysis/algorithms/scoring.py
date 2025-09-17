"""
评分算法引擎

提供可配置的评分算法，包括机会评分、商业价值评估等
重构自原始scoring.py，支持配置化参数
"""

import logging
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass


@dataclass
class ScoreConfig:
    """评分配置参数"""
    # 机会评分权重
    trend_weight: float = 0.35
    intent_weight: float = 0.30
    search_volume_weight: float = 0.15
    freshness_weight: float = 0.20
    difficulty_penalty: float = 0.6

    # AdSense参数
    adsense_ctr_serp: float = 0.25
    adsense_click_share_rank: float = 0.35
    adsense_rpm_usd: float = 10.0

    # Amazon联盟参数
    amazon_ctr: float = 0.12
    amazon_conversion_rate: float = 0.04
    amazon_aov_usd: float = 80.0
    amazon_commission: float = 0.03

    # 收益范围参数
    revenue_range_low_factor: float = 0.75
    revenue_range_high_factor: float = 1.25


class ScoringEngine:
    """
    评分算法引擎

    提供标准化的评分算法，支持配置化参数
    """

    def __init__(self, config: Optional[ScoreConfig] = None):
        """
        初始化评分引擎

        Args:
            config: 评分配置参数，默认使用标准配置
        """
        self.config = config or ScoreConfig()
        self.logger = logging.getLogger(__name__)

    def _clamp01(self, x: Union[int, float, str]) -> float:
        """将值限制在0-1范围内"""
        try:
            x = float(x)
        except (ValueError, TypeError):
            x = 0.0
        return max(0.0, min(1.0, x))

    def calculate_opportunity_score(
        self,
        trend: float,
        intent: float,
        search_volume: float,
        freshness: float,
        difficulty: float
    ) -> float:
        """
        计算机会评分 (0-100)

        Args:
            trend: 趋势得分 (0-1)
            intent: 商业意图得分 (0-1)
            search_volume: 搜索量得分 (0-1)
            freshness: 新鲜度得分 (0-1)
            difficulty: 竞争难度 (0-1, 越高越难)

        Returns:
            机会评分 (0-100)
        """
        # 标准化输入值
        T = self._clamp01(trend)
        I = self._clamp01(intent)
        S = self._clamp01(search_volume)
        F = self._clamp01(freshness)
        D = self._clamp01(difficulty)

        # 加权计算基础分数
        base_score = (
            self.config.trend_weight * T +
            self.config.intent_weight * I +
            self.config.search_volume_weight * S +
            self.config.freshness_weight * F
        )

        # 应用竞争难度惩罚
        final_score = 100.0 * base_score * (1.0 - self.config.difficulty_penalty * D)

        # 限制在0-100范围内
        final_score = max(0.0, min(100.0, final_score))

        return round(final_score, 2)

    def estimate_adsense_revenue(self, search_volume: int) -> float:
        """
        估算AdSense收益

        Args:
            search_volume: 月搜索量

        Returns:
            预估月收益 (USD)
        """
        try:
            sv = max(0.0, float(search_volume))
        except (ValueError, TypeError):
            sv = 0.0

        # 计算预估页面浏览量
        page_views = sv * self.config.adsense_ctr_serp * self.config.adsense_click_share_rank

        # 计算收益
        revenue = (page_views / 1000.0) * self.config.adsense_rpm_usd

        return round(revenue, 2)

    def estimate_amazon_revenue(self, search_volume: int) -> float:
        """
        估算Amazon联盟收益

        Args:
            search_volume: 月搜索量

        Returns:
            预估月收益 (USD)
        """
        try:
            sv = max(0.0, float(search_volume))
        except (ValueError, TypeError):
            sv = 0.0

        # 计算导向Amazon的流量
        amazon_traffic = sv * self.config.amazon_ctr

        # 计算收益
        revenue = (
            amazon_traffic *
            self.config.amazon_conversion_rate *
            self.config.amazon_aov_usd *
            self.config.amazon_commission
        )

        return round(revenue, 2)

    def estimate_total_value(
        self,
        search_volume: int,
        opportunity_score: float,
        mode: str = 'max'
    ) -> float:
        """
        估算总体商业价值

        Args:
            search_volume: 月搜索量
            opportunity_score: 机会评分 (0-100)
            mode: 计算模式 ('max' 或 'sum')

        Returns:
            预估月收益 (USD)
        """
        adsense_revenue = self.estimate_adsense_revenue(search_volume)
        amazon_revenue = self.estimate_amazon_revenue(search_volume)

        # 根据模式选择基础收益
        if mode == 'max':
            base_revenue = max(adsense_revenue, amazon_revenue)
        else:  # sum
            base_revenue = adsense_revenue + amazon_revenue

        # 应用稳定性因子（基于机会评分）
        opp_score = max(0.0, min(100.0, float(opportunity_score)))
        stability_factor = 0.6 + 0.4 * (opp_score / 100.0)

        final_value = base_revenue * stability_factor

        return round(final_value, 2)

    def generate_revenue_range(self, point_estimate: float) -> Dict[str, Any]:
        """
        生成收益范围估算

        Args:
            point_estimate: 点估计值

        Returns:
            包含点估计和范围的字典
        """
        try:
            value = float(point_estimate)
        except (ValueError, TypeError):
            value = 0.0

        low = max(0.0, value * self.config.revenue_range_low_factor)
        high = value * self.config.revenue_range_high_factor

        return {
            "point": round(value, 2),
            "range": f"${low:.0f}–${high:.0f}/mo",
            "low": round(low, 2),
            "high": round(high, 2)
        }

    def explain_scoring(
        self,
        trend_pct: float,
        intent_hits: list,
        difficulty_label: str
    ) -> Dict[str, str]:
        """
        生成评分解释

        Args:
            trend_pct: 趋势百分比
            intent_hits: 意图关键词命中列表
            difficulty_label: 竞争难度标签

        Returns:
            评分解释字典
        """
        return {
            "trend": f"最近30%均值 {trend_pct:+.0f}% vs 整体",
            "intent": f"意图命中: {', '.join(intent_hits) if intent_hits else 'N/A'}",
            "difficulty": difficulty_label or "未知"
        }

    def batch_score_keywords(
        self,
        keywords_data: list,
        metric_keys: Dict[str, str] = None
    ) -> list:
        """
        批量计算关键词评分

        Args:
            keywords_data: 关键词数据列表
            metric_keys: 指标字段名映射

        Returns:
            包含评分的关键词数据列表
        """
        if not metric_keys:
            metric_keys = {
                'trend': 'trend_score',
                'intent': 'intent_score',
                'search_volume': 'search_volume_score',
                'freshness': 'freshness_score',
                'difficulty': 'difficulty_score'
            }

        scored_keywords = []

        for kw_data in keywords_data:
            try:
                # 提取评分指标
                trend = kw_data.get(metric_keys['trend'], 0)
                intent = kw_data.get(metric_keys['intent'], 0)
                search_vol = kw_data.get(metric_keys['search_volume'], 0)
                freshness = kw_data.get(metric_keys['freshness'], 0)
                difficulty = kw_data.get(metric_keys['difficulty'], 0)

                # 计算机会评分
                opportunity_score = self.calculate_opportunity_score(
                    trend, intent, search_vol, freshness, difficulty
                )

                # 估算商业价值
                search_volume = kw_data.get('search_volume', 0)
                estimated_value = self.estimate_total_value(search_volume, opportunity_score)
                revenue_range = self.generate_revenue_range(estimated_value)

                # 添加评分结果
                result = kw_data.copy()
                result.update({
                    'opportunity_score': opportunity_score,
                    'estimated_value': estimated_value,
                    'revenue_range': revenue_range,
                    'adsense_revenue': self.estimate_adsense_revenue(search_volume),
                    'amazon_revenue': self.estimate_amazon_revenue(search_volume)
                })

                scored_keywords.append(result)

            except Exception as e:
                self.logger.error(f"评分计算失败: {kw_data.get('keyword', 'unknown')}: {e}")
                # 保留原数据，添加默认评分
                result = kw_data.copy()
                result.update({
                    'opportunity_score': 0,
                    'estimated_value': 0,
                    'revenue_range': {"point": 0, "range": "$0–$0/mo"},
                    'scoring_error': str(e)
                })
                scored_keywords.append(result)

        return scored_keywords


# 向后兼容性: 提供函数式接口
def opportunity_score(T, I, S, F, D, d_penalty=0.6):
    """向后兼容的机会评分函数"""
    config = ScoreConfig(difficulty_penalty=d_penalty)
    engine = ScoringEngine(config)
    return engine.calculate_opportunity_score(T, I, S, F, D)


def estimate_adsense(search_volume, ctr_serp=0.25, click_share_rank=0.35, rpm_usd=10.0):
    """向后兼容的AdSense收益估算函数"""
    config = ScoreConfig(
        adsense_ctr_serp=ctr_serp,
        adsense_click_share_rank=click_share_rank,
        adsense_rpm_usd=rpm_usd
    )
    engine = ScoringEngine(config)
    return engine.estimate_adsense_revenue(search_volume)


def estimate_amazon(search_volume, ctr_to_amazon=0.12, cr=0.04, aov_usd=80.0, commission=0.03):
    """向后兼容的Amazon收益估算函数"""
    config = ScoreConfig(
        amazon_ctr=ctr_to_amazon,
        amazon_conversion_rate=cr,
        amazon_aov_usd=aov_usd,
        amazon_commission=commission
    )
    engine = ScoringEngine(config)
    return engine.estimate_amazon_revenue(search_volume)


def estimate_value(search_volume, opp_score, ads_params=None, aff_params=None, mode='max'):
    """向后兼容的价值估算函数"""
    ads_params = ads_params or {}
    aff_params = aff_params or {}

    config = ScoreConfig(
        adsense_ctr_serp=ads_params.get('ctr_serp', 0.25),
        adsense_click_share_rank=ads_params.get('click_share_rank', 0.35),
        adsense_rpm_usd=ads_params.get('rpm_usd', 10.0),
        amazon_ctr=aff_params.get('ctr_to_amazon', 0.12),
        amazon_conversion_rate=aff_params.get('cr', 0.04),
        amazon_aov_usd=aff_params.get('aov_usd', 80.0),
        amazon_commission=aff_params.get('commission', 0.03)
    )

    engine = ScoringEngine(config)
    return engine.estimate_total_value(search_volume, opp_score, mode)


def explain_selection(trend_pct, intent_hits, difficulty_label):
    """向后兼容的评分解释函数"""
    engine = ScoringEngine()
    return engine.explain_scoring(trend_pct, intent_hits, difficulty_label)


def make_revenue_range(point_estimate):
    """向后兼容的收益范围函数"""
    engine = ScoringEngine()
    return engine.generate_revenue_range(point_estimate)