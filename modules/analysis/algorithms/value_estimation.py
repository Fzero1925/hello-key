"""
价值评估算法

专门负责商业价值评估，包括多种收益模型和风险评估
"""

import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum


class RevenueModel(Enum):
    """收益模型类型"""
    ADSENSE = "adsense"
    AMAZON = "amazon"
    AFFILIATE = "affiliate"
    DIRECT_SALES = "direct_sales"
    LEAD_GENERATION = "lead_generation"


@dataclass
class ValueConfig:
    """价值评估配置"""
    # AdSense参数
    adsense_ctr: float = 0.25
    adsense_click_share: float = 0.35
    adsense_rpm: float = 10.0

    # Amazon联盟参数
    amazon_ctr: float = 0.12
    amazon_conversion_rate: float = 0.04
    amazon_aov: float = 80.0
    amazon_commission: float = 0.03

    # 联盟营销参数
    affiliate_ctr: float = 0.08
    affiliate_conversion_rate: float = 0.02
    affiliate_commission_rate: float = 0.05
    affiliate_avg_sale: float = 150.0

    # 潜在客户生成参数
    lead_ctr: float = 0.15
    lead_conversion_rate: float = 0.05
    lead_value: float = 25.0

    # 风险调整参数
    market_volatility: float = 0.2
    competition_factor: float = 0.3
    seasonality_factor: float = 0.15


@dataclass
class ValueEstimate:
    """价值评估结果"""
    revenue_model: str
    monthly_estimate: float
    annual_estimate: float
    confidence_level: float
    risk_factors: List[str]
    assumptions: Dict[str, Any]
    range_low: float
    range_high: float


