"""
商业规则引擎

基于配置化规则评估商业价值、竞争程度和收益潜力
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from ..config.rules_config import RulesConfigManager, CommercialRulesConfig


class CompetitionLevel(Enum):
    """竞争程度等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class RevenueModel(Enum):
    """收益模型"""
    ADSENSE = "adsense"
    AFFILIATE = "affiliate"
    LEAD_GENERATION = "lead_generation"
    DIRECT_SALES = "direct_sales"


@dataclass
class CommercialAnalysisResult:
    """商业分析结果"""
    keyword_or_topic: str
    commercial_value: float
    competition_level: CompetitionLevel
    recommended_models: List[RevenueModel]
    estimated_monthly_revenue: Dict[str, float]
    risk_factors: List[str]
    opportunities: List[str]
    investment_priority: str
    metadata: Dict[str, Any]


class CommercialRuleEngine:
    """
    商业规则引擎

    评估关键词和话题的商业价值和收益潜力
    """

    def __init__(self, rules_config: Optional[CommercialRulesConfig] = None):
        """
        初始化商业规则引擎

        Args:
            rules_config: 商业规则配置
        """
        self.logger = logging.getLogger(__name__)

        if rules_config:
            self.rules = rules_config
        else:
            config_manager = RulesConfigManager()
            self.rules = config_manager.get_commercial_rules()

    def analyze_commercial_value(
        self,
        keyword_or_topic: str,
        search_volume: int = 0,
        commercial_intent: float = 0.0,
        competition_score: float = 0.0,
        trend_direction: float = 0.0,
        brand_presence: float = 0.0,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> CommercialAnalysisResult:
        """
        分析商业价值

        Args:
            keyword_or_topic: 关键词或话题
            search_volume: 搜索量
            commercial_intent: 商业意图得分 (0-1)
            competition_score: 竞争得分 (0-1)
            trend_direction: 趋势方向 (-1到1)
            brand_presence: 品牌存在感 (0-1)
            category: 分类
            metadata: 附加元数据

        Returns:
            商业分析结果
        """
        try:
            metadata = metadata or {}

            # 计算商业价值
            commercial_value = self._calculate_commercial_value(
                search_volume, commercial_intent, competition_score,
                trend_direction, brand_presence
            )

            # 确定竞争程度
            competition_level = self._determine_competition_level(competition_score)

            # 推荐收益模型
            recommended_models = self._recommend_revenue_models(
                search_volume, commercial_intent, category, competition_level
            )

            # 估算收益
            estimated_revenue = self._estimate_revenue_by_models(
                search_volume, commercial_intent, recommended_models, category
            )

            # 识别风险因素
            risk_factors = self._identify_risk_factors(
                competition_level, trend_direction, search_volume, category
            )

            # 识别机会
            opportunities = self._identify_opportunities(
                commercial_value, competition_level, trend_direction, category
            )

            # 确定投资优先级
            investment_priority = self._determine_investment_priority(
                commercial_value, competition_level, estimated_revenue
            )

            return CommercialAnalysisResult(
                keyword_or_topic=keyword_or_topic,
                commercial_value=commercial_value,
                competition_level=competition_level,
                recommended_models=recommended_models,
                estimated_monthly_revenue=estimated_revenue,
                risk_factors=risk_factors,
                opportunities=opportunities,
                investment_priority=investment_priority,
                metadata=metadata
            )

        except Exception as e:
            self.logger.error(f"商业分析失败 {keyword_or_topic}: {e}")
            return self._create_error_result(keyword_or_topic, str(e))

    def _calculate_commercial_value(
        self,
        search_volume: int,
        commercial_intent: float,
        competition_score: float,
        trend_direction: float,
        brand_presence: float
    ) -> float:
        """计算商业价值"""
        # 标准化搜索量 (对数缩放)
        import math
        normalized_volume = min(1.0, math.log10(max(1, search_volume)) / 6)  # 假设100万是满分

        # 应用权重
        weighted_value = (
            self.rules.value_weights.get('search_volume', 0.3) * normalized_volume +
            self.rules.value_weights.get('commercial_intent', 0.25) * commercial_intent +
            self.rules.value_weights.get('competition_level', -0.2) * competition_score +
            self.rules.value_weights.get('trend_direction', 0.15) * max(0, trend_direction) +
            self.rules.value_weights.get('brand_presence', 0.1) * brand_presence
        )

        # 确保在0-1范围内
        return max(0.0, min(1.0, weighted_value))

    def _determine_competition_level(self, competition_score: float) -> CompetitionLevel:
        """确定竞争程度"""
        thresholds = self.rules.competition_thresholds

        if competition_score >= thresholds.get('very_high', 0.9):
            return CompetitionLevel.VERY_HIGH
        elif competition_score >= thresholds.get('high', 0.8):
            return CompetitionLevel.HIGH
        elif competition_score >= thresholds.get('medium', 0.6):
            return CompetitionLevel.MEDIUM
        else:
            return CompetitionLevel.LOW

    def _recommend_revenue_models(
        self,
        search_volume: int,
        commercial_intent: float,
        category: str,
        competition_level: CompetitionLevel
    ) -> List[RevenueModel]:
        """推荐收益模型"""
        recommended = []

        for model_name, config in self.rules.revenue_models.items():
            if not config.get('enabled', True):
                continue

            min_traffic = config.get('min_traffic', 0)
            if search_volume < min_traffic:
                continue

            # 根据不同模型的特点进行推荐
            if model_name == 'adsense':
                if search_volume >= 1000 and commercial_intent >= 0.3:
                    recommended.append(RevenueModel.ADSENSE)

            elif model_name == 'affiliate':
                if commercial_intent >= 0.5 and competition_level != CompetitionLevel.VERY_HIGH:
                    recommended.append(RevenueModel.AFFILIATE)

            elif model_name == 'lead_generation':
                if commercial_intent >= 0.4 and category in ['technology', 'smart_home', 'security']:
                    recommended.append(RevenueModel.LEAD_GENERATION)

        # 如果没有推荐的模型，默认推荐AdSense
        if not recommended and search_volume >= 500:
            recommended.append(RevenueModel.ADSENSE)

        return recommended

    def _estimate_revenue_by_models(
        self,
        search_volume: int,
        commercial_intent: float,
        models: List[RevenueModel],
        category: str
    ) -> Dict[str, float]:
        """按模型估算收益"""
        revenue_estimates = {}

        for model in models:
            if model == RevenueModel.ADSENSE:
                revenue = self._estimate_adsense_revenue(search_volume, commercial_intent)
            elif model == RevenueModel.AFFILIATE:
                revenue = self._estimate_affiliate_revenue(search_volume, commercial_intent, category)
            elif model == RevenueModel.LEAD_GENERATION:
                revenue = self._estimate_lead_generation_revenue(search_volume, commercial_intent, category)
            else:
                revenue = 0

            revenue_estimates[model.value] = revenue

        return revenue_estimates

    def _estimate_adsense_revenue(self, search_volume: int, commercial_intent: float) -> float:
        """估算AdSense收益"""
        config = self.rules.revenue_models.get('adsense', {})
        ctr_range = config.get('ctr_range', [0.1, 0.4])
        rpm_range = config.get('rpm_range', [5, 15])

        # 根据商业意图调整CTR和RPM
        ctr = ctr_range[0] + (ctr_range[1] - ctr_range[0]) * commercial_intent
        rpm = rpm_range[0] + (rpm_range[1] - rpm_range[0]) * commercial_intent

        monthly_revenue = (search_volume * ctr * rpm) / 1000
        return round(monthly_revenue, 2)

    def _estimate_affiliate_revenue(self, search_volume: int, commercial_intent: float, category: str) -> float:
        """估算联盟营销收益"""
        config = self.rules.revenue_models.get('affiliate', {})
        conversion_range = config.get('conversion_range', [0.01, 0.05])

        # 根据分类调整转化率
        category_multipliers = {
            'smart_home': 1.2,
            'security': 1.1,
            'technology': 1.0,
            'general': 0.8
        }

        base_conversion = conversion_range[0] + (conversion_range[1] - conversion_range[0]) * commercial_intent
        conversion_rate = base_conversion * category_multipliers.get(category, 1.0)

        # 假设平均佣金和订单价值
        avg_commission = 30  # 美元
        monthly_revenue = search_volume * 0.1 * conversion_rate * avg_commission  # 假设10%的流量转化
        return round(monthly_revenue, 2)

    def _estimate_lead_generation_revenue(self, search_volume: int, commercial_intent: float, category: str) -> float:
        """估算潜在客户生成收益"""
        config = self.rules.revenue_models.get('lead_generation', {})
        conversion_range = config.get('conversion_range', [0.02, 0.10])

        # 根据分类调整潜在客户价值
        lead_values = {
            'technology': 50,
            'smart_home': 40,
            'security': 60,
            'general': 25
        }

        conversion_rate = conversion_range[0] + (conversion_range[1] - conversion_range[0]) * commercial_intent
        lead_value = lead_values.get(category, 25)

        monthly_revenue = search_volume * 0.15 * conversion_rate * lead_value  # 假设15%的流量转化
        return round(monthly_revenue, 2)

    def _identify_risk_factors(
        self,
        competition_level: CompetitionLevel,
        trend_direction: float,
        search_volume: int,
        category: str
    ) -> List[str]:
        """识别风险因素"""
        risks = []

        if competition_level == CompetitionLevel.VERY_HIGH:
            risks.append("竞争极其激烈，获得排名困难")
        elif competition_level == CompetitionLevel.HIGH:
            risks.append("竞争激烈，需要大量资源投入")

        if trend_direction < -0.3:
            risks.append("搜索趋势下降，市场兴趣减弱")

        if search_volume < 1000:
            risks.append("搜索量较低，流量有限")

        if category == "technology":
            risks.append("技术类话题变化快，需要持续更新")

        return risks

    def _identify_opportunities(
        self,
        commercial_value: float,
        competition_level: CompetitionLevel,
        trend_direction: float,
        category: str
    ) -> List[str]:
        """识别机会"""
        opportunities = []

        if commercial_value > 0.7:
            opportunities.append("商业价值高，投资回报潜力大")

        if competition_level == CompetitionLevel.LOW:
            opportunities.append("竞争较低，容易获得排名")

        if trend_direction > 0.3:
            opportunities.append("上升趋势明显，抓住机会窗口")

        if category in ["smart_home", "security"]:
            opportunities.append("成长性行业，长期潜力好")

        return opportunities

    def _determine_investment_priority(
        self,
        commercial_value: float,
        competition_level: CompetitionLevel,
        estimated_revenue: Dict[str, float]
    ) -> str:
        """确定投资优先级"""
        max_revenue = max(estimated_revenue.values()) if estimated_revenue else 0

        # 综合评分
        priority_score = commercial_value

        # 竞争调整
        competition_penalties = {
            CompetitionLevel.LOW: 0,
            CompetitionLevel.MEDIUM: -0.1,
            CompetitionLevel.HIGH: -0.2,
            CompetitionLevel.VERY_HIGH: -0.3
        }
        priority_score += competition_penalties.get(competition_level, 0)

        # 收益调整
        if max_revenue > 1000:
            priority_score += 0.2
        elif max_revenue > 500:
            priority_score += 0.1

        # 确定优先级
        if priority_score >= 0.8:
            return "极高"
        elif priority_score >= 0.6:
            return "高"
        elif priority_score >= 0.4:
            return "中"
        elif priority_score >= 0.2:
            return "低"
        else:
            return "极低"

    def batch_analyze_commercial_value(
        self,
        items_data: List[Dict[str, Any]]
    ) -> List[CommercialAnalysisResult]:
        """批量分析商业价值"""
        results = []

        for item_data in items_data:
            try:
                result = self.analyze_commercial_value(
                    keyword_or_topic=item_data.get('keyword', ''),
                    search_volume=item_data.get('search_volume', 0),
                    commercial_intent=item_data.get('commercial_intent', 0.0),
                    competition_score=item_data.get('competition_score', 0.0),
                    trend_direction=item_data.get('trend_direction', 0.0),
                    brand_presence=item_data.get('brand_presence', 0.0),
                    category=item_data.get('category', 'general'),
                    metadata=item_data.get('metadata', {})
                )
                results.append(result)

            except Exception as e:
                self.logger.error(f"批量商业分析失败 {item_data}: {e}")
                error_result = self._create_error_result(
                    item_data.get('keyword', 'unknown'), str(e)
                )
                results.append(error_result)

        return results

    def get_high_value_opportunities(
        self,
        results: List[CommercialAnalysisResult],
        min_value: float = 0.6
    ) -> List[CommercialAnalysisResult]:
        """获取高价值机会"""
        high_value = [
            r for r in results
            if r.commercial_value >= min_value and r.investment_priority in ["极高", "高"]
        ]

        return sorted(
            high_value,
            key=lambda x: (x.commercial_value, max(x.estimated_monthly_revenue.values()) if x.estimated_monthly_revenue else 0),
            reverse=True
        )

    def _create_error_result(self, keyword_or_topic: str, error_msg: str) -> CommercialAnalysisResult:
        """创建错误结果"""
        return CommercialAnalysisResult(
            keyword_or_topic=keyword_or_topic,
            commercial_value=0.0,
            competition_level=CompetitionLevel.LOW,
            recommended_models=[],
            estimated_monthly_revenue={},
            risk_factors=[f"分析错误: {error_msg}"],
            opportunities=[],
            investment_priority="极低",
            metadata={}
        )