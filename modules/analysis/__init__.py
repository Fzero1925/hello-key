"""
通用分析模块

提供模块化的分析算法、规则引擎和数据模型
用于关键词分析和话题分析的通用功能
"""

from .algorithms import ScoringEngine, ValueEstimator, TrendAnalyzer
from .rules import KeywordRuleEngine, TopicRuleEngine, CommercialRuleEngine
from .models import AnalysisResult, ScoreMetrics, InsightData
from .analyzer_factory import AnalyzerFactory

__all__ = [
    'ScoringEngine', 'ValueEstimator', 'TrendAnalyzer',
    'KeywordRuleEngine', 'TopicRuleEngine', 'CommercialRuleEngine',
    'AnalysisResult', 'ScoreMetrics', 'InsightData',
    'AnalyzerFactory'
]

__version__ = "2.0.0"