class ValueEstimator:
    """
    价值评估引擎

    提供多种收益模型的商业价值评估
    """

    def __init__(self, config: Optional[ValueConfig] = None):
        """
        初始化价值评估器

        Args:
            config: 价值评估配置
        """
        self.config = config or ValueConfig()
        self.logger = logging.getLogger(__name__)

    def estimate_adsense_value(
        self,
        search_volume: int,
        niche_factor: float = 1.0,
        content_quality: float = 1.0
    ) -> ValueEstimate:
        """
        估算AdSense收益价值

        Args:
            search_volume: 月搜索量
            niche_factor: 利基市场因子 (0.5-2.0)
            content_quality: 内容质量因子 (0.5-2.0)

        Returns:
            价值评估结果
        """
        try:
            # 计算预估页面访问量
            page_views = search_volume * self.config.adsense_ctr * self.config.adsense_click_share

            # 调整RPM基于利基和质量
            adjusted_rpm = self.config.adsense_rpm * niche_factor * content_quality

            # 计算月收益
            monthly_revenue = (page_views / 1000.0) * adjusted_rpm

            # 计算年收益
            annual_revenue = monthly_revenue * 12

            # 风险评估
            risk_factors = []
            confidence = 0.8

            if search_volume < 1000:
                risk_factors.append("搜索量较低")
                confidence *= 0.7

            if niche_factor < 0.8:
                risk_factors.append("利基市场竞争激烈")
                confidence *= 0.8

            # 计算范围
            variance = monthly_revenue * self.config.market_volatility
            range_low = max(0, monthly_revenue - variance)
            range_high = monthly_revenue + variance

            return ValueEstimate(
                revenue_model=RevenueModel.ADSENSE.value,
                monthly_estimate=round(monthly_revenue, 2),
                annual_estimate=round(annual_revenue, 2),
                confidence_level=round(confidence, 2),
                risk_factors=risk_factors,
                assumptions={
                    "search_volume": search_volume,
                    "ctr": self.config.adsense_ctr,
                    "click_share": self.config.adsense_click_share,
                    "rpm": adjusted_rpm,
                    "niche_factor": niche_factor,
                    "content_quality": content_quality
                },
                range_low=round(range_low, 2),
                range_high=round(range_high, 2)
            )

        except Exception as e:
            self.logger.error(f"AdSense价值评估失败: {e}")
            return self._create_error_estimate(RevenueModel.ADSENSE.value, str(e))

    def estimate_amazon_value(
        self,
        search_volume: int,
        product_category: str = "general",
        competition_level: float = 0.5
    ) -> ValueEstimate:
        """
        估算Amazon联盟收益价值

        Args:
            search_volume: 月搜索量
            product_category: 产品类别
            competition_level: 竞争水平 (0-1)

        Returns:
            价值评估结果
        """
        try:
            # 根据产品类别调整参数
            category_multipliers = {
                "electronics": {"aov": 1.5, "commission": 1.0, "cr": 1.2},
                "home_garden": {"aov": 1.2, "commission": 1.1, "cr": 1.0},
                "books": {"aov": 0.4, "commission": 0.8, "cr": 0.8},
                "general": {"aov": 1.0, "commission": 1.0, "cr": 1.0}
            }

            multiplier = category_multipliers.get(product_category, category_multipliers["general"])

            # 调整参数
            adjusted_aov = self.config.amazon_aov * multiplier["aov"]
            adjusted_commission = self.config.amazon_commission * multiplier["commission"]
            adjusted_cr = self.config.amazon_conversion_rate * multiplier["cr"]

            # 竞争调整
            competition_penalty = 1.0 - (competition_level * self.config.competition_factor)

            # 计算访问Amazon的流量
            amazon_traffic = search_volume * self.config.amazon_ctr * competition_penalty

            # 计算月收益
            monthly_revenue = amazon_traffic * adjusted_cr * adjusted_aov * adjusted_commission

            # 计算年收益
            annual_revenue = monthly_revenue * 12

            # 风险评估
            risk_factors = []
            confidence = 0.75

            if competition_level > 0.7:
                risk_factors.append("高度竞争市场")
                confidence *= 0.7

            if search_volume < 5000:
                risk_factors.append("搜索量可能不足")
                confidence *= 0.8

            if product_category == "books":
                risk_factors.append("低佣金产品类别")
                confidence *= 0.9

            # 计算范围
            variance = monthly_revenue * (self.config.market_volatility + competition_level * 0.1)
            range_low = max(0, monthly_revenue - variance)
            range_high = monthly_revenue + variance

            return ValueEstimate(
                revenue_model=RevenueModel.AMAZON.value,
                monthly_estimate=round(monthly_revenue, 2),
                annual_estimate=round(annual_revenue, 2),
                confidence_level=round(confidence, 2),
                risk_factors=risk_factors,
                assumptions={
                    "search_volume": search_volume,
                    "amazon_ctr": self.config.amazon_ctr,
                    "conversion_rate": adjusted_cr,
                    "aov": adjusted_aov,
                    "commission": adjusted_commission,
                    "category": product_category,
                    "competition_level": competition_level
                },
                range_low=round(range_low, 2),
                range_high=round(range_high, 2)
            )

        except Exception as e:
            self.logger.error(f"Amazon价值评估失败: {e}")
            return self._create_error_estimate(RevenueModel.AMAZON.value, str(e))

    def estimate_lead_generation_value(
        self,
        search_volume: int,
        industry: str = "general",
        service_complexity: float = 1.0
    ) -> ValueEstimate:
        """
        估算潜在客户生成收益

        Args:
            search_volume: 月搜索量
            industry: 行业类型
            service_complexity: 服务复杂度 (0.5-3.0)

        Returns:
            价值评估结果
        """
        try:
            # 行业调整因子
            industry_factors = {
                "legal": {"lead_value": 250, "ctr": 0.20, "cr": 0.08},
                "finance": {"lead_value": 150, "ctr": 0.18, "cr": 0.06},
                "healthcare": {"lead_value": 100, "ctr": 0.15, "cr": 0.05},
                "technology": {"lead_value": 75, "ctr": 0.12, "cr": 0.04},
                "general": {"lead_value": 25, "ctr": 0.15, "cr": 0.05}
            }

            factor = industry_factors.get(industry, industry_factors["general"])

            # 调整参数
            adjusted_lead_value = factor["lead_value"] * service_complexity
            adjusted_ctr = factor["ctr"]
            adjusted_cr = factor["cr"]

            # 计算潜在客户数量
            leads = search_volume * adjusted_ctr * adjusted_cr

            # 计算月收益
            monthly_revenue = leads * adjusted_lead_value

            # 计算年收益
            annual_revenue = monthly_revenue * 12

            # 风险评估
            risk_factors = []
            confidence = 0.65  # 潜在客户生成的不确定性较高

            if search_volume < 2000:
                risk_factors.append("搜索量偏低")
                confidence *= 0.8

            if service_complexity > 2.0:
                risk_factors.append("服务复杂度高，转化难度大")
                confidence *= 0.7

            # 计算范围（潜在客户生成波动性较大）
            variance = monthly_revenue * 0.4
            range_low = max(0, monthly_revenue - variance)
            range_high = monthly_revenue + variance

            return ValueEstimate(
                revenue_model=RevenueModel.LEAD_GENERATION.value,
                monthly_estimate=round(monthly_revenue, 2),
                annual_estimate=round(annual_revenue, 2),
                confidence_level=round(confidence, 2),
                risk_factors=risk_factors,
                assumptions={
                    "search_volume": search_volume,
                    "lead_ctr": adjusted_ctr,
                    "conversion_rate": adjusted_cr,
                    "lead_value": adjusted_lead_value,
                    "industry": industry,
                    "service_complexity": service_complexity
                },
                range_low=round(range_low, 2),
                range_high=round(range_high, 2)
            )

        except Exception as e:
            self.logger.error(f"潜在客户生成价值评估失败: {e}")
            return self._create_error_estimate(RevenueModel.LEAD_GENERATION.value, str(e))

    def compare_models(
        self,
        search_volume: int,
        keyword_data: Dict[str, Any] = None
    ) -> List[ValueEstimate]:
        """
        比较多种收益模型

        Args:
            search_volume: 月搜索量
            keyword_data: 关键词附加数据

        Returns:
            各种收益模型的评估结果列表
        """
        keyword_data = keyword_data or {}

        estimates = []

        # AdSense评估
        adsense_estimate = self.estimate_adsense_value(
            search_volume,
            keyword_data.get('niche_factor', 1.0),
            keyword_data.get('content_quality', 1.0)
        )
        estimates.append(adsense_estimate)

        # Amazon评估
        amazon_estimate = self.estimate_amazon_value(
            search_volume,
            keyword_data.get('product_category', 'general'),
            keyword_data.get('competition_level', 0.5)
        )
        estimates.append(amazon_estimate)

        # 潜在客户生成评估
        lead_estimate = self.estimate_lead_generation_value(
            search_volume,
            keyword_data.get('industry', 'general'),
            keyword_data.get('service_complexity', 1.0)
        )
        estimates.append(lead_estimate)

        # 按月收益排序
        estimates.sort(key=lambda x: x.monthly_estimate, reverse=True)

        return estimates

    def calculate_lifetime_value(
        self,
        monthly_estimate: float,
        retention_months: int = 24,
        growth_rate: float = 0.02
    ) -> Dict[str, float]:
        """
        计算生命周期价值

        Args:
            monthly_estimate: 月收益估算
            retention_months: 保持期（月）
            growth_rate: 月增长率

        Returns:
            生命周期价值分析
        """
        total_value = 0
        current_monthly = monthly_estimate

        for month in range(retention_months):
            total_value += current_monthly
            current_monthly *= (1 + growth_rate)

        return {
            "lifetime_value": round(total_value, 2),
            "final_monthly": round(current_monthly, 2),
            "total_growth": round((current_monthly / monthly_estimate - 1) * 100, 1),
            "retention_months": retention_months
        }

    def _create_error_estimate(self, model: str, error: str) -> ValueEstimate:
        """创建错误情况下的默认估值"""
        return ValueEstimate(
            revenue_model=model,
            monthly_estimate=0,
            annual_estimate=0,
            confidence_level=0,
            risk_factors=[f"评估错误: {error}"],
            assumptions={},
            range_low=0,
            range_high=0
        )

    def export_analysis_report(
        self,
        estimates: List[ValueEstimate],
        keyword: str = ""
    ) -> Dict[str, Any]:
        """
        导出价值分析报告

        Args:
            estimates: 价值评估结果列表
            keyword: 关键词

        Returns:
            格式化的分析报告
        """
        if not estimates:
            return {"error": "无评估数据"}

        best_estimate = max(estimates, key=lambda x: x.monthly_estimate)
        total_potential = sum(est.monthly_estimate for est in estimates)

        return {
            "keyword": keyword,
            "analysis_date": "2025-01-17",
            "best_model": {
                "model": best_estimate.revenue_model,
                "monthly_revenue": best_estimate.monthly_estimate,
                "annual_revenue": best_estimate.annual_estimate,
                "confidence": best_estimate.confidence_level
            },
            "all_models": [
                {
                    "model": est.revenue_model,
                    "monthly": est.monthly_estimate,
                    "annual": est.annual_estimate,
                    "confidence": est.confidence_level,
                    "range": f"${est.range_low:.0f}-${est.range_high:.0f}",
                    "risks": est.risk_factors
                }
                for est in estimates
            ],
            "total_potential": round(total_potential, 2),
            "recommendation": self._generate_recommendation(estimates)
        }

    def _generate_recommendation(self, estimates: List[ValueEstimate]) -> str:
        """生成推荐建议"""
        if not estimates:
            return "无足够数据提供建议"

        best = max(estimates, key=lambda x: x.monthly_estimate)

        if best.monthly_estimate < 10:
            return "收益潜力较低，建议寻找更高价值的关键词"
        elif best.monthly_estimate < 50:
            return f"中等收益潜力，推荐使用{best.revenue_model}模式"
        elif best.monthly_estimate < 200:
            return f"高收益潜力，强烈推荐使用{best.revenue_model}模式开发内容"
        else:
            return f"极高收益潜力，优先级最高，使用{best.revenue_model}模式快速开发"