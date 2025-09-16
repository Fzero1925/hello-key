"""
Topic Analyzer - 专门负责话题分析
对获取到的话题进行商业价值评估、紧急度分析和策略建议
"""

import os
import sys
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple, Optional, Any
import logging
from dataclasses import dataclass, asdict
import random
import yaml

# 导入编码处理器
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
try:
    from modules.utils.encoding_handler import safe_print, get_encoding_handler
except ImportError:
    def safe_print(text, **kwargs):
        print(text, **kwargs)

# Import v2 scoring functions
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'keyword_tools'))
    from scoring import opportunity_score, estimate_value, estimate_adsense, estimate_amazon, make_revenue_range
except ImportError:
    # Fallback implementation
    def estimate_value(search_volume, opp, ads_params=None, aff_params=None, mode='max'):
        ads_params = ads_params or {"ctr_serp":0.25, "click_share_rank":0.35, "rpm_usd":10}
        aff_params = aff_params or {"ctr_to_amazon":0.12, "cr":0.04, "aov_usd":80, "commission":0.03}
        pv = search_volume * ads_params["ctr_serp"] * ads_params["click_share_rank"]
        ra = (pv/1000.0) * ads_params["rpm_usd"]
        rf = (search_volume*aff_params["ctr_to_amazon"])*aff_params["cr"]*aff_params["aov_usd"]*aff_params["commission"]
        base = max(ra, rf)
        return base * (0.6 + 0.4*opp/100.0)

    def make_revenue_range(v):
        return {"point": v, "range": f"${v*0.75:.0f}–${v*1.25:.0f}/mo"}


@dataclass
class TrendingTopic:
    """分析后的热点话题数据结构"""
    keyword: str
    category: str
    trend_score: float
    commercial_value: float
    search_volume_est: int
    competition_level: str
    urgency_score: float  # 紧急度评分（0-1）
    sources: List[str]
    time_detected: datetime
    peak_regions: List[str]
    related_terms: List[str]
    business_reasoning: str
    content_angle: str
    estimated_revenue: str
    social_signals: Dict[str, int]
    opportunity_score: Optional[float] = None


@dataclass
class MarketOpportunity:
    """市场机会分析"""
    keyword: str
    opportunity_score: float  # 0-1
    competition_gap: str
    revenue_potential: str
    time_sensitivity: str  # "URGENT", "HIGH", "MEDIUM", "LOW"
    recommended_action: str
    content_strategy: str


@dataclass
class TopicAnalysisResult:
    """话题分析结果"""
    trending_topics: List[TrendingTopic]
    market_opportunities: List[MarketOpportunity]
    analysis_summary: Dict[str, Any]
    recommendations: List[str]
    timestamp: datetime


