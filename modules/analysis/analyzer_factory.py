"""
分析器工厂

提供统一的分析器创建和配置接口
"""

import logging
from typing import Optional, Dict, Any, Union
from pathlib import Path

from .algorithms.scoring import ScoringEngine, ScoreConfig
from .algorithms.value_estimation import ValueEstimator, ValueConfig
from .algorithms.trend_analysis import TrendAnalyzer, TrendConfig
from .algorithms.intent_detection import IntentDetector, IntentConfig

from .rules.keyword_rules import KeywordRuleEngine
from .rules.topic_rules import TopicRuleEngine
from .rules.commercial_rules import CommercialRuleEngine

from .config.algorithm_config import AlgorithmConfigManager
from .config.rules_config import RulesConfigManager


class AnalyzerFactory:
    """
    分析器工厂

    统一创建和管理各种分析器实例
    """

    def __init__(
        self,
        algorithm_config_path: Optional[str] = None,
        rules_config_path: Optional[str] = None
    ):
        """
        初始化分析器工厂

        Args:
            algorithm_config_path: 算法配置文件路径
            rules_config_path: 规则配置文件路径
        """
        self.logger = logging.getLogger(__name__)

        # 加载配置管理器
        self.algorithm_config_manager = AlgorithmConfigManager(algorithm_config_path)
        self.rules_config_manager = RulesConfigManager(rules_config_path)

        # 缓存已创建的实例
        self._algorithm_instances = {}
        self._rule_engine_instances = {}

        self.logger.info("分析器工厂初始化完成")

    def get_scoring_engine(self, config_override: Optional[Dict[str, Any]] = None) -> ScoringEngine:
        """
        获取评分引擎

        Args:
            config_override: 配置覆盖参数

        Returns:
            评分引擎实例
        """
        cache_key = "scoring_engine"

        if cache_key not in self._algorithm_instances:
            # 获取配置
            config = self.algorithm_config_manager.get_scoring_config()

            # 应用配置覆盖
            if config_override:
                for key, value in config_override.items():
                    if hasattr(config, key):
                        setattr(config, key, value)

            # 转换为算法需要的配置格式
            score_config = ScoreConfig(
                trend_weight=config.trend_weight,
                intent_weight=config.intent_weight,
                search_volume_weight=config.search_volume_weight,
                freshness_weight=config.freshness_weight,
                difficulty_penalty=config.difficulty_penalty,
                adsense_ctr_serp=config.adsense_ctr_serp,
                adsense_click_share_rank=config.adsense_click_share_rank,
                adsense_rpm_usd=config.adsense_rpm_usd,
                amazon_ctr=config.amazon_ctr,
                amazon_conversion_rate=config.amazon_conversion_rate,
                amazon_aov_usd=config.amazon_aov_usd,
                amazon_commission=config.amazon_commission
            )

            self._algorithm_instances[cache_key] = ScoringEngine(score_config)
            self.logger.debug("创建新的评分引擎实例")

        return self._algorithm_instances[cache_key]

    def get_value_estimator(self, config_override: Optional[Dict[str, Any]] = None) -> ValueEstimator:
        """
        获取价值评估器

        Args:
            config_override: 配置覆盖参数

        Returns:
            价值评估器实例
        """
        cache_key = "value_estimator"

        if cache_key not in self._algorithm_instances:
            # 获取配置
            config = self.algorithm_config_manager.get_value_estimation_config()

            # 应用配置覆盖
            if config_override:
                for key, value in config_override.items():
                    if hasattr(config, key):
                        setattr(config, key, value)

            # 转换为算法需要的配置格式
            value_config = ValueConfig(
                adsense_ctr=config.adsense_ctr,
                adsense_click_share=config.adsense_click_share,
                adsense_rpm=config.adsense_rpm,
                amazon_ctr=config.amazon_ctr,
                amazon_conversion_rate=config.amazon_conversion_rate,
                amazon_aov=config.amazon_aov,
                amazon_commission=config.amazon_commission,
                affiliate_ctr=config.affiliate_ctr,
                affiliate_conversion_rate=config.affiliate_conversion_rate,
                affiliate_commission_rate=config.affiliate_commission_rate,
                affiliate_avg_sale=config.affiliate_avg_sale,
                lead_ctr=config.lead_ctr,
                lead_conversion_rate=config.lead_conversion_rate,
                lead_value=config.lead_value,
                market_volatility=config.market_volatility,
                competition_factor=config.competition_factor,
                seasonality_factor=config.seasonality_factor
            )

            self._algorithm_instances[cache_key] = ValueEstimator(value_config)
            self.logger.debug("创建新的价值评估器实例")

        return self._algorithm_instances[cache_key]

    def get_trend_analyzer(self, config_override: Optional[Dict[str, Any]] = None) -> TrendAnalyzer:
        """
        获取趋势分析器

        Args:
            config_override: 配置覆盖参数

        Returns:
            趋势分析器实例
        """
        cache_key = "trend_analyzer"

        if cache_key not in self._algorithm_instances:
            # 获取配置
            config = self.algorithm_config_manager.get_trend_analysis_config()

            # 应用配置覆盖
            if config_override:
                for key, value in config_override.items():
                    if hasattr(config, key):
                        setattr(config, key, value)

            # 转换为算法需要的配置格式
            trend_config = TrendConfig(
                short_window=config.short_window,
                long_window=config.long_window,
                trend_threshold=config.trend_threshold,
                volatility_low=config.volatility_low,
                volatility_moderate=config.volatility_moderate,
                volatility_high=config.volatility_high,
                strength_thresholds=config.strength_thresholds
            )

            self._algorithm_instances[cache_key] = TrendAnalyzer(trend_config)
            self.logger.debug("创建新的趋势分析器实例")

        return self._algorithm_instances[cache_key]

    def get_intent_detector(self, config_override: Optional[Dict[str, Any]] = None) -> IntentDetector:
        """
        获取意图识别器

        Args:
            config_override: 配置覆盖参数

        Returns:
            意图识别器实例
        """
        cache_key = "intent_detector"

        if cache_key not in self._algorithm_instances:
            # 获取配置
            config = self.algorithm_config_manager.get_intent_detection_config()

            # 应用配置覆盖
            if config_override:
                for key, value in config_override.items():
                    if hasattr(config, key):
                        setattr(config, key, value)

            # 转换为算法需要的配置格式
            intent_config = IntentConfig(
                commercial_keywords=set(config.commercial_keywords),
                transactional_keywords=set(config.transactional_keywords),
                informational_keywords=set(config.informational_keywords),
                navigational_keywords=set(config.navigational_keywords),
                local_keywords=set(config.local_keywords),
                brand_names=set(config.brand_names),
                intent_weights=config.intent_weights
            )

            self._algorithm_instances[cache_key] = IntentDetector(intent_config)
            self.logger.debug("创建新的意图识别器实例")

        return self._algorithm_instances[cache_key]

    def get_keyword_rule_engine(self, config_override: Optional[Dict[str, Any]] = None) -> KeywordRuleEngine:
        """
        获取关键词规则引擎

        Args:
            config_override: 配置覆盖参数

        Returns:
            关键词规则引擎实例
        """
        cache_key = "keyword_rule_engine"

        if cache_key not in self._rule_engine_instances:
            # 获取配置
            config = self.rules_config_manager.get_keyword_rules()

            # 应用配置覆盖
            if config_override:
                for key, value in config_override.items():
                    if hasattr(config, key):
                        setattr(config, key, value)

            self._rule_engine_instances[cache_key] = KeywordRuleEngine(config)
            self.logger.debug("创建新的关键词规则引擎实例")

        return self._rule_engine_instances[cache_key]

    def get_topic_rule_engine(self, config_override: Optional[Dict[str, Any]] = None) -> TopicRuleEngine:
        """
        获取话题规则引擎

        Args:
            config_override: 配置覆盖参数

        Returns:
            话题规则引擎实例
        """
        cache_key = "topic_rule_engine"

        if cache_key not in self._rule_engine_instances:
            # 获取配置
            config = self.rules_config_manager.get_topic_rules()

            # 应用配置覆盖
            if config_override:
                for key, value in config_override.items():
                    if hasattr(config, key):
                        setattr(config, key, value)

            self._rule_engine_instances[cache_key] = TopicRuleEngine(config)
            self.logger.debug("创建新的话题规则引擎实例")

        return self._rule_engine_instances[cache_key]

    def get_commercial_rule_engine(self, config_override: Optional[Dict[str, Any]] = None) -> CommercialRuleEngine:
        """
        获取商业规则引擎

        Args:
            config_override: 配置覆盖参数

        Returns:
            商业规则引擎实例
        """
        cache_key = "commercial_rule_engine"

        if cache_key not in self._rule_engine_instances:
            # 获取配置
            config = self.rules_config_manager.get_commercial_rules()

            # 应用配置覆盖
            if config_override:
                for key, value in config_override.items():
                    if hasattr(config, key):
                        setattr(config, key, value)

            self._rule_engine_instances[cache_key] = CommercialRuleEngine(config)
            self.logger.debug("创建新的商业规则引擎实例")

        return self._rule_engine_instances[cache_key]

    def create_analysis_suite(self, suite_type: str = "full") -> Dict[str, Any]:
        """
        创建分析套件

        Args:
            suite_type: 套件类型 ('full', 'keyword', 'topic', 'commercial')

        Returns:
            分析器实例字典
        """
        suite = {}

        if suite_type in ["full", "keyword"]:
            suite.update({
                'scoring_engine': self.get_scoring_engine(),
                'intent_detector': self.get_intent_detector(),
                'keyword_rule_engine': self.get_keyword_rule_engine(),
                'value_estimator': self.get_value_estimator()
            })

        if suite_type in ["full", "topic"]:
            suite.update({
                'trend_analyzer': self.get_trend_analyzer(),
                'topic_rule_engine': self.get_topic_rule_engine()
            })

        if suite_type in ["full", "commercial"]:
            suite.update({
                'commercial_rule_engine': self.get_commercial_rule_engine(),
                'value_estimator': self.get_value_estimator()
            })

        self.logger.info(f"创建{suite_type}分析套件，包含{len(suite)}个组件")
        return suite

    def reload_configurations(self):
        """重新加载配置"""
        try:
            # 清空实例缓存
            self._algorithm_instances.clear()
            self._rule_engine_instances.clear()

            # 重新加载配置
            self.algorithm_config_manager = AlgorithmConfigManager()
            self.rules_config_manager = RulesConfigManager()

            self.logger.info("配置重新加载完成")

        except Exception as e:
            self.logger.error(f"配置重新加载失败: {e}")
            raise

    def validate_factory_setup(self) -> Dict[str, Any]:
        """
        验证工厂设置

        Returns:
            验证结果
        """
        validation_result = {
            'valid': True,
            'algorithm_config_valid': False,
            'rules_config_valid': False,
            'instances_created': 0,
            'errors': [],
            'warnings': []
        }

        try:
            # 验证算法配置
            algo_validation = self.algorithm_config_manager.validate_config()
            validation_result['algorithm_config_valid'] = algo_validation['valid']
            if not algo_validation['valid']:
                validation_result['errors'].extend(algo_validation['errors'])
            validation_result['warnings'].extend(algo_validation.get('warnings', []))

            # 验证规则配置
            rules_validation = self.rules_config_manager.validate_rules()
            validation_result['rules_config_valid'] = rules_validation['valid']
            if not rules_validation['valid']:
                validation_result['errors'].extend(rules_validation['errors'])
            validation_result['warnings'].extend(rules_validation.get('warnings', []))

            # 尝试创建核心实例
            try:
                self.get_scoring_engine()
                self.get_keyword_rule_engine()
                validation_result['instances_created'] += 2
            except Exception as e:
                validation_result['errors'].append(f"核心实例创建失败: {e}")

            # 总体有效性
            validation_result['valid'] = (
                validation_result['algorithm_config_valid'] and
                validation_result['rules_config_valid'] and
                validation_result['instances_created'] > 0 and
                len(validation_result['errors']) == 0
            )

        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"验证过程失败: {e}")

        return validation_result

    def get_factory_status(self) -> Dict[str, Any]:
        """
        获取工厂状态

        Returns:
            工厂状态信息
        """
        return {
            'algorithm_instances': len(self._algorithm_instances),
            'rule_engine_instances': len(self._rule_engine_instances),
            'total_instances': len(self._algorithm_instances) + len(self._rule_engine_instances),
            'algorithm_config_loaded': self.algorithm_config_manager is not None,
            'rules_config_loaded': self.rules_config_manager is not None,
            'available_algorithms': [
                'scoring_engine', 'value_estimator', 'trend_analyzer', 'intent_detector'
            ],
            'available_rule_engines': [
                'keyword_rule_engine', 'topic_rule_engine', 'commercial_rule_engine'
            ]
        }

    def export_factory_config(self, output_dir: str = "config") -> bool:
        """
        导出工厂配置模板

        Args:
            output_dir: 输出目录

        Returns:
            是否导出成功
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # 导出算法配置模板
            algo_template_path = output_path / "algorithm_config_template.yml"
            self.algorithm_config_manager.export_config_template(str(algo_template_path))

            # 导出规则配置模板
            rules_template_path = output_path / "rules_config_template.yml"
            self.rules_config_manager.export_rules_template(str(rules_template_path))

            self.logger.info(f"工厂配置模板导出成功: {output_dir}")
            return True

        except Exception as e:
            self.logger.error(f"工厂配置模板导出失败: {e}")
            return False


# 全局工厂实例
_global_factory = None


def get_default_factory() -> AnalyzerFactory:
    """获取默认的工厂实例"""
    global _global_factory
    if _global_factory is None:
        _global_factory = AnalyzerFactory()
    return _global_factory


def reset_default_factory():
    """重置默认工厂实例"""
    global _global_factory
    _global_factory = None


# 便捷函数
def create_scoring_engine(**config_overrides) -> ScoringEngine:
    """便捷函数：创建评分引擎"""
    return get_default_factory().get_scoring_engine(config_overrides)


def create_value_estimator(**config_overrides) -> ValueEstimator:
    """便捷函数：创建价值评估器"""
    return get_default_factory().get_value_estimator(config_overrides)


def create_keyword_rule_engine(**config_overrides) -> KeywordRuleEngine:
    """便捷函数：创建关键词规则引擎"""
    return get_default_factory().get_keyword_rule_engine(config_overrides)


def create_full_analysis_suite() -> Dict[str, Any]:
    """便捷函数：创建完整分析套件"""
    return get_default_factory().create_analysis_suite("full")