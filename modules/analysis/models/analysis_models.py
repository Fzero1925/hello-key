"""
分析数据模型

定义标准化的分析结果数据结构
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum


class AnalysisType(Enum):
    """分析类型"""
    KEYWORD = "keyword"
    TOPIC = "topic"
    COMMERCIAL = "commercial"
    TREND = "trend"
    INTENT = "intent"


class ResultStatus(Enum):
    """结果状态"""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PARTIAL = "partial"


@dataclass
class AnalysisMetrics:
    """分析指标"""
    score: float = 0.0
    confidence: float = 0.0
    accuracy: float = 0.0
    completeness: float = 0.0
    quality_grade: str = "unknown"


@dataclass
class AnalysisResult:
    """通用分析结果"""
    # 基本信息
    analysis_id: str = ""
    analysis_type: AnalysisType = AnalysisType.KEYWORD
    target: str = ""  # 分析目标（关键词或话题）
    timestamp: datetime = field(default_factory=datetime.now)

    # 状态信息
    status: ResultStatus = ResultStatus.SUCCESS
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    # 核心指标
    metrics: AnalysisMetrics = field(default_factory=AnalysisMetrics)

    # 详细数据
    data: Dict[str, Any] = field(default_factory=dict)

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 建议和洞察
    recommendations: List[str] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)

    # 处理时间
    processing_time_ms: float = 0.0


@dataclass
class ScoreMetrics:
    """评分指标详情"""
    # 主要得分
    total_score: float = 0.0
    opportunity_score: float = 0.0
    commercial_value: float = 0.0

    # 子指标得分
    trend_score: float = 0.0
    intent_score: float = 0.0
    search_volume_score: float = 0.0
    freshness_score: float = 0.0
    difficulty_score: float = 0.0

    # 权重信息
    weights: Dict[str, float] = field(default_factory=dict)

    # 评分说明
    explanations: Dict[str, str] = field(default_factory=dict)


@dataclass
class InsightData:
    """洞察数据"""
    # 洞察类型
    insight_type: str = "general"
    priority: str = "medium"  # high, medium, low

    # 洞察内容
    title: str = ""
    description: str = ""
    evidence: List[str] = field(default_factory=list)

    # 行动建议
    action_items: List[str] = field(default_factory=list)
    estimated_impact: str = "medium"  # high, medium, low

    # 时效性
    urgency: str = "normal"  # urgent, normal, low
    validity_period_days: int = 30

    # 置信度
    confidence_level: float = 0.0
    data_quality: str = "good"  # excellent, good, fair, poor


@dataclass
class KeywordAnalysisData:
    """关键词分析专用数据"""
    keyword: str = ""
    category: str = ""
    search_volume: int = 0
    competition_level: str = "medium"
    commercial_intent: float = 0.0

    # 趋势数据
    trend_direction: str = "stable"  # rising, falling, stable, volatile
    trend_strength: float = 0.0
    seasonality_score: float = 0.0

    # 商业价值
    estimated_cpc: float = 0.0
    estimated_revenue: Dict[str, float] = field(default_factory=dict)
    revenue_potential: str = "medium"  # high, medium, low

    # 竞争分析
    top_competitors: List[str] = field(default_factory=list)
    content_gaps: List[str] = field(default_factory=list)
    ranking_difficulty: str = "medium"

    # 相关关键词
    related_keywords: List[str] = field(default_factory=list)
    long_tail_opportunities: List[str] = field(default_factory=list)


@dataclass
class TopicAnalysisData:
    """话题分析专用数据"""
    topic: str = ""
    category: str = ""
    lifecycle_stage: str = "growing"  # emerging, growing, peak, declining, stable

    # 热度指标
    mention_count: int = 0
    engagement_rate: float = 0.0
    viral_potential: float = 0.0

    # 时间特征
    first_detected: Optional[datetime] = None
    peak_time: Optional[datetime] = None
    estimated_lifetime_days: int = 30

    # 传播特征
    spread_velocity: float = 0.0
    source_diversity: float = 0.0
    authority_score: float = 0.0

    # 商业机会
    monetization_potential: float = 0.0
    target_audience: List[str] = field(default_factory=list)
    content_opportunities: List[str] = field(default_factory=list)

    # 风险评估
    controversy_level: float = 0.0
    sustainability: float = 0.0
    market_saturation: float = 0.0


@dataclass
class TrendAnalysisData:
    """趋势分析专用数据"""
    trend_type: str = "short_term"  # short_term, long_term, seasonal, cyclical
    direction: str = "stable"  # rising, falling, stable, volatile
    strength: float = 0.0

    # 时间序列数据
    time_series: List[Dict[str, Any]] = field(default_factory=list)
    change_points: List[datetime] = field(default_factory=list)

    # 预测数据
    forecast: List[Dict[str, Any]] = field(default_factory=list)
    prediction_confidence: float = 0.0
    forecast_horizon_days: int = 30

    # 模式识别
    detected_patterns: List[str] = field(default_factory=list)
    seasonality: Dict[str, float] = field(default_factory=dict)
    anomalies: List[Dict[str, Any]] = field(default_factory=list)

    # 影响因素
    driving_factors: List[str] = field(default_factory=list)
    external_influences: List[str] = field(default_factory=list)


@dataclass
class CommercialAnalysisData:
    """商业分析专用数据"""
    target_item: str = ""
    market_size: float = 0.0
    competition_intensity: float = 0.0

    # 收益预估
    revenue_models: List[str] = field(default_factory=list)
    estimated_monthly_revenue: Dict[str, float] = field(default_factory=dict)
    roi_estimate: float = 0.0
    payback_period_months: int = 12

    # 市场分析
    market_trends: List[str] = field(default_factory=list)
    customer_segments: List[str] = field(default_factory=list)
    value_proposition: str = ""

    # 风险分析
    risk_factors: List[str] = field(default_factory=list)
    risk_level: str = "medium"  # high, medium, low
    mitigation_strategies: List[str] = field(default_factory=list)

    # 投资建议
    investment_priority: str = "medium"  # high, medium, low
    recommended_budget: float = 0.0
    success_probability: float = 0.0


@dataclass
class BatchAnalysisResult:
    """批量分析结果"""
    batch_id: str = ""
    total_items: int = 0
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0

    # 时间信息
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_processing_time_ms: float = 0.0

    # 结果汇总
    results: List[AnalysisResult] = field(default_factory=list)
    summary_statistics: Dict[str, Any] = field(default_factory=dict)

    # 质量指标
    average_confidence: float = 0.0
    quality_distribution: Dict[str, int] = field(default_factory=dict)

    # 错误信息
    errors: List[Dict[str, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ComparisonResult:
    """比较分析结果"""
    comparison_type: str = ""  # keyword_vs_keyword, topic_vs_topic, etc.
    items: List[str] = field(default_factory=list)

    # 比较维度
    comparison_dimensions: List[str] = field(default_factory=list)
    scores_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # 排名结果
    ranking: List[Dict[str, Any]] = field(default_factory=list)
    winner: str = ""
    confidence: float = 0.0

    # 差异分析
    significant_differences: List[Dict[str, Any]] = field(default_factory=list)
    similarity_score: float = 0.0

    # 建议
    selection_recommendation: str = ""
    optimization_suggestions: List[str] = field(default_factory=list)


# 工厂函数
def create_keyword_analysis_result(
    keyword: str,
    keyword_data: KeywordAnalysisData,
    score_metrics: ScoreMetrics,
    insights: List[InsightData] = None,
    **kwargs
) -> AnalysisResult:
    """创建关键词分析结果"""
    insights = insights or []

    return AnalysisResult(
        analysis_type=AnalysisType.KEYWORD,
        target=keyword,
        metrics=AnalysisMetrics(
            score=score_metrics.total_score,
            confidence=kwargs.get('confidence', 0.8),
            quality_grade=kwargs.get('quality_grade', 'good')
        ),
        data={
            'keyword_data': keyword_data,
            'score_metrics': score_metrics
        },
        insights=[insight.description for insight in insights],
        recommendations=kwargs.get('recommendations', []),
        **kwargs
    )


def create_topic_analysis_result(
    topic: str,
    topic_data: TopicAnalysisData,
    insights: List[InsightData] = None,
    **kwargs
) -> AnalysisResult:
    """创建话题分析结果"""
    insights = insights or []

    return AnalysisResult(
        analysis_type=AnalysisType.TOPIC,
        target=topic,
        metrics=AnalysisMetrics(
            score=kwargs.get('score', 0.0),
            confidence=kwargs.get('confidence', 0.7),
            quality_grade=kwargs.get('quality_grade', 'good')
        ),
        data={
            'topic_data': topic_data
        },
        insights=[insight.description for insight in insights],
        recommendations=kwargs.get('recommendations', []),
        **kwargs
    )


def create_commercial_analysis_result(
    target: str,
    commercial_data: CommercialAnalysisData,
    **kwargs
) -> AnalysisResult:
    """创建商业分析结果"""
    return AnalysisResult(
        analysis_type=AnalysisType.COMMERCIAL,
        target=target,
        metrics=AnalysisMetrics(
            score=commercial_data.success_probability,
            confidence=kwargs.get('confidence', 0.7),
            quality_grade=kwargs.get('quality_grade', 'good')
        ),
        data={
            'commercial_data': commercial_data
        },
        recommendations=commercial_data.mitigation_strategies + [commercial_data.value_proposition],
        **kwargs
    )


# 辅助函数
def merge_analysis_results(results: List[AnalysisResult]) -> BatchAnalysisResult:
    """合并多个分析结果为批量结果"""
    if not results:
        return BatchAnalysisResult()

    successful_results = [r for r in results if r.status == ResultStatus.SUCCESS]
    failed_results = [r for r in results if r.status == ResultStatus.ERROR]

    # 计算汇总统计
    if successful_results:
        avg_score = sum(r.metrics.score for r in successful_results) / len(successful_results)
        avg_confidence = sum(r.metrics.confidence for r in successful_results) / len(successful_results)
    else:
        avg_score = 0.0
        avg_confidence = 0.0

    # 质量分布
    quality_dist = {}
    for result in successful_results:
        grade = result.metrics.quality_grade
        quality_dist[grade] = quality_dist.get(grade, 0) + 1

    return BatchAnalysisResult(
        batch_id=f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        total_items=len(results),
        processed_items=len(results),
        successful_items=len(successful_results),
        failed_items=len(failed_results),
        results=results,
        summary_statistics={
            'average_score': round(avg_score, 3),
            'score_distribution': _calculate_score_distribution(successful_results),
            'top_performers': [r.target for r in sorted(successful_results, key=lambda x: x.metrics.score, reverse=True)[:5]]
        },
        average_confidence=round(avg_confidence, 3),
        quality_distribution=quality_dist,
        errors=[{'target': r.target, 'error': r.error_message} for r in failed_results if r.error_message],
        total_processing_time_ms=sum(r.processing_time_ms for r in results)
    )


def _calculate_score_distribution(results: List[AnalysisResult]) -> Dict[str, int]:
    """计算得分分布"""
    distribution = {
        '0-20': 0, '20-40': 0, '40-60': 0, '60-80': 0, '80-100': 0
    }

    for result in results:
        score = result.metrics.score * 100  # 转换为0-100范围
        if score < 20:
            distribution['0-20'] += 1
        elif score < 40:
            distribution['20-40'] += 1
        elif score < 60:
            distribution['40-60'] += 1
        elif score < 80:
            distribution['60-80'] += 1
        else:
            distribution['80-100'] += 1

    return distribution