class TopicAnalyzer:
    """
    话题分析器 - 专门负责话题价值评估和商业洞察
    不包含数据获取功能，专注于分析能力
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._get_default_config()
        self.logger = logging.getLogger(__name__)

        # Load v2 configuration
        self.v2_config = self._load_v2_config()

        # 商业意图关键词
        self.commercial_signals = [
            'best', 'review', 'buy', 'deal', 'sale', 'price', 'cheap',
            'discount', 'compare', 'vs', '2025', 'guide', 'how to choose'
        ]

        # 紧急度信号词
        self.urgency_signals = {
            'breaking': 1.0,
            'new': 0.9,
            'latest': 0.8,
            'trending': 0.9,
            'viral': 1.0,
            'hot': 0.8,
            'popular': 0.7,
            'rising': 0.8
        }

        # 智能家居类别关键词（用于分析）
        self.smart_home_categories = {
            'smart_plugs': ['smart plug', 'wifi outlet', 'alexa plug', 'smart switch'],
            'security_devices': ['security camera', 'video doorbell', 'smart lock', 'doorbell cam'],
            'cleaning_devices': ['robot vacuum', 'robotic cleaner', 'smart mop', 'pet hair vacuum'],
            'climate_control': ['smart thermostat', 'wifi thermostat', 'nest thermostat'],
            'lighting': ['smart bulb', 'color changing bulb', 'wifi light', 'smart dimmer'],
            'speakers_displays': ['smart speaker', 'alexa echo', 'google nest', 'smart display'],
            'emerging_categories': ['smart mirror', 'smart doorbell', 'smart garage door']
        }

    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            'min_commercial_value': 0.6,
            'min_urgency_score': 0.7,
            'min_trend_score': 0.5,
            'max_competition_level': 'Medium-High',
            'min_search_volume': 5000,
            'content_angle_preferences': ['best', 'review', 'guide', 'comparison'],
            'revenue_estimation_enabled': True,
            'market_opportunity_threshold': 0.75
        }

    def _load_v2_config(self) -> Dict:
        """Load Keyword Engine v2 configuration from YAML file"""
        config_path = "keyword_engine.yml"
        default_config = {
            "window_recent_ratio": 0.3,
            "thresholds": {"opportunity": 70, "search_volume": 10000, "urgency": 0.8},
            "weights": {"T": 0.35, "I": 0.30, "S": 0.15, "F": 0.20, "D_penalty": 0.6},
            "adsense": {"ctr_serp": 0.25, "click_share_rank": 0.35, "rpm_usd": 10},
            "amazon": {"ctr_to_amazon": 0.12, "cr": 0.04, "aov_usd": 80, "commission": 0.03},
            "mode": "max"
        }

        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                        elif isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                if subkey not in config[key]:
                                    config[key][subkey] = subvalue
                    return config
        except Exception as e:
            self.logger.warning(f"Could not load v2 config: {e}, using defaults")

        return default_config

    def analyze_topics(self, raw_topics: List[Dict]) -> TopicAnalysisResult:
        """
        分析原始话题数据，生成完整的分析结果

        Args:
            raw_topics: 从TopicFetcher获取的原始话题数据

        Returns:
            完整的话题分析结果
        """
        trending_topics = []

        for topic_data in raw_topics:
            # 检查是否与智能家居相关
            if not self._is_smart_home_related(topic_data.get('keyword', '')):
                continue

            analyzed_topic = self._analyze_single_topic(topic_data)
            if analyzed_topic:
                trending_topics.append(analyzed_topic)

        # 去重和排序
        trending_topics = self._deduplicate_and_rank(trending_topics)

        # 生成市场机会分析
        market_opportunities = self.generate_market_opportunities(trending_topics)

        # 生成分析摘要
        analysis_summary = self._generate_analysis_summary(trending_topics, market_opportunities)

        # 生成推荐建议
        recommendations = self._generate_recommendations(trending_topics, market_opportunities)

        return TopicAnalysisResult(
            trending_topics=trending_topics,
            market_opportunities=market_opportunities,
            analysis_summary=analysis_summary,
            recommendations=recommendations,
            timestamp=datetime.now(timezone.utc)
        )

    def _analyze_single_topic(self, topic_data: Dict) -> Optional[TrendingTopic]:
        """分析单个话题"""
        try:
            keyword = topic_data.get('keyword', '').strip()
            if not keyword:
                return None

            # 基础分析
            category = self._categorize_keyword(keyword)
            commercial_value = self._calculate_commercial_value(keyword)
            urgency_score = self._calculate_urgency(topic_data)
            trend_score = self._extract_trend_score(topic_data)
            search_volume_est = self._estimate_search_volume(keyword, topic_data)
            competition_level = self._estimate_competition_level(keyword)

            # 检查最小阈值
            if (commercial_value < self.config['min_commercial_value'] or
                urgency_score < self.config['min_urgency_score'] or
                trend_score < self.config['min_trend_score']):
                return None

            # 生成商业洞察
            business_reasoning = self._generate_business_reasoning(topic_data)
            content_angle = self._suggest_content_angle(keyword)
            estimated_revenue = self._estimate_revenue_potential(topic_data)

            # 提取相关信息
            sources = self._extract_sources(topic_data)
            related_terms = self._extract_related_terms(topic_data)
            social_signals = self._extract_social_signals(topic_data)
            peak_regions = topic_data.get('peak_regions', ['US'])

            # 计算v2机会评分
            opportunity_score_v2 = self._calculate_v2_opportunity_score(
                keyword, trend_score, commercial_value, competition_level
            )

            return TrendingTopic(
                keyword=keyword,
                category=category,
                trend_score=trend_score,
                commercial_value=commercial_value,
                search_volume_est=search_volume_est,
                competition_level=competition_level,
                urgency_score=urgency_score,
                sources=sources,
                time_detected=topic_data.get('timestamp', datetime.now(timezone.utc)),
                peak_regions=peak_regions,
                related_terms=related_terms,
                business_reasoning=business_reasoning,
                content_angle=content_angle,
                estimated_revenue=estimated_revenue,
                social_signals=social_signals,
                opportunity_score=opportunity_score_v2
            )

        except Exception as e:
            self.logger.warning(f"Failed to analyze topic {topic_data.get('keyword', 'unknown')}: {e}")
            return None

    def _is_smart_home_related(self, text: str) -> bool:
        """检查文本是否与智能家居相关"""
        text_lower = text.lower()

        # 智能家居核心词汇
        smart_home_terms = [
            'smart', 'wifi', 'bluetooth', 'alexa', 'google', 'home', 'automation',
            'iot', 'connected', 'wireless', 'app', 'control', 'remote', 'voice'
        ]

        # 产品术语
        product_terms = [
            'plug', 'outlet', 'bulb', 'light', 'camera', 'doorbell', 'lock',
            'thermostat', 'vacuum', 'robot', 'speaker', 'display', 'hub',
            'sensor', 'switch', 'dimmer', 'security', 'alarm'
        ]

        # 检查是否包含相关术语
        return (any(term in text_lower for term in smart_home_terms) or
                any(term in text_lower for term in product_terms))

    def _categorize_keyword(self, keyword: str) -> str:
        """分类关键词"""
        keyword_lower = keyword.lower()

        for category, terms in self.smart_home_categories.items():
            if any(term in keyword_lower for term in terms):
                return category

        return 'general'

    def _calculate_commercial_value(self, keyword: str) -> float:
        """计算商业价值评分"""
        keyword_lower = keyword.lower()
        commercial_score = 0.0

        # 强商业意图词汇
        strong_signals = ['buy', 'price', 'deal', 'sale', 'cheap', 'discount']
        for signal in strong_signals:
            if signal in keyword_lower:
                commercial_score += 0.3

        # 中等商业意图词汇
        medium_signals = ['best', 'review', 'compare', 'vs', 'guide', '2025']
        for signal in medium_signals:
            if signal in keyword_lower:
                commercial_score += 0.2

        # 产品相关词汇
        if any(term in keyword_lower for term in ['smart', 'wifi', 'bluetooth']):
            commercial_score += 0.1

        return min(1.0, commercial_score)

    def _calculate_urgency(self, topic_data: Dict) -> float:
        """计算紧急度评分"""
        urgency = 0.0

        # 检查标题中的紧急度信号
        text = f"{topic_data.get('keyword', '')} {topic_data.get('title', '')}".lower()

        for signal, score in self.urgency_signals.items():
            if signal in text:
                urgency = max(urgency, score)

        # 基于数据源的紧急度调整
        source = topic_data.get('source', '')
        if 'spike' in source:
            urgency += 0.3
        elif 'trending' in source:
            urgency += 0.2
        elif 'social' in source:
            urgency += 0.1

        # 基于时间的紧急度
        timestamp = topic_data.get('timestamp')
        if timestamp:
            hours_ago = (datetime.now(timezone.utc) - timestamp).total_seconds() / 3600
            if hours_ago < 6:  # 6小时内
                urgency += 0.2
            elif hours_ago < 24:  # 24小时内
                urgency += 0.1

        return min(1.0, urgency)

    def _extract_trend_score(self, topic_data: Dict) -> float:
        """提取趋势评分"""
        # 从各种字段中提取趋势评分
        if 'trend_score' in topic_data:
            return float(topic_data['trend_score'])

        # 基于其他指标计算
        score = 0.5  # 默认值

        # 基于Google Trends数据
        if 'current_interest' in topic_data:
            interest = topic_data['current_interest']
            score = min(1.0, interest / 100.0)

        # 基于社交媒体数据
        elif 'score' in topic_data:  # Reddit score
            reddit_score = topic_data['score']
            score = min(1.0, reddit_score / 1000.0)

        elif 'views' in topic_data:  # YouTube views
            views = topic_data['views']
            score = min(1.0, views / 100000.0)

        return score

    def _estimate_search_volume(self, keyword: str, topic_data: Dict) -> int:
        """估算搜索量"""
        base_volume = 10000  # 基础搜索量

        # 基于关键词长度调整
        word_count = len(keyword.split())
        if word_count == 1:
            base_volume *= 2  # 单词搜索量更高
        elif word_count > 4:
            base_volume *= 0.5  # 长尾关键词搜索量较低

        # 基于商业意图调整
        commercial_value = self._calculate_commercial_value(keyword)
        base_volume = int(base_volume * (1 + commercial_value))

        # 基于数据源的调整
        source = topic_data.get('source', '')
        if 'google_trends' in source:
            interest = topic_data.get('current_interest', 0)
            base_volume = int(base_volume * (interest / 50.0 + 0.5))
        elif 'reddit' in source:
            score = topic_data.get('score', 0)
            base_volume = int(base_volume * (score / 500.0 + 0.5))

        return max(1000, base_volume)

    def _estimate_competition_level(self, keyword: str) -> str:
        """估算竞争等级"""
        keyword_lower = keyword.lower()

        # 高竞争指标
        high_comp_signals = ['best', 'top', 'review', 'vs']
        medium_comp_signals = ['guide', 'how to', '2025']

        high_count = sum(1 for signal in high_comp_signals if signal in keyword_lower)
        medium_count = sum(1 for signal in medium_comp_signals if signal in keyword_lower)

        if high_count >= 2:
            return 'High'
        elif high_count >= 1 or medium_count >= 2:
            return 'Medium-High'
        elif medium_count >= 1:
            return 'Medium'
        else:
            return 'Low-Medium'

    def _generate_business_reasoning(self, topic_data: Dict) -> str:
        """生成商业推理"""
        keyword = topic_data.get('keyword', '')
        source = topic_data.get('source', '')

        reasons = []

        # 基于数据源的推理
        if 'google_trends' in source:
            interest = topic_data.get('current_interest', 0)
            if interest > 50:
                reasons.append(f"Google搜索兴趣度达到{interest}，显示强烈的用户需求")

        elif 'reddit' in source:
            score = topic_data.get('score', 0)
            comments = topic_data.get('comments', 0)
            if score > 100:
                reasons.append(f"Reddit讨论活跃度高({score}点赞，{comments}评论)，用户参与度强")

        elif 'youtube' in source:
            views = topic_data.get('views', 0)
            if views > 50000:
                reasons.append(f"YouTube视频观看量达到{views:,}，视频内容需求旺盛")

        # 基于关键词特征的推理
        if any(signal in keyword.lower() for signal in ['best', 'review', 'guide']):
            reasons.append("包含购买意图关键词，商业转化潜力高")

        if not reasons:
            reasons.append("基于多数据源验证的热门话题，具有商业开发价值")

        return "; ".join(reasons)

    def _suggest_content_angle(self, keyword: str) -> str:
        """建议内容角度"""
        keyword_lower = keyword.lower()

        # 基于关键词特征建议角度
        if 'best' in keyword_lower:
            return 'product_roundup'
        elif 'review' in keyword_lower:
            return 'detailed_review'
        elif 'vs' in keyword_lower or 'compare' in keyword_lower:
            return 'comparison'
        elif 'guide' in keyword_lower or 'how to' in keyword_lower:
            return 'tutorial_guide'
        elif '2025' in keyword_lower:
            return 'annual_roundup'
        else:
            # 根据产品类型建议
            if any(term in keyword_lower for term in ['plug', 'outlet', 'switch']):
                return 'setup_guide'
            elif any(term in keyword_lower for term in ['camera', 'security', 'doorbell']):
                return 'security_focus'
            elif any(term in keyword_lower for term in ['vacuum', 'robot', 'clean']):
                return 'performance_test'
            else:
                return 'comprehensive_review'

    def _estimate_revenue_potential(self, topic_data: Dict) -> str:
        """估算收益潜力"""
        if not self.config.get('revenue_estimation_enabled', True):
            return "Revenue estimation disabled"

        try:
            keyword = topic_data.get('keyword', '')
            search_volume = self._estimate_search_volume(keyword, topic_data)
            commercial_value = self._calculate_commercial_value(keyword)

            # 使用v2评分系统估算收益
            opp_score = commercial_value * 100  # 转换为0-100范围
            estimated_revenue = estimate_value(
                search_volume=search_volume,
                opp=opp_score,
                ads_params=self.v2_config.get('adsense'),
                aff_params=self.v2_config.get('amazon'),
                mode=self.v2_config.get('mode', 'max')
            )

            revenue_range = make_revenue_range(estimated_revenue)
            return revenue_range['range']

        except Exception as e:
            self.logger.warning(f"Revenue estimation failed: {e}")
            return "Unable to estimate"

    def _extract_sources(self, topic_data: Dict) -> List[str]:
        """提取数据源"""
        sources = []
        source = topic_data.get('source', '')
        if source:
            sources.append(source)

        # 检查是否有多个来源
        if 'sources' in topic_data:
            additional_sources = topic_data['sources']
            if isinstance(additional_sources, list):
                sources.extend(additional_sources)
            else:
                sources.append(str(additional_sources))

        return list(set(sources))  # 去重

    def _extract_related_terms(self, topic_data: Dict) -> List[str]:
        """提取相关词汇"""
        related_terms = []

        # 从标题中提取
        title = topic_data.get('title', '')
        if title:
            words = title.lower().split()
            related_terms.extend([word for word in words if len(word) > 3])

        # 从其他字段提取
        if 'related_terms' in topic_data:
            related_terms.extend(topic_data['related_terms'])

        return list(set(related_terms[:10]))  # 限制数量并去重

    def _extract_social_signals(self, topic_data: Dict) -> Dict[str, int]:
        """提取社交信号"""
        signals = {}

        # Reddit信号
        if 'score' in topic_data:
            signals['reddit_score'] = topic_data['score']
        if 'comments' in topic_data:
            signals['reddit_comments'] = topic_data['comments']

        # YouTube信号
        if 'views' in topic_data:
            signals['youtube_views'] = topic_data['views']
        if 'likes' in topic_data:
            signals['youtube_likes'] = topic_data['likes']

        # 其他社交信号
        if 'mentions' in topic_data:
            signals['social_mentions'] = topic_data['mentions']

        return signals

    def _calculate_v2_opportunity_score(self, keyword: str, trend_score: float,
                                      commercial_value: float, competition_level: str) -> float:
        """使用v2算法计算机会评分"""
        try:
            # 转换参数为v2格式
            T = trend_score  # 趋势评分 (0-1)
            I = commercial_value  # 商业意图 (0-1)
            S = 0.5  # 季节性评分（中性）
            F = 0.8  # 网站适合度（假设较高）

            # 竞争度映射
            competition_map = {
                'Low': 0.2,
                'Low-Medium': 0.3,
                'Medium': 0.5,
                'Medium-High': 0.7,
                'High': 0.9
            }
            D = competition_map.get(competition_level, 0.5)

            # 使用v2权重计算
            weights = self.v2_config.get('weights', {})
            d_penalty = weights.get('D_penalty', 0.6)

            base_score = (weights.get('T', 0.35) * T +
                         weights.get('I', 0.30) * I +
                         weights.get('S', 0.15) * S +
                         weights.get('F', 0.20) * F)

            final_score = 100 * base_score * (1 - d_penalty * D)
            return max(0.0, min(100.0, final_score))

        except Exception as e:
            self.logger.warning(f"V2 opportunity score calculation failed: {e}")
            return 50.0  # 默认中性评分

    def _deduplicate_and_rank(self, topics: List[TrendingTopic]) -> List[TrendingTopic]:
        """去重和排序话题"""
        # 按关键词去重
        unique_topics = {}
        for topic in topics:
            key = topic.keyword.lower().strip()
            if key not in unique_topics or topic.urgency_score > unique_topics[key].urgency_score:
                unique_topics[key] = topic

        # 按综合评分排序
        sorted_topics = sorted(
            unique_topics.values(),
            key=lambda t: (t.urgency_score * 0.4 + t.commercial_value * 0.3 + t.trend_score * 0.3),
            reverse=True
        )

        return sorted_topics

    def generate_market_opportunities(self, trending_topics: List[TrendingTopic]) -> List[MarketOpportunity]:
        """生成市场机会分析"""
        opportunities = []

        for topic in trending_topics:
            # 只分析高价值话题
            combined_score = (topic.urgency_score * 0.4 +
                            topic.commercial_value * 0.3 +
                            topic.trend_score * 0.3)

            if combined_score >= self.config.get('market_opportunity_threshold', 0.75):
                opportunity = MarketOpportunity(
                    keyword=topic.keyword,
                    opportunity_score=combined_score,
                    competition_gap=self._analyze_competition_gap(topic),
                    revenue_potential=topic.estimated_revenue,
                    time_sensitivity=self._determine_time_sensitivity(topic),
                    recommended_action=self._recommend_action(topic),
                    content_strategy=self._suggest_content_strategy(topic)
                )
                opportunities.append(opportunity)

        return sorted(opportunities, key=lambda o: o.opportunity_score, reverse=True)

    def _analyze_competition_gap(self, topic: TrendingTopic) -> str:
        """分析竞争缺口"""
        if topic.competition_level in ['Low', 'Low-Medium']:
            return "竞争较少，存在明显市场缺口"
        elif topic.competition_level == 'Medium':
            return "适中竞争，有差异化机会"
        else:
            return "竞争激烈，需要独特角度切入"

    def _determine_time_sensitivity(self, topic: TrendingTopic) -> str:
        """确定时间敏感性"""
        if topic.urgency_score >= 0.9:
            return "URGENT"
        elif topic.urgency_score >= 0.8:
            return "HIGH"
        elif topic.urgency_score >= 0.6:
            return "MEDIUM"
        else:
            return "LOW"

    def _recommend_action(self, topic: TrendingTopic) -> str:
        """推荐行动方案"""
        if topic.urgency_score >= 0.8 and topic.commercial_value >= 0.7:
            return "立即创建内容，抢占流量窗口"
        elif topic.commercial_value >= 0.8:
            return "优先创建转化导向的内容"
        elif topic.trend_score >= 0.8:
            return "创建趋势相关内容，建立话题权威"
        else:
            return "监控发展，寻找最佳切入时机"

    def _suggest_content_strategy(self, topic: TrendingTopic) -> str:
        """建议内容策略"""
        strategies = []

        if topic.content_angle == 'product_roundup':
            strategies.append("制作综合产品对比内容")
        elif topic.content_angle == 'detailed_review':
            strategies.append("深度评测单一产品")
        elif topic.content_angle == 'comparison':
            strategies.append("对比分析不同产品")

        if topic.commercial_value >= 0.8:
            strategies.append("优化购买转化路径")

        if topic.urgency_score >= 0.8:
            strategies.append("快速发布抢占先机")

        return "; ".join(strategies) if strategies else "标准内容策略"

    def _generate_analysis_summary(self, trending_topics: List[TrendingTopic],
                                 opportunities: List[MarketOpportunity]) -> Dict[str, Any]:
        """生成分析摘要"""
        if not trending_topics:
            return {
                'total_topics': 0,
                'high_value_topics': 0,
                'avg_commercial_value': 0,
                'avg_urgency_score': 0,
                'top_categories': [],
                'market_opportunities': 0
            }

        return {
            'total_topics': len(trending_topics),
            'high_value_topics': len([t for t in trending_topics if t.commercial_value >= 0.7]),
            'avg_commercial_value': sum(t.commercial_value for t in trending_topics) / len(trending_topics),
            'avg_urgency_score': sum(t.urgency_score for t in trending_topics) / len(trending_topics),
            'top_categories': self._get_top_categories(trending_topics),
            'market_opportunities': len(opportunities),
            'urgent_topics': len([t for t in trending_topics if t.urgency_score >= 0.8]),
            'revenue_range': self._calculate_total_revenue_range(trending_topics)
        }

    def _generate_recommendations(self, trending_topics: List[TrendingTopic],
                                opportunities: List[MarketOpportunity]) -> List[str]:
        """生成推荐建议"""
        recommendations = []

        if not trending_topics:
            recommendations.append("当前没有发现高价值话题，建议扩大监控范围")
            return recommendations

        # 基于紧急话题的建议
        urgent_topics = [t for t in trending_topics if t.urgency_score >= 0.8]
        if urgent_topics:
            recommendations.append(f"发现{len(urgent_topics)}个紧急话题，建议立即行动")

        # 基于商业价值的建议
        high_commercial = [t for t in trending_topics if t.commercial_value >= 0.8]
        if high_commercial:
            recommendations.append(f"{len(high_commercial)}个高商业价值话题值得优先投入")

        # 基于竞争情况的建议
        low_competition = [t for t in trending_topics if t.competition_level in ['Low', 'Low-Medium']]
        if low_competition:
            recommendations.append(f"{len(low_competition)}个低竞争话题存在快速获得排名的机会")

        return recommendations

    def _get_top_categories(self, topics: List[TrendingTopic]) -> List[Dict[str, Any]]:
        """获取热门类别"""
        category_counts = {}
        for topic in topics:
            category_counts[topic.category] = category_counts.get(topic.category, 0) + 1

        return [
            {'category': cat, 'count': count}
            for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

    def _calculate_total_revenue_range(self, topics: List[TrendingTopic]) -> str:
        """计算总收益范围"""
        try:
            total_min = 0
            total_max = 0

            for topic in topics[:10]:  # 取前10个话题
                revenue_str = topic.estimated_revenue
                if '$' in revenue_str and '–' in revenue_str:
                    parts = revenue_str.replace('$', '').replace('/mo', '').split('–')
                    if len(parts) == 2:
                        total_min += int(parts[0])
                        total_max += int(parts[1])

            if total_min > 0 and total_max > 0:
                return f"${total_min:,}–${total_max:,}/mo"
            else:
                return "无法估算"

        except Exception as e:
            self.logger.warning(f"Revenue range calculation failed: {e}")
            return "估算出错"

    def export_analysis_report(self, analysis_result: TopicAnalysisResult,
                             output_file: str = None) -> str:
        """导出分析报告"""
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            output_file = f"data/topic_analysis_{timestamp}.json"

        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            # 转换为可序列化的格式
            report_data = {
                'analysis_summary': analysis_result.analysis_summary,
                'recommendations': analysis_result.recommendations,
                'trending_topics': [asdict(topic) for topic in analysis_result.trending_topics],
                'market_opportunities': [asdict(opp) for opp in analysis_result.market_opportunities],
                'timestamp': analysis_result.timestamp.isoformat(),
                'total_topics_analyzed': len(analysis_result.trending_topics)
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)

            self.logger.info(f"Analysis report exported to: {output_file}")
            return output_file

        except Exception as e:
            self.logger.error(f"Failed to export analysis report: {e}")
            return ""


# 示例使用
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO)

    # 创建话题分析器
    analyzer = TopicAnalyzer()

    safe_print("=== 话题分析器测试 ===")

    # 模拟原始话题数据（通常来自TopicFetcher）
    raw_topics = [
        {
            'keyword': 'best smart plug alexa 2025',
            'category': 'smart_plugs',
            'source': 'google_trends',
            'current_interest': 75,
            'timestamp': datetime.now(timezone.utc)
        },
        {
            'keyword': 'robot vacuum pet hair mapping',
            'category': 'cleaning_devices',
            'source': 'reddit',
            'score': 350,
            'comments': 45,
            'timestamp': datetime.now(timezone.utc)
        },
        {
            'keyword': 'wireless security camera outdoor',
            'category': 'security_devices',
            'source': 'youtube',
            'views': 125000,
            'likes': 2500,
            'timestamp': datetime.now(timezone.utc)
        }
    ]

    safe_print(f"\n分析 {len(raw_topics)} 个原始话题...")
    analysis_result = analyzer.analyze_topics(raw_topics)

    safe_print(f"\n=== 分析结果 ===")
    safe_print(f"热门话题数量: {len(analysis_result.trending_topics)}")
    safe_print(f"市场机会数量: {len(analysis_result.market_opportunities)}")

    safe_print(f"\n=== 热门话题 ===")
    for topic in analysis_result.trending_topics:
        safe_print(f"话题: {topic.keyword}")
        safe_print(f"  类别: {topic.category}")
        safe_print(f"  商业价值: {topic.commercial_value:.2f}")
        safe_print(f"  紧急度: {topic.urgency_score:.2f}")
        safe_print(f"  预估收益: {topic.estimated_revenue}")
        safe_print(f"  推荐角度: {topic.content_angle}")
        safe_print(f"  机会评分: {topic.opportunity_score:.1f}")
        safe_print()

    safe_print(f"\n=== 推荐建议 ===")
    for recommendation in analysis_result.recommendations:
        safe_print(f"- {recommendation}")

    # 导出报告
    safe_print(f"\n导出分析报告...")
    report_file = analyzer.export_analysis_report(analysis_result)
    safe_print(f"报告已导出到: {report_file}")

    safe_print(f"\n分析完成！此模块专注于话题价值评估和策略建议。")