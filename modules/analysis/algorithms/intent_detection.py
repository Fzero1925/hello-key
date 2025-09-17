"""
意图识别算法

专门负责识别关键词的搜索意图，包括商业意图、信息意图、导航意图等
"""

import logging
import re
from typing import Dict, Any, Optional, List, Union, Set
from dataclasses import dataclass
from enum import Enum


class SearchIntent(Enum):
    """搜索意图类型"""
    COMMERCIAL = "commercial"          # 商业意图（购买、比较）
    INFORMATIONAL = "informational"    # 信息意图（学习、了解）
    NAVIGATIONAL = "navigational"      # 导航意图（寻找特定网站）
    TRANSACTIONAL = "transactional"    # 交易意图（立即购买）
    LOCAL = "local"                    # 本地意图（寻找本地服务）
    MIXED = "mixed"                    # 混合意图


@dataclass
class IntentConfig:
    """意图识别配置"""
    # 商业意图关键词
    commercial_keywords: Set[str] = None

    # 交易意图关键词
    transactional_keywords: Set[str] = None

    # 信息意图关键词
    informational_keywords: Set[str] = None

    # 导航意图关键词
    navigational_keywords: Set[str] = None

    # 本地意图关键词
    local_keywords: Set[str] = None

    # 品牌名称列表
    brand_names: Set[str] = None

    # 意图权重
    intent_weights: Dict[str, float] = None

    def __post_init__(self):
        if self.commercial_keywords is None:
            self.commercial_keywords = {
                'best', 'top', 'review', 'compare', 'vs', 'versus', 'price', 'cost',
                'cheap', 'expensive', 'budget', 'premium', 'quality', 'rating',
                'recommend', 'suggestion', 'advice', 'guide', 'buying', 'purchase',
                'deal', 'discount', 'sale', 'offer', 'coupon', 'promo'
            }

        if self.transactional_keywords is None:
            self.transactional_keywords = {
                'buy', 'purchase', 'order', 'shop', 'store', 'cart', 'checkout',
                'payment', 'shipping', 'delivery', 'install', 'download',
                'subscribe', 'sign up', 'register', 'book', 'reserve'
            }

        if self.informational_keywords is None:
            self.informational_keywords = {
                'how', 'what', 'why', 'when', 'where', 'who', 'which',
                'tutorial', 'guide', 'learn', 'understand', 'explain',
                'definition', 'meaning', 'example', 'tips', 'tricks',
                'help', 'support', 'manual', 'instructions', 'steps'
            }

        if self.navigational_keywords is None:
            self.navigational_keywords = {
                'official', 'website', 'site', 'homepage', 'login', 'account',
                'dashboard', 'app', 'download', 'contact', 'support'
            }

        if self.local_keywords is None:
            self.local_keywords = {
                'near', 'nearby', 'local', 'around', 'close', 'location',
                'address', 'directions', 'map', 'hours', 'open', 'closed'
            }

        if self.brand_names is None:
            self.brand_names = {
                'amazon', 'google', 'apple', 'microsoft', 'samsung', 'sony',
                'lg', 'philips', 'nest', 'ring', 'arlo', 'wyze', 'tp-link'
            }

        if self.intent_weights is None:
            self.intent_weights = {
                'commercial': 0.8,      # 高商业价值
                'transactional': 1.0,   # 最高商业价值
                'informational': 0.4,   # 中等商业价值
                'navigational': 0.2,    # 低商业价值
                'local': 0.7,          # 较高商业价值
                'mixed': 0.6           # 中等商业价值
            }


@dataclass
class IntentAnalysis:
    """意图分析结果"""
    primary_intent: SearchIntent
    intent_scores: Dict[str, float]
    commercial_value: float
    intent_confidence: float
    detected_patterns: List[str]
    brand_mentions: List[str]
    modifier_words: List[str]
    recommendations: List[str]


