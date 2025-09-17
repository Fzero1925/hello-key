"""
算法配置管理器

负责加载、验证和管理各种分析算法的配置参数
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict, field


@dataclass
class ScoringConfig:
    """评分算法配置"""
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


@dataclass
class ValueEstimationConfig:
    """价值评估算法配置"""
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
class TrendAnalysisConfig:
    """趋势分析算法配置"""
    # 时间窗口设置
    short_window: int = 7
    long_window: int = 30
    trend_threshold: float = 0.1

    # 波动性阈值
    volatility_low: float = 0.1
    volatility_moderate: float = 0.3
    volatility_high: float = 0.5

    # 趋势强度阈值
    strength_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "very_weak": 0.05,
        "weak": 0.15,
        "moderate": 0.30,
        "strong": 0.50,
        "very_strong": 0.70
    })


@dataclass
class IntentDetectionConfig:
    """意图识别算法配置"""
    # 商业意图关键词
    commercial_keywords: list = field(default_factory=lambda: [
        'best', 'top', 'review', 'compare', 'vs', 'versus', 'price', 'cost',
        'cheap', 'expensive', 'budget', 'premium', 'quality', 'rating',
        'recommend', 'suggestion', 'advice', 'guide', 'buying', 'purchase',
        'deal', 'discount', 'sale', 'offer', 'coupon', 'promo'
    ])

    # 交易意图关键词
    transactional_keywords: list = field(default_factory=lambda: [
        'buy', 'purchase', 'order', 'shop', 'store', 'cart', 'checkout',
        'payment', 'shipping', 'delivery', 'install', 'download',
        'subscribe', 'sign up', 'register', 'book', 'reserve'
    ])

    # 信息意图关键词
    informational_keywords: list = field(default_factory=lambda: [
        'how', 'what', 'why', 'when', 'where', 'who', 'which',
        'tutorial', 'guide', 'learn', 'understand', 'explain',
        'definition', 'meaning', 'example', 'tips', 'tricks',
        'help', 'support', 'manual', 'instructions', 'steps'
    ])

    # 导航意图关键词
    navigational_keywords: list = field(default_factory=lambda: [
        'official', 'website', 'site', 'homepage', 'login', 'account',
        'dashboard', 'app', 'download', 'contact', 'support'
    ])

    # 本地意图关键词
    local_keywords: list = field(default_factory=lambda: [
        'near', 'nearby', 'local', 'around', 'close', 'location',
        'address', 'directions', 'map', 'hours', 'open', 'closed'
    ])

    # 品牌名称列表
    brand_names: list = field(default_factory=lambda: [
        'amazon', 'google', 'apple', 'microsoft', 'samsung', 'sony',
        'lg', 'philips', 'nest', 'ring', 'arlo', 'wyze', 'tp-link'
    ])

    # 意图权重
    intent_weights: Dict[str, float] = field(default_factory=lambda: {
        'commercial': 0.8,
        'transactional': 1.0,
        'informational': 0.4,
        'navigational': 0.2,
        'local': 0.7,
        'mixed': 0.6
    })


@dataclass
class AlgorithmConfiguration:
    """算法总配置"""
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    value_estimation: ValueEstimationConfig = field(default_factory=ValueEstimationConfig)
    trend_analysis: TrendAnalysisConfig = field(default_factory=TrendAnalysisConfig)
    intent_detection: IntentDetectionConfig = field(default_factory=IntentDetectionConfig)

    # 全局设置
    cache_enabled: bool = True
    debug_mode: bool = False
    log_level: str = "INFO"


class AlgorithmConfigManager:
    """
    算法配置管理器

    负责加载、验证、更新和保存算法配置
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = self._resolve_config_path(config_path)
        self.config: AlgorithmConfiguration = self._load_config()

    def _resolve_config_path(self, config_path: Optional[str]) -> str:
        """解析配置文件路径"""
        if config_path and os.path.exists(config_path):
            return config_path

        # 尝试默认路径
        default_paths = [
            "config/analysis_config.yml",
            "config/algorithm_config.yml",
            "analysis_config.yml",
            "algorithm_config.yml"
        ]

        for path in default_paths:
            if os.path.exists(path):
                return path

        # 如果没有找到配置文件，使用默认配置
        self.logger.warning("未找到算法配置文件，将使用默认配置")
        return None

    def _load_config(self) -> AlgorithmConfiguration:
        """加载配置"""
        if not self.config_path:
            self.logger.info("使用默认算法配置")
            return AlgorithmConfiguration()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)

            if not config_data:
                self.logger.warning("配置文件为空，使用默认配置")
                return AlgorithmConfiguration()

            # 解析配置数据
            config = AlgorithmConfiguration()

            # 加载评分配置
            if 'scoring' in config_data:
                config.scoring = self._parse_scoring_config(config_data['scoring'])

            # 加载价值评估配置
            if 'value_estimation' in config_data:
                config.value_estimation = self._parse_value_estimation_config(config_data['value_estimation'])

            # 加载趋势分析配置
            if 'trend_analysis' in config_data:
                config.trend_analysis = self._parse_trend_analysis_config(config_data['trend_analysis'])

            # 加载意图识别配置
            if 'intent_detection' in config_data:
                config.intent_detection = self._parse_intent_detection_config(config_data['intent_detection'])

            # 加载全局设置
            if 'global' in config_data:
                global_config = config_data['global']
                config.cache_enabled = global_config.get('cache_enabled', True)
                config.debug_mode = global_config.get('debug_mode', False)
                config.log_level = global_config.get('log_level', 'INFO')

            self.logger.info(f"算法配置加载成功: {self.config_path}")
            return config

        except Exception as e:
            self.logger.error(f"配置文件加载失败: {e}")
            self.logger.info("使用默认算法配置")
            return AlgorithmConfiguration()

    def _parse_scoring_config(self, data: Dict[str, Any]) -> ScoringConfig:
        """解析评分配置"""
        config = ScoringConfig()

        # 机会评分权重
        if 'opportunity_weights' in data:
            weights = data['opportunity_weights']
            config.trend_weight = weights.get('trend', config.trend_weight)
            config.intent_weight = weights.get('intent', config.intent_weight)
            config.search_volume_weight = weights.get('search_volume', config.search_volume_weight)
            config.freshness_weight = weights.get('freshness', config.freshness_weight)
            config.difficulty_penalty = weights.get('difficulty_penalty', config.difficulty_penalty)

        # AdSense参数
        if 'adsense' in data:
            adsense = data['adsense']
            config.adsense_ctr_serp = adsense.get('ctr_serp', config.adsense_ctr_serp)
            config.adsense_click_share_rank = adsense.get('click_share_rank', config.adsense_click_share_rank)
            config.adsense_rpm_usd = adsense.get('rpm_usd', config.adsense_rpm_usd)

        # Amazon参数
        if 'amazon' in data:
            amazon = data['amazon']
            config.amazon_ctr = amazon.get('ctr', config.amazon_ctr)
            config.amazon_conversion_rate = amazon.get('conversion_rate', config.amazon_conversion_rate)
            config.amazon_aov_usd = amazon.get('aov_usd', config.amazon_aov_usd)
            config.amazon_commission = amazon.get('commission', config.amazon_commission)

        return config

    def _parse_value_estimation_config(self, data: Dict[str, Any]) -> ValueEstimationConfig:
        """解析价值评估配置"""
        config = ValueEstimationConfig()

        # 直接映射字段
        field_mapping = {
            'adsense_ctr': 'adsense_ctr',
            'adsense_click_share': 'adsense_click_share',
            'adsense_rpm': 'adsense_rpm',
            'amazon_ctr': 'amazon_ctr',
            'amazon_conversion_rate': 'amazon_conversion_rate',
            'amazon_aov': 'amazon_aov',
            'amazon_commission': 'amazon_commission',
            'affiliate_ctr': 'affiliate_ctr',
            'affiliate_conversion_rate': 'affiliate_conversion_rate',
            'affiliate_commission_rate': 'affiliate_commission_rate',
            'affiliate_avg_sale': 'affiliate_avg_sale',
            'lead_ctr': 'lead_ctr',
            'lead_conversion_rate': 'lead_conversion_rate',
            'lead_value': 'lead_value',
            'market_volatility': 'market_volatility',
            'competition_factor': 'competition_factor',
            'seasonality_factor': 'seasonality_factor'
        }

        for yaml_key, config_attr in field_mapping.items():
            if yaml_key in data:
                setattr(config, config_attr, data[yaml_key])

        return config

    def _parse_trend_analysis_config(self, data: Dict[str, Any]) -> TrendAnalysisConfig:
        """解析趋势分析配置"""
        config = TrendAnalysisConfig()

        # 直接映射字段
        field_mapping = {
            'short_window': 'short_window',
            'long_window': 'long_window',
            'trend_threshold': 'trend_threshold',
            'volatility_low': 'volatility_low',
            'volatility_moderate': 'volatility_moderate',
            'volatility_high': 'volatility_high'
        }

        for yaml_key, config_attr in field_mapping.items():
            if yaml_key in data:
                setattr(config, config_attr, data[yaml_key])

        # 趋势强度阈值
        if 'strength_thresholds' in data:
            config.strength_thresholds.update(data['strength_thresholds'])

        return config

    def _parse_intent_detection_config(self, data: Dict[str, Any]) -> IntentDetectionConfig:
        """解析意图识别配置"""
        config = IntentDetectionConfig()

        # 关键词列表
        keyword_lists = [
            'commercial_keywords', 'transactional_keywords', 'informational_keywords',
            'navigational_keywords', 'local_keywords', 'brand_names'
        ]

        for keyword_list in keyword_lists:
            if keyword_list in data:
                setattr(config, keyword_list, data[keyword_list])

        # 意图权重
        if 'intent_weights' in data:
            config.intent_weights.update(data['intent_weights'])

        return config

    def get_scoring_config(self) -> ScoringConfig:
        """获取评分配置"""
        return self.config.scoring

    def get_value_estimation_config(self) -> ValueEstimationConfig:
        """获取价值评估配置"""
        return self.config.value_estimation

    def get_trend_analysis_config(self) -> TrendAnalysisConfig:
        """获取趋势分析配置"""
        return self.config.trend_analysis

    def get_intent_detection_config(self) -> IntentDetectionConfig:
        """获取意图识别配置"""
        return self.config.intent_detection

    def update_config(self, section: str, updates: Dict[str, Any]) -> bool:
        """
        更新配置

        Args:
            section: 配置节名称 ('scoring', 'value_estimation', 'trend_analysis', 'intent_detection')
            updates: 更新的配置项

        Returns:
            是否更新成功
        """
        try:
            if section == 'scoring':
                for key, value in updates.items():
                    if hasattr(self.config.scoring, key):
                        setattr(self.config.scoring, key, value)
            elif section == 'value_estimation':
                for key, value in updates.items():
                    if hasattr(self.config.value_estimation, key):
                        setattr(self.config.value_estimation, key, value)
            elif section == 'trend_analysis':
                for key, value in updates.items():
                    if hasattr(self.config.trend_analysis, key):
                        setattr(self.config.trend_analysis, key, value)
            elif section == 'intent_detection':
                for key, value in updates.items():
                    if hasattr(self.config.intent_detection, key):
                        setattr(self.config.intent_detection, key, value)
            else:
                self.logger.error(f"未知的配置节: {section}")
                return False

            self.logger.info(f"配置更新成功: {section}")
            return True

        except Exception as e:
            self.logger.error(f"配置更新失败: {e}")
            return False

    def save_config(self, output_path: Optional[str] = None) -> bool:
        """
        保存配置到文件

        Args:
            output_path: 输出文件路径，默认使用原路径

        Returns:
            是否保存成功
        """
        try:
            save_path = output_path or self.config_path or "algorithm_config.yml"

            # 确保输出目录存在
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)

            # 转换为字典格式
            config_dict = {
                'scoring': asdict(self.config.scoring),
                'value_estimation': asdict(self.config.value_estimation),
                'trend_analysis': asdict(self.config.trend_analysis),
                'intent_detection': asdict(self.config.intent_detection),
                'global': {
                    'cache_enabled': self.config.cache_enabled,
                    'debug_mode': self.config.debug_mode,
                    'log_level': self.config.log_level
                }
            }

            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True, indent=2)

            self.logger.info(f"配置保存成功: {save_path}")
            return True

        except Exception as e:
            self.logger.error(f"配置保存失败: {e}")
            return False

    def reset_to_defaults(self) -> bool:
        """重置为默认配置"""
        try:
            self.config = AlgorithmConfiguration()
            self.logger.info("配置已重置为默认值")
            return True
        except Exception as e:
            self.logger.error(f"配置重置失败: {e}")
            return False

    def validate_config(self) -> Dict[str, Any]:
        """
        验证配置有效性

        Returns:
            验证结果
        """
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': []
        }

        try:
            # 验证评分权重和为1
            scoring = self.config.scoring
            weight_sum = (scoring.trend_weight + scoring.intent_weight +
                         scoring.search_volume_weight + scoring.freshness_weight)

            if abs(weight_sum - 1.0) > 0.01:
                validation_result['warnings'].append(
                    f"评分权重和不为1.0: {weight_sum:.3f}"
                )

            # 验证百分比值在有效范围内
            percentage_fields = [
                ('scoring.difficulty_penalty', scoring.difficulty_penalty),
                ('value_estimation.market_volatility', self.config.value_estimation.market_volatility),
                ('trend_analysis.trend_threshold', self.config.trend_analysis.trend_threshold)
            ]

            for field_name, value in percentage_fields:
                if not 0 <= value <= 1:
                    validation_result['errors'].append(
                        f"{field_name} 值超出范围 [0, 1]: {value}"
                    )

            # 验证时间窗口合理性
            trend_config = self.config.trend_analysis
            if trend_config.short_window >= trend_config.long_window:
                validation_result['errors'].append(
                    f"短期窗口 ({trend_config.short_window}) 应小于长期窗口 ({trend_config.long_window})"
                )

            if validation_result['errors']:
                validation_result['valid'] = False

        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"配置验证失败: {e}")

        return validation_result

    def export_config_template(self, output_path: str = "algorithm_config_template.yml") -> bool:
        """
        导出配置模板

        Args:
            output_path: 输出路径

        Returns:
            是否导出成功
        """
        try:
            default_config = AlgorithmConfiguration()
            config_dict = asdict(default_config)

            # 添加注释信息
            template_content = """# 算法配置文件模板
#
# 这个文件包含了智能关键词分析工具中所有算法的配置参数
# 请根据实际需求调整参数值

# 评分算法配置
scoring:
  # 机会评分权重 (总和应为1.0)
  opportunity_weights:
    trend: 0.35           # 趋势权重
    intent: 0.30          # 意图权重
    search_volume: 0.15   # 搜索量权重
    freshness: 0.20       # 新鲜度权重
  difficulty_penalty: 0.6 # 难度惩罚系数

  # AdSense参数
  adsense:
    ctr_serp: 0.25        # SERP点击率
    click_share_rank: 0.35 # 排名点击份额
    rpm_usd: 10.0         # 千次展示收益

  # Amazon联盟参数
  amazon:
    ctr: 0.12             # 点击率
    conversion_rate: 0.04  # 转化率
    aov_usd: 80.0         # 平均订单价值
    commission: 0.03      # 佣金率

# 价值评估配置
value_estimation:
  # AdSense参数
  adsense_ctr: 0.25
  adsense_click_share: 0.35
  adsense_rpm: 10.0

  # Amazon联盟参数
  amazon_ctr: 0.12
  amazon_conversion_rate: 0.04
  amazon_aov: 80.0
  amazon_commission: 0.03

  # 联盟营销参数
  affiliate_ctr: 0.08
  affiliate_conversion_rate: 0.02
  affiliate_commission_rate: 0.05
  affiliate_avg_sale: 150.0

  # 潜在客户生成参数
  lead_ctr: 0.15
  lead_conversion_rate: 0.05
  lead_value: 25.0

  # 风险调整参数
  market_volatility: 0.2
  competition_factor: 0.3
  seasonality_factor: 0.15

# 趋势分析配置
trend_analysis:
  # 时间窗口 (天)
  short_window: 7
  long_window: 30
  trend_threshold: 0.1

  # 波动性阈值
  volatility_low: 0.1
  volatility_moderate: 0.3
  volatility_high: 0.5

  # 趋势强度阈值
  strength_thresholds:
    very_weak: 0.05
    weak: 0.15
    moderate: 0.30
    strong: 0.50
    very_strong: 0.70

# 意图识别配置
intent_detection:
  # 商业意图关键词
  commercial_keywords:
    - best
    - top
    - review
    - compare
    - price
    - cost
    - buying
    # ... 添加更多关键词

  # 交易意图关键词
  transactional_keywords:
    - buy
    - purchase
    - order
    - shop
    - cart
    # ... 添加更多关键词

  # 信息意图关键词
  informational_keywords:
    - how
    - what
    - why
    - tutorial
    - guide
    # ... 添加更多关键词

  # 意图权重
  intent_weights:
    commercial: 0.8
    transactional: 1.0
    informational: 0.4
    navigational: 0.2
    local: 0.7
    mixed: 0.6

# 全局设置
global:
  cache_enabled: true
  debug_mode: false
  log_level: INFO
"""

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(template_content)

            self.logger.info(f"配置模板导出成功: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"配置模板导出失败: {e}")
            return False