"""
规则配置管理器

负责加载、验证和管理业务规则配置
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional, List, Set
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class KeywordRulesConfig:
    """关键词规则配置"""
    # 意图识别规则
    commercial_patterns: List[str] = field(default_factory=lambda: [
        r'\b(best|top|review|compare)\b',
        r'\b(price|cost|cheap|expensive)\b',
        r'\b(buy|purchase|deal|discount)\b',
        r'\bvs\b|\bversus\b'
    ])

    informational_patterns: List[str] = field(default_factory=lambda: [
        r'\b(how|what|why|when|where)\b',
        r'\b(tutorial|guide|learn|explain)\b',
        r'\b(tips|tricks|help|support)\b'
    ])

    transactional_patterns: List[str] = field(default_factory=lambda: [
        r'\b(buy|purchase|order|shop)\b',
        r'\b(install|download|subscribe)\b',
        r'\b(checkout|payment|shipping)\b'
    ])

    # 分类映射规则
    category_mappings: Dict[str, List[str]] = field(default_factory=lambda: {
        'smart_plugs': ['smart plug', 'wifi plug', 'outlet control', 'power control'],
        'security_cameras': ['security camera', 'surveillance', 'ip camera', 'cctv'],
        'smart_lighting': ['smart light', 'led bulb', 'dimmer', 'color bulb'],
        'smart_speakers': ['smart speaker', 'voice assistant', 'alexa', 'google home'],
        'smart_thermostats': ['smart thermostat', 'temperature control', 'hvac control'],
        'robot_vacuums': ['robot vacuum', 'robotic cleaner', 'automatic vacuum'],
        'smart_locks': ['smart lock', 'electronic lock', 'keyless entry']
    })

    # 品质修饰词规则
    quality_modifiers: Dict[str, float] = field(default_factory=lambda: {
        'premium': 1.2,
        'professional': 1.15,
        'advanced': 1.1,
        'basic': 0.9,
        'budget': 0.8,
        'cheap': 0.7
    })

    # 排除关键词
    excluded_keywords: List[str] = field(default_factory=lambda: [
        'porn', 'adult', 'illegal', 'hack', 'crack', 'pirate'
    ])

    # 最小/最大长度限制
    min_keyword_length: int = 3
    max_keyword_length: int = 100


@dataclass
class TopicRulesConfig:
    """话题规则配置"""
    # 热门话题识别规则
    trending_indicators: List[str] = field(default_factory=lambda: [
        'breaking', 'new', 'latest', 'update', 'release',
        'announcement', 'launch', 'trending', 'viral'
    ])

    # 紧急度计算规则
    urgency_factors: Dict[str, float] = field(default_factory=lambda: {
        'breaking_news': 1.0,
        'product_release': 0.8,
        'security_alert': 0.9,
        'trend_shift': 0.7,
        'seasonal_peak': 0.6
    })

    # 话题生命周期规则
    lifecycle_stages: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        'emerging': {'min_mentions': 5, 'max_age_hours': 24, 'growth_rate': 0.5},
        'growing': {'min_mentions': 20, 'max_age_hours': 72, 'growth_rate': 0.3},
        'peak': {'min_mentions': 50, 'max_age_hours': 168, 'growth_rate': 0.1},
        'declining': {'min_mentions': 10, 'max_age_hours': 336, 'growth_rate': -0.2},
        'stable': {'min_mentions': 5, 'max_age_hours': 720, 'growth_rate': 0.0}
    })

    # 话题分类规则
    topic_categories: Dict[str, List[str]] = field(default_factory=lambda: {
        'technology': ['ai', 'machine learning', 'blockchain', 'iot', 'cloud'],
        'smart_home': ['automation', 'smart device', 'home assistant', 'connected home'],
        'security': ['cybersecurity', 'privacy', 'data protection', 'vulnerability'],
        'reviews': ['product review', 'comparison', 'rating', 'recommendation'],
        'tutorials': ['how to', 'guide', 'tutorial', 'instructions', 'setup']
    })


@dataclass
class CommercialRulesConfig:
    """商业价值规则配置"""
    # 商业价值权重
    value_weights: Dict[str, float] = field(default_factory=lambda: {
        'search_volume': 0.3,
        'commercial_intent': 0.25,
        'competition_level': -0.2,  # 负权重，竞争越高价值越低
        'trend_direction': 0.15,
        'brand_presence': 0.1
    })

    # 竞争程度阈值
    competition_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'low': 0.3,
        'medium': 0.6,
        'high': 0.8,
        'very_high': 0.9
    })

    # 收益模型配置
    revenue_models: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        'adsense': {
            'enabled': True,
            'min_traffic': 1000,
            'ctr_range': [0.1, 0.4],
            'rpm_range': [5, 15]
        },
        'affiliate': {
            'enabled': True,
            'min_traffic': 500,
            'conversion_range': [0.01, 0.05],
            'commission_range': [0.02, 0.08]
        },
        'lead_generation': {
            'enabled': True,
            'min_traffic': 200,
            'conversion_range': [0.02, 0.10],
            'lead_value_range': [10, 100]
        }
    })

    # 行业特定规则
    industry_rules: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        'smart_home': {
            'seasonal_factor': 1.2,  # 节假日期间提升
            'replacement_cycle_months': 36,
            'avg_product_price': 150
        },
        'security': {
            'seasonal_factor': 1.0,
            'replacement_cycle_months': 60,
            'avg_product_price': 200
        },
        'entertainment': {
            'seasonal_factor': 1.3,
            'replacement_cycle_months': 24,
            'avg_product_price': 100
        }
    })


@dataclass
class FilteringRulesConfig:
    """过滤规则配置"""
    # 质量过滤规则
    quality_filters: Dict[str, Any] = field(default_factory=lambda: {
        'min_search_volume': 100,
        'min_trend_score': 0.1,
        'min_commercial_value': 0.2,
        'max_competition_score': 0.9
    })

    # 内容过滤规则
    content_filters: List[str] = field(default_factory=lambda: [
        r'\b(adult|porn|xxx)\b',
        r'\b(illegal|piracy|crack)\b',
        r'\b(spam|scam|fake)\b'
    ])

    # 重复检测规则
    deduplication_rules: Dict[str, Any] = field(default_factory=lambda: {
        'similarity_threshold': 0.8,
        'levenshtein_threshold': 3,
        'enable_stemming': True,
        'ignore_case': True
    })


@dataclass
class RulesConfiguration:
    """规则总配置"""
    keyword_rules: KeywordRulesConfig = field(default_factory=KeywordRulesConfig)
    topic_rules: TopicRulesConfig = field(default_factory=TopicRulesConfig)
    commercial_rules: CommercialRulesConfig = field(default_factory=CommercialRulesConfig)
    filtering_rules: FilteringRulesConfig = field(default_factory=FilteringRulesConfig)

    # 全局规则设置
    enable_caching: bool = True
    cache_ttl_minutes: int = 60
    max_batch_size: int = 100


class RulesConfigManager:
    """
    规则配置管理器

    负责加载、验证、更新和保存业务规则配置
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化规则配置管理器

        Args:
            config_path: 配置文件路径
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = self._resolve_config_path(config_path)
        self.config: RulesConfiguration = self._load_config()

    def _resolve_config_path(self, config_path: Optional[str]) -> str:
        """解析配置文件路径"""
        if config_path and os.path.exists(config_path):
            return config_path

        # 尝试默认路径
        default_paths = [
            "config/rules_config.yml",
            "config/business_rules.yml",
            "rules_config.yml",
            "business_rules.yml"
        ]

        for path in default_paths:
            if os.path.exists(path):
                return path

        self.logger.warning("未找到规则配置文件，将使用默认配置")
        return None

    def _load_config(self) -> RulesConfiguration:
        """加载配置"""
        if not self.config_path:
            self.logger.info("使用默认规则配置")
            return RulesConfiguration()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)

            if not config_data:
                self.logger.warning("配置文件为空，使用默认配置")
                return RulesConfiguration()

            config = RulesConfiguration()

            # 加载各部分配置
            if 'keyword_rules' in config_data:
                config.keyword_rules = self._parse_keyword_rules(config_data['keyword_rules'])

            if 'topic_rules' in config_data:
                config.topic_rules = self._parse_topic_rules(config_data['topic_rules'])

            if 'commercial_rules' in config_data:
                config.commercial_rules = self._parse_commercial_rules(config_data['commercial_rules'])

            if 'filtering_rules' in config_data:
                config.filtering_rules = self._parse_filtering_rules(config_data['filtering_rules'])

            # 加载全局设置
            if 'global' in config_data:
                global_config = config_data['global']
                config.enable_caching = global_config.get('enable_caching', True)
                config.cache_ttl_minutes = global_config.get('cache_ttl_minutes', 60)
                config.max_batch_size = global_config.get('max_batch_size', 100)

            self.logger.info(f"规则配置加载成功: {self.config_path}")
            return config

        except Exception as e:
            self.logger.error(f"规则配置文件加载失败: {e}")
            self.logger.info("使用默认规则配置")
            return RulesConfiguration()

    def _parse_keyword_rules(self, data: Dict[str, Any]) -> KeywordRulesConfig:
        """解析关键词规则配置"""
        config = KeywordRulesConfig()

        # 意图识别模式
        patterns = ['commercial_patterns', 'informational_patterns', 'transactional_patterns']
        for pattern in patterns:
            if pattern in data:
                setattr(config, pattern, data[pattern])

        # 其他配置项
        if 'category_mappings' in data:
            config.category_mappings.update(data['category_mappings'])

        if 'quality_modifiers' in data:
            config.quality_modifiers.update(data['quality_modifiers'])

        if 'excluded_keywords' in data:
            config.excluded_keywords = data['excluded_keywords']

        if 'min_keyword_length' in data:
            config.min_keyword_length = data['min_keyword_length']

        if 'max_keyword_length' in data:
            config.max_keyword_length = data['max_keyword_length']

        return config

    def _parse_topic_rules(self, data: Dict[str, Any]) -> TopicRulesConfig:
        """解析话题规则配置"""
        config = TopicRulesConfig()

        if 'trending_indicators' in data:
            config.trending_indicators = data['trending_indicators']

        if 'urgency_factors' in data:
            config.urgency_factors.update(data['urgency_factors'])

        if 'lifecycle_stages' in data:
            config.lifecycle_stages.update(data['lifecycle_stages'])

        if 'topic_categories' in data:
            config.topic_categories.update(data['topic_categories'])

        return config

    def _parse_commercial_rules(self, data: Dict[str, Any]) -> CommercialRulesConfig:
        """解析商业规则配置"""
        config = CommercialRulesConfig()

        if 'value_weights' in data:
            config.value_weights.update(data['value_weights'])

        if 'competition_thresholds' in data:
            config.competition_thresholds.update(data['competition_thresholds'])

        if 'revenue_models' in data:
            config.revenue_models.update(data['revenue_models'])

        if 'industry_rules' in data:
            config.industry_rules.update(data['industry_rules'])

        return config

    def _parse_filtering_rules(self, data: Dict[str, Any]) -> FilteringRulesConfig:
        """解析过滤规则配置"""
        config = FilteringRulesConfig()

        if 'quality_filters' in data:
            config.quality_filters.update(data['quality_filters'])

        if 'content_filters' in data:
            config.content_filters = data['content_filters']

        if 'deduplication_rules' in data:
            config.deduplication_rules.update(data['deduplication_rules'])

        return config

    def get_keyword_rules(self) -> KeywordRulesConfig:
        """获取关键词规则配置"""
        return self.config.keyword_rules

    def get_topic_rules(self) -> TopicRulesConfig:
        """获取话题规则配置"""
        return self.config.topic_rules

    def get_commercial_rules(self) -> CommercialRulesConfig:
        """获取商业规则配置"""
        return self.config.commercial_rules

    def get_filtering_rules(self) -> FilteringRulesConfig:
        """获取过滤规则配置"""
        return self.config.filtering_rules

    def add_keyword_pattern(self, intent_type: str, pattern: str) -> bool:
        """
        添加关键词模式

        Args:
            intent_type: 意图类型 ('commercial', 'informational', 'transactional')
            pattern: 正则表达式模式

        Returns:
            是否添加成功
        """
        try:
            pattern_attr = f"{intent_type}_patterns"
            if hasattr(self.config.keyword_rules, pattern_attr):
                patterns = getattr(self.config.keyword_rules, pattern_attr)
                if pattern not in patterns:
                    patterns.append(pattern)
                    self.logger.info(f"添加{intent_type}模式: {pattern}")
                    return True
            return False
        except Exception as e:
            self.logger.error(f"添加关键词模式失败: {e}")
            return False

    def update_category_mapping(self, category: str, keywords: List[str]) -> bool:
        """
        更新分类映射

        Args:
            category: 分类名称
            keywords: 关键词列表

        Returns:
            是否更新成功
        """
        try:
            self.config.keyword_rules.category_mappings[category] = keywords
            self.logger.info(f"更新分类映射: {category}")
            return True
        except Exception as e:
            self.logger.error(f"更新分类映射失败: {e}")
            return False

    def set_quality_filter(self, filter_name: str, threshold: float) -> bool:
        """
        设置质量过滤阈值

        Args:
            filter_name: 过滤器名称
            threshold: 阈值

        Returns:
            是否设置成功
        """
        try:
            self.config.filtering_rules.quality_filters[filter_name] = threshold
            self.logger.info(f"设置质量过滤器 {filter_name}: {threshold}")
            return True
        except Exception as e:
            self.logger.error(f"设置质量过滤器失败: {e}")
            return False

    def validate_rules(self) -> Dict[str, Any]:
        """
        验证规则配置

        Returns:
            验证结果
        """
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': []
        }

        try:
            # 验证关键词长度限制
            kw_rules = self.config.keyword_rules
            if kw_rules.min_keyword_length >= kw_rules.max_keyword_length:
                validation_result['errors'].append(
                    f"最小关键词长度 ({kw_rules.min_keyword_length}) 应小于最大长度 ({kw_rules.max_keyword_length})"
                )

            # 验证商业价值权重
            weights = self.config.commercial_rules.value_weights
            weight_sum = sum(abs(w) for w in weights.values())
            if weight_sum < 0.5 or weight_sum > 2.0:
                validation_result['warnings'].append(
                    f"商业价值权重总和异常: {weight_sum:.2f}"
                )

            # 验证竞争阈值顺序
            thresholds = self.config.commercial_rules.competition_thresholds
            threshold_values = [thresholds.get(k, 0) for k in ['low', 'medium', 'high', 'very_high']]
            if threshold_values != sorted(threshold_values):
                validation_result['errors'].append("竞争阈值应该按升序排列")

            # 验证过滤器阈值范围
            filters = self.config.filtering_rules.quality_filters
            for filter_name, value in filters.items():
                if filter_name.startswith('min_') and value < 0:
                    validation_result['errors'].append(f"{filter_name} 不能为负数: {value}")
                elif filter_name.startswith('max_') and value > 1 and 'score' in filter_name:
                    validation_result['errors'].append(f"{filter_name} 评分不能超过1: {value}")

            if validation_result['errors']:
                validation_result['valid'] = False

        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"规则验证失败: {e}")

        return validation_result

    def export_rules_template(self, output_path: str = "rules_config_template.yml") -> bool:
        """
        导出规则配置模板

        Args:
            output_path: 输出路径

        Returns:
            是否导出成功
        """
        try:
            template_content = """# 业务规则配置文件模板
#
# 这个文件包含了智能关键词分析工具中所有业务规则的配置
# 请根据实际业务需求调整规则参数

# 关键词规则配置
keyword_rules:
  # 意图识别正则表达式模式
  commercial_patterns:
    - '\\b(best|top|review|compare)\\b'
    - '\\b(price|cost|cheap|expensive)\\b'
    - '\\b(buy|purchase|deal|discount)\\b'

  informational_patterns:
    - '\\b(how|what|why|when|where)\\b'
    - '\\b(tutorial|guide|learn|explain)\\b'

  transactional_patterns:
    - '\\b(buy|purchase|order|shop)\\b'
    - '\\b(install|download|subscribe)\\b'

  # 分类映射规则
  category_mappings:
    smart_plugs:
      - smart plug
      - wifi plug
      - outlet control
    security_cameras:
      - security camera
      - surveillance
      - ip camera

  # 品质修饰词权重
  quality_modifiers:
    premium: 1.2
    professional: 1.15
    basic: 0.9
    budget: 0.8

  # 排除关键词
  excluded_keywords:
    - spam
    - illegal
    - adult

  # 长度限制
  min_keyword_length: 3
  max_keyword_length: 100

# 话题规则配置
topic_rules:
  # 热门话题指示词
  trending_indicators:
    - breaking
    - new
    - latest
    - trending

  # 紧急度因子
  urgency_factors:
    breaking_news: 1.0
    product_release: 0.8
    security_alert: 0.9

  # 话题生命周期阶段
  lifecycle_stages:
    emerging:
      min_mentions: 5
      max_age_hours: 24
      growth_rate: 0.5
    growing:
      min_mentions: 20
      max_age_hours: 72
      growth_rate: 0.3

# 商业价值规则配置
commercial_rules:
  # 价值权重
  value_weights:
    search_volume: 0.3
    commercial_intent: 0.25
    competition_level: -0.2
    trend_direction: 0.15

  # 竞争程度阈值
  competition_thresholds:
    low: 0.3
    medium: 0.6
    high: 0.8
    very_high: 0.9

  # 收益模型配置
  revenue_models:
    adsense:
      enabled: true
      min_traffic: 1000
      ctr_range: [0.1, 0.4]
    affiliate:
      enabled: true
      min_traffic: 500
      conversion_range: [0.01, 0.05]

# 过滤规则配置
filtering_rules:
  # 质量过滤器
  quality_filters:
    min_search_volume: 100
    min_trend_score: 0.1
    min_commercial_value: 0.2
    max_competition_score: 0.9

  # 内容过滤正则表达式
  content_filters:
    - '\\b(adult|porn|xxx)\\b'
    - '\\b(illegal|piracy|crack)\\b'

  # 重复检测规则
  deduplication_rules:
    similarity_threshold: 0.8
    levenshtein_threshold: 3
    enable_stemming: true

# 全局设置
global:
  enable_caching: true
  cache_ttl_minutes: 60
  max_batch_size: 100
"""

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(template_content)

            self.logger.info(f"规则配置模板导出成功: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"规则配置模板导出失败: {e}")
            return False