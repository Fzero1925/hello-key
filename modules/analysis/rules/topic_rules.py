"""
话题规则引擎

基于配置化规则处理话题的分类、生命周期分析、紧急度评估等业务逻辑
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from ..config.rules_config import RulesConfigManager, TopicRulesConfig


class TopicStage(Enum):
    """话题生命周期阶段"""
    EMERGING = "emerging"
    GROWING = "growing"
    PEAK = "peak"
    DECLINING = "declining"
    STABLE = "stable"


class UrgencyLevel(Enum):
    """紧急度等级"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


@dataclass
class TopicAnalysisResult:
    """话题分析结果"""
    topic: str
    category: str
    stage: TopicStage
    urgency_level: UrgencyLevel
    urgency_score: float
    trend_indicators: List[str]
    growth_rate: float
    estimated_lifetime_days: int
    recommendations: List[str]
    metadata: Dict[str, Any]


class TopicRuleEngine:
    """
    话题规则引擎

    提供基于规则的话题分析、生命周期评估和紧急度判断
    """

    def __init__(self, rules_config: Optional[TopicRulesConfig] = None):
        """
        初始化话题规则引擎

        Args:
            rules_config: 话题规则配置，如果为None则从配置管理器加载
        """
        self.logger = logging.getLogger(__name__)

        if rules_config:
            self.rules = rules_config
        else:
            config_manager = RulesConfigManager()
            self.rules = config_manager.get_topic_rules()

    def analyze_topic(
        self,
        topic: str,
        mentions_count: int = 0,
        first_seen: Optional[datetime] = None,
        growth_data: Optional[List[int]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TopicAnalysisResult:
        """
        分析话题

        Args:
            topic: 话题文本
            mentions_count: 提及次数
            first_seen: 首次发现时间
            growth_data: 增长数据点列表
            metadata: 附加元数据

        Returns:
            话题分析结果
        """
        try:
            metadata = metadata or {}

            # 分类识别
            category = self._classify_topic(topic)

            # 检测趋势指标
            trend_indicators = self._detect_trend_indicators(topic)

            # 计算增长率
            growth_rate = self._calculate_growth_rate(growth_data or [mentions_count])

            # 确定生命周期阶段
            stage = self._determine_lifecycle_stage(
                mentions_count, first_seen, growth_rate
            )

            # 计算紧急度
            urgency_score, urgency_level = self._calculate_urgency(
                topic, stage, trend_indicators, growth_rate, metadata
            )

            # 估算生命周期
            estimated_lifetime = self._estimate_lifetime(stage, category, growth_rate)

            # 生成建议
            recommendations = self._generate_recommendations(
                topic, category, stage, urgency_level, growth_rate
            )

            return TopicAnalysisResult(
                topic=topic,
                category=category,
                stage=stage,
                urgency_level=urgency_level,
                urgency_score=urgency_score,
                trend_indicators=trend_indicators,
                growth_rate=growth_rate,
                estimated_lifetime_days=estimated_lifetime,
                recommendations=recommendations,
                metadata=metadata
            )

        except Exception as e:
            self.logger.error(f"话题分析失败 {topic}: {e}")
            return self._create_error_result(topic, str(e))

    def _classify_topic(self, topic: str) -> str:
        """对话题进行分类"""
        topic_lower = topic.lower()

        for category, keywords in self.rules.topic_categories.items():
            for keyword in keywords:
                if keyword.lower() in topic_lower:
                    return category

        return "general"

    def _detect_trend_indicators(self, topic: str) -> List[str]:
        """检测趋势指标"""
        detected = []
        topic_lower = topic.lower()

        for indicator in self.rules.trending_indicators:
            if indicator.lower() in topic_lower:
                detected.append(indicator)

        return detected

    def _calculate_growth_rate(self, growth_data: List[int]) -> float:
        """计算增长率"""
        if len(growth_data) < 2:
            return 0.0

        try:
            recent_avg = sum(growth_data[-3:]) / len(growth_data[-3:])
            earlier_avg = sum(growth_data[:-3]) / len(growth_data[:-3]) if len(growth_data) > 3 else growth_data[0]

            if earlier_avg == 0:
                return 1.0 if recent_avg > 0 else 0.0

            growth_rate = (recent_avg - earlier_avg) / earlier_avg
            return max(-1.0, min(2.0, growth_rate))  # 限制在合理范围内

        except Exception:
            return 0.0

    def _determine_lifecycle_stage(
        self,
        mentions_count: int,
        first_seen: Optional[datetime],
        growth_rate: float
    ) -> TopicStage:
        """确定生命周期阶段"""
        # 计算话题年龄
        if first_seen:
            age_hours = (datetime.now() - first_seen).total_seconds() / 3600
        else:
            age_hours = 24  # 默认假设24小时

        # 根据规则确定阶段
        for stage_name, criteria in self.rules.lifecycle_stages.items():
            min_mentions = criteria.get('min_mentions', 0)
            max_age_hours = criteria.get('max_age_hours', float('inf'))
            expected_growth = criteria.get('growth_rate', 0)

            # 检查是否满足该阶段的条件
            if (mentions_count >= min_mentions and
                age_hours <= max_age_hours and
                self._growth_matches_stage(growth_rate, expected_growth)):

                if stage_name == "emerging":
                    return TopicStage.EMERGING
                elif stage_name == "growing":
                    return TopicStage.GROWING
                elif stage_name == "peak":
                    return TopicStage.PEAK
                elif stage_name == "declining":
                    return TopicStage.DECLINING
                elif stage_name == "stable":
                    return TopicStage.STABLE

        # 默认阶段判断
        if growth_rate > 0.3:
            return TopicStage.GROWING
        elif growth_rate < -0.2:
            return TopicStage.DECLINING
        else:
            return TopicStage.STABLE

    def _growth_matches_stage(self, actual_growth: float, expected_growth: float) -> bool:
        """检查增长率是否匹配阶段"""
        tolerance = 0.2
        return abs(actual_growth - expected_growth) <= tolerance

    def _calculate_urgency(
        self,
        topic: str,
        stage: TopicStage,
        trend_indicators: List[str],
        growth_rate: float,
        metadata: Dict[str, Any]
    ) -> Tuple[float, UrgencyLevel]:
        """计算紧急度"""
        urgency_score = 0.0

        # 基于生命周期阶段的基础分数
        stage_scores = {
            TopicStage.EMERGING: 0.8,
            TopicStage.GROWING: 0.6,
            TopicStage.PEAK: 0.9,
            TopicStage.DECLINING: 0.3,
            TopicStage.STABLE: 0.2
        }
        urgency_score += stage_scores.get(stage, 0.2)

        # 趋势指标影响
        for indicator in trend_indicators:
            if indicator in ['breaking', 'urgent', 'critical']:
                urgency_score += 0.3
            elif indicator in ['new', 'latest', 'trending']:
                urgency_score += 0.2

        # 增长率影响
        if growth_rate > 0.5:
            urgency_score += 0.2
        elif growth_rate > 0.2:
            urgency_score += 0.1

        # 特定类型话题的紧急度调整
        topic_lower = topic.lower()
        if any(word in topic_lower for word in ['security', 'breach', 'vulnerability']):
            urgency_score += 0.3
        elif any(word in topic_lower for word in ['release', 'launch', 'announcement']):
            urgency_score += 0.2

        # 元数据影响
        if metadata.get('source_authority', 0) > 0.8:
            urgency_score += 0.1

        # 限制在0-1范围内
        urgency_score = max(0.0, min(1.0, urgency_score))

        # 确定紧急度等级
        if urgency_score >= 0.8:
            urgency_level = UrgencyLevel.CRITICAL
        elif urgency_score >= 0.6:
            urgency_level = UrgencyLevel.HIGH
        elif urgency_score >= 0.4:
            urgency_level = UrgencyLevel.MEDIUM
        elif urgency_score >= 0.2:
            urgency_level = UrgencyLevel.LOW
        else:
            urgency_level = UrgencyLevel.MINIMAL

        return urgency_score, urgency_level

    def _estimate_lifetime(self, stage: TopicStage, category: str, growth_rate: float) -> int:
        """估算话题生命周期（天）"""
        # 基础生命周期
        base_lifetimes = {
            TopicStage.EMERGING: 7,
            TopicStage.GROWING: 14,
            TopicStage.PEAK: 30,
            TopicStage.DECLINING: 7,
            TopicStage.STABLE: 90
        }

        base_lifetime = base_lifetimes.get(stage, 30)

        # 分类调整
        category_multipliers = {
            'technology': 1.5,
            'security': 0.8,
            'reviews': 2.0,
            'tutorials': 3.0,
            'general': 1.0
        }

        category_multiplier = category_multipliers.get(category, 1.0)

        # 增长率调整
        if growth_rate > 0.5:
            growth_multiplier = 1.3  # 快速增长的话题持续时间可能更长
        elif growth_rate < -0.3:
            growth_multiplier = 0.7  # 快速衰减的话题持续时间较短
        else:
            growth_multiplier = 1.0

        estimated_lifetime = int(base_lifetime * category_multiplier * growth_multiplier)
        return max(1, min(365, estimated_lifetime))  # 限制在1天到1年之间

    def _generate_recommendations(
        self,
        topic: str,
        category: str,
        stage: TopicStage,
        urgency_level: UrgencyLevel,
        growth_rate: float
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        # 基于紧急度的建议
        if urgency_level == UrgencyLevel.CRITICAL:
            recommendations.append("紧急度极高，建议立即创建相关内容")
        elif urgency_level == UrgencyLevel.HIGH:
            recommendations.append("紧急度高，建议24小时内响应")
        elif urgency_level == UrgencyLevel.MEDIUM:
            recommendations.append("紧急度中等，建议3天内处理")
        else:
            recommendations.append("紧急度较低，可以安排到常规计划中")

        # 基于生命周期阶段的建议
        if stage == TopicStage.EMERGING:
            recommendations.append("话题处于萌芽期，抓住早期机会创建内容")
        elif stage == TopicStage.GROWING:
            recommendations.append("话题正在增长，是投入资源的好时机")
        elif stage == TopicStage.PEAK:
            recommendations.append("话题处于巅峰期，快速创建高质量内容获取最大流量")
        elif stage == TopicStage.DECLINING:
            recommendations.append("话题开始衰减，考虑内容更新或转向相关话题")
        else:
            recommendations.append("话题相对稳定，适合创建长期价值内容")

        # 基于增长率的建议
        if growth_rate > 0.3:
            recommendations.append("话题增长迅速，建议快速行动抢占先机")
        elif growth_rate < -0.2:
            recommendations.append("话题热度下降，考虑是否值得继续投入")

        # 基于分类的建议
        if category == "technology":
            recommendations.append("技术类话题，建议深度解析和实用指南")
        elif category == "security":
            recommendations.append("安全类话题，建议及时跟进并提供解决方案")
        elif category == "reviews":
            recommendations.append("评价类话题，建议创建对比分析内容")

        return recommendations

    def batch_analyze_topics(
        self,
        topics_data: List[Dict[str, Any]]
    ) -> List[TopicAnalysisResult]:
        """批量分析话题"""
        results = []

        for topic_data in topics_data:
            try:
                topic = topic_data.get('topic', '')
                mentions_count = topic_data.get('mentions_count', 0)
                first_seen_str = topic_data.get('first_seen')
                first_seen = datetime.fromisoformat(first_seen_str) if first_seen_str else None
                growth_data = topic_data.get('growth_data', [])
                metadata = topic_data.get('metadata', {})

                result = self.analyze_topic(
                    topic, mentions_count, first_seen, growth_data, metadata
                )
                results.append(result)

            except Exception as e:
                self.logger.error(f"批量话题分析失败 {topic_data}: {e}")
                error_result = self._create_error_result(
                    topic_data.get('topic', 'unknown'), str(e)
                )
                results.append(error_result)

        return results

    def get_urgent_topics(
        self,
        results: List[TopicAnalysisResult],
        min_urgency: UrgencyLevel = UrgencyLevel.MEDIUM
    ) -> List[TopicAnalysisResult]:
        """获取紧急话题"""
        urgency_order = {
            UrgencyLevel.CRITICAL: 5,
            UrgencyLevel.HIGH: 4,
            UrgencyLevel.MEDIUM: 3,
            UrgencyLevel.LOW: 2,
            UrgencyLevel.MINIMAL: 1
        }

        min_level = urgency_order.get(min_urgency, 3)

        urgent_topics = [
            result for result in results
            if urgency_order.get(result.urgency_level, 0) >= min_level
        ]

        # 按紧急度排序
        return sorted(
            urgent_topics,
            key=lambda x: (
                urgency_order.get(x.urgency_level, 0),
                x.urgency_score,
                x.growth_rate
            ),
            reverse=True
        )

    def generate_topic_report(
        self,
        results: List[TopicAnalysisResult]
    ) -> Dict[str, Any]:
        """生成话题分析报告"""
        total_topics = len(results)

        # 统计生命周期阶段分布
        stage_distribution = {}
        for stage in TopicStage:
            count = len([r for r in results if r.stage == stage])
            stage_distribution[stage.value] = {
                'count': count,
                'percentage': (count / total_topics * 100) if total_topics > 0 else 0
            }

        # 统计紧急度分布
        urgency_distribution = {}
        for urgency in UrgencyLevel:
            count = len([r for r in results if r.urgency_level == urgency])
            urgency_distribution[urgency.value] = {
                'count': count,
                'percentage': (count / total_topics * 100) if total_topics > 0 else 0
            }

        # 计算平均增长率
        avg_growth_rate = (
            sum(r.growth_rate for r in results) / total_topics
            if total_topics > 0 else 0
        )

        # 获取热门分类
        category_counts = {}
        for result in results:
            category_counts[result.category] = category_counts.get(result.category, 0) + 1

        top_categories = sorted(
            category_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            'summary': {
                'total_topics': total_topics,
                'avg_growth_rate': round(avg_growth_rate, 3),
                'urgent_topics_count': len([r for r in results if r.urgency_level in [UrgencyLevel.CRITICAL, UrgencyLevel.HIGH]])
            },
            'stage_distribution': stage_distribution,
            'urgency_distribution': urgency_distribution,
            'top_categories': top_categories,
            'urgent_topics': [
                {
                    'topic': r.topic,
                    'urgency_level': r.urgency_level.value,
                    'urgency_score': r.urgency_score,
                    'stage': r.stage.value
                }
                for r in self.get_urgent_topics(results, UrgencyLevel.HIGH)[:10]
            ]
        }

    def _create_error_result(self, topic: str, error_msg: str) -> TopicAnalysisResult:
        """创建错误结果"""
        return TopicAnalysisResult(
            topic=topic,
            category="error",
            stage=TopicStage.STABLE,
            urgency_level=UrgencyLevel.MINIMAL,
            urgency_score=0.0,
            trend_indicators=[],
            growth_rate=0.0,
            estimated_lifetime_days=1,
            recommendations=[f"分析错误: {error_msg}"],
            metadata={}
        )