class IntentDetector:
    """
    意图识别引擎

    分析关键词的搜索意图和商业价值
    """

    def __init__(self, config: Optional[IntentConfig] = None):
        """
        初始化意图识别器

        Args:
            config: 意图识别配置
        """
        self.config = config or IntentConfig()
        self.logger = logging.getLogger(__name__)

    def analyze_intent(self, keyword: str) -> IntentAnalysis:
        """
        分析关键词意图

        Args:
            keyword: 待分析的关键词

        Returns:
            意图分析结果
        """
        try:
            # 预处理关键词
            normalized_keyword = self._normalize_keyword(keyword)
            words = normalized_keyword.split()

            # 计算各类意图得分
            intent_scores = self._calculate_intent_scores(words)

            # 确定主要意图
            primary_intent = self._determine_primary_intent(intent_scores)

            # 计算商业价值
            commercial_value = self._calculate_commercial_value(intent_scores, words)

            # 计算置信度
            intent_confidence = self._calculate_confidence(intent_scores)

            # 检测模式
            detected_patterns = self._detect_patterns(words)

            # 检测品牌提及
            brand_mentions = self._detect_brands(words)

            # 提取修饰词
            modifier_words = self._extract_modifiers(words)

            # 生成建议
            recommendations = self._generate_recommendations(
                primary_intent, commercial_value, detected_patterns
            )

            return IntentAnalysis(
                primary_intent=primary_intent,
                intent_scores=intent_scores,
                commercial_value=round(commercial_value, 2),
                intent_confidence=round(intent_confidence, 2),
                detected_patterns=detected_patterns,
                brand_mentions=brand_mentions,
                modifier_words=modifier_words,
                recommendations=recommendations
            )

        except Exception as e:
            self.logger.error(f"意图分析失败: {keyword}: {e}")
            return self._create_error_analysis(str(e))

    def _normalize_keyword(self, keyword: str) -> str:
        """规范化关键词"""
        # 转换为小写
        normalized = keyword.lower().strip()

        # 移除特殊字符，保留字母、数字和空格
        normalized = re.sub(r'[^\w\s-]', ' ', normalized)

        # 合并多个空格
        normalized = re.sub(r'\s+', ' ', normalized)

        return normalized

    def _calculate_intent_scores(self, words: List[str]) -> Dict[str, float]:
        """计算各类意图得分"""
        scores = {
            'commercial': 0,
            'transactional': 0,
            'informational': 0,
            'navigational': 0,
            'local': 0
        }

        total_words = len(words)
        if total_words == 0:
            return scores

        # 计算每种意图的匹配度
        for word in words:
            if word in self.config.commercial_keywords:
                scores['commercial'] += 1
            if word in self.config.transactional_keywords:
                scores['transactional'] += 1
            if word in self.config.informational_keywords:
                scores['informational'] += 1
            if word in self.config.navigational_keywords:
                scores['navigational'] += 1
            if word in self.config.local_keywords:
                scores['local'] += 1

        # 规范化得分（0-1）
        for intent in scores:
            scores[intent] = scores[intent] / total_words

        return scores

    def _determine_primary_intent(self, intent_scores: Dict[str, float]) -> SearchIntent:
        """确定主要意图"""
        # 找到得分最高的意图
        max_score = max(intent_scores.values())

        if max_score == 0:
            return SearchIntent.INFORMATIONAL  # 默认为信息意图

        # 获取得分最高的意图
        primary_intents = [intent for intent, score in intent_scores.items() if score == max_score]

        # 如果有多个相同得分的意图，按优先级选择
        intent_priority = {
            'transactional': 1,
            'commercial': 2,
            'local': 3,
            'informational': 4,
            'navigational': 5
        }

        selected_intent = min(primary_intents, key=lambda x: intent_priority.get(x, 6))

        # 检查是否为混合意图
        high_score_count = sum(1 for score in intent_scores.values() if score > 0.3)
        if high_score_count > 1:
            return SearchIntent.MIXED

        # 转换为枚举
        intent_mapping = {
            'commercial': SearchIntent.COMMERCIAL,
            'transactional': SearchIntent.TRANSACTIONAL,
            'informational': SearchIntent.INFORMATIONAL,
            'navigational': SearchIntent.NAVIGATIONAL,
            'local': SearchIntent.LOCAL
        }

        return intent_mapping.get(selected_intent, SearchIntent.INFORMATIONAL)

    def _calculate_commercial_value(self, intent_scores: Dict[str, float], words: List[str]) -> float:
        """计算商业价值 (0-1)"""
        # 基于意图权重计算基础商业价值
        base_value = sum(
            score * self.config.intent_weights.get(intent, 0)
            for intent, score in intent_scores.items()
        )

        # 品牌修正
        brand_modifier = 1.0
        for word in words:
            if word in self.config.brand_names:
                brand_modifier *= 1.2  # 品牌词提升商业价值

        # 修饰词修正
        modifier_boost = self._calculate_modifier_boost(words)

        # 最终商业价值
        commercial_value = base_value * brand_modifier * modifier_boost

        return min(1.0, commercial_value)

    def _calculate_confidence(self, intent_scores: Dict[str, float]) -> float:
        """计算意图识别置信度"""
        scores = list(intent_scores.values())

        if not scores:
            return 0

        max_score = max(scores)
        if max_score == 0:
            return 0.1

        # 计算得分分布的集中度
        score_variance = sum((score - max_score)**2 for score in scores) / len(scores)

        # 置信度与最高得分和分布集中度相关
        confidence = max_score * (1 - score_variance)

        return min(0.95, max(0.1, confidence))

    def _detect_patterns(self, words: List[str]) -> List[str]:
        """检测关键词模式"""
        patterns = []

        # 疑问词模式
        question_words = {'how', 'what', 'why', 'when', 'where', 'who', 'which'}
        if any(word in question_words for word in words):
            patterns.append("疑问句模式")

        # 比较模式
        comparison_words = {'vs', 'versus', 'compare', 'comparison', 'better', 'worse'}
        if any(word in comparison_words for word in words):
            patterns.append("比较模式")

        # 评价模式
        review_words = {'review', 'rating', 'stars', 'feedback', 'opinion'}
        if any(word in review_words for word in words):
            patterns.append("评价模式")

        # 购买意图模式
        buying_words = {'buy', 'purchase', 'price', 'cost', 'cheap', 'expensive'}
        if any(word in buying_words for word in words):
            patterns.append("购买意图模式")

        # 位置模式
        location_words = {'near', 'nearby', 'location', 'address', 'directions'}
        if any(word in location_words for word in words):
            patterns.append("位置查询模式")

        return patterns

    def _detect_brands(self, words: List[str]) -> List[str]:
        """检测品牌提及"""
        detected_brands = []

        for word in words:
            if word in self.config.brand_names:
                detected_brands.append(word.title())

        return detected_brands

    def _extract_modifiers(self, words: List[str]) -> List[str]:
        """提取修饰词"""
        modifiers = []

        modifier_words = {
            'best', 'top', 'good', 'great', 'excellent', 'amazing',
            'cheap', 'expensive', 'budget', 'premium', 'high-end',
            'new', 'latest', 'old', 'vintage', 'modern',
            'small', 'large', 'big', 'tiny', 'huge',
            'fast', 'slow', 'quick', 'instant'
        }

        for word in words:
            if word in modifier_words:
                modifiers.append(word)

        return modifiers

    def _calculate_modifier_boost(self, words: List[str]) -> float:
        """计算修饰词对商业价值的提升"""
        boost = 1.0

        # 高价值修饰词
        high_value_modifiers = {'best', 'top', 'premium', 'professional', 'advanced'}
        for word in words:
            if word in high_value_modifiers:
                boost *= 1.1

        # 购买意图修饰词
        buying_modifiers = {'buy', 'purchase', 'order', 'shop'}
        for word in words:
            if word in buying_modifiers:
                boost *= 1.15

        return min(1.5, boost)  # 最大1.5倍提升

    def _generate_recommendations(
        self,
        primary_intent: SearchIntent,
        commercial_value: float,
        patterns: List[str]
    ) -> List[str]:
        """生成优化建议"""
        recommendations = []

        # 基于主要意图的建议
        if primary_intent == SearchIntent.COMMERCIAL:
            recommendations.append("关键词具有强烈的商业意图，建议创建产品比较和评价内容")
        elif primary_intent == SearchIntent.TRANSACTIONAL:
            recommendations.append("关键词具有交易意图，建议优化产品页面和购买流程")
        elif primary_intent == SearchIntent.INFORMATIONAL:
            recommendations.append("关键词以信息查询为主，建议创建教程和指南内容")
        elif primary_intent == SearchIntent.LOCAL:
            recommendations.append("关键词具有本地查询意图，建议优化本地SEO")
        elif primary_intent == SearchIntent.NAVIGATIONAL:
            recommendations.append("关键词具有导航意图，建议优化品牌页面")

        # 基于商业价值的建议
        if commercial_value > 0.7:
            recommendations.append("商业价值高，建议优先投入资源开发")
        elif commercial_value > 0.4:
            recommendations.append("商业价值中等，可以考虑投入")
        else:
            recommendations.append("商业价值较低，建议作为流量入口使用")

        # 基于模式的建议
        if "比较模式" in patterns:
            recommendations.append("建议创建产品对比表格和详细比较内容")
        if "评价模式" in patterns:
            recommendations.append("建议收集和展示用户评价和评分")
        if "疑问句模式" in patterns:
            recommendations.append("建议采用FAQ格式回答相关问题")

        return recommendations

    def batch_analyze_intents(
        self,
        keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """批量分析关键词意图"""
        results = []

        for keyword in keywords:
            try:
                analysis = self.analyze_intent(keyword)

                result = {
                    'keyword': keyword,
                    'primary_intent': analysis.primary_intent.value,
                    'commercial_value': analysis.commercial_value,
                    'intent_confidence': analysis.intent_confidence,
                    'intent_scores': analysis.intent_scores,
                    'patterns': analysis.detected_patterns,
                    'brands': analysis.brand_mentions,
                    'modifiers': analysis.modifier_words,
                    'recommendations': analysis.recommendations[:3]  # 只保留前3个建议
                }

                results.append(result)

            except Exception as e:
                self.logger.error(f"批量意图分析失败: {keyword}: {e}")
                results.append({
                    'keyword': keyword,
                    'error': str(e),
                    'primary_intent': 'informational',
                    'commercial_value': 0,
                    'intent_confidence': 0
                })

        return results

    def _create_error_analysis(self, error_msg: str) -> IntentAnalysis:
        """创建错误情况下的默认分析结果"""
        return IntentAnalysis(
            primary_intent=SearchIntent.INFORMATIONAL,
            intent_scores={'commercial': 0, 'transactional': 0, 'informational': 0, 'navigational': 0, 'local': 0},
            commercial_value=0,
            intent_confidence=0,
            detected_patterns=[f"分析错误: {error_msg}"],
            brand_mentions=[],
            modifier_words=[],
            recommendations=["无法生成建议，请检查输入"]
        )