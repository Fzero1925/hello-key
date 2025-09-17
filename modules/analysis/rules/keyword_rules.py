"""
关键词规则引擎

基于配置化规则处理关键词的分类、过滤、质量评估等业务逻辑
"""

import re
import logging
from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from ..config.rules_config import RulesConfigManager, KeywordRulesConfig


class KeywordQuality(Enum):
    """关键词质量等级"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    INVALID = "invalid"


@dataclass
class KeywordAnalysisResult:
    """关键词分析结果"""
    keyword: str
    category: str
    quality: KeywordQuality
    commercial_intent_score: float
    quality_modifier: float
    detected_patterns: List[str]
    exclusion_reasons: List[str]
    recommendations: List[str]
    is_valid: bool


class KeywordRuleEngine:
    """
    关键词规则引擎

    提供基于规则的关键词分析、分类和质量评估
    """

    def __init__(self, rules_config: Optional[KeywordRulesConfig] = None):
        """
        初始化关键词规则引擎

        Args:
            rules_config: 关键词规则配置，如果为None则从配置管理器加载
        """
        self.logger = logging.getLogger(__name__)

        if rules_config:
            self.rules = rules_config
        else:
            # 从配置管理器加载
            config_manager = RulesConfigManager()
            self.rules = config_manager.get_keyword_rules()

        # 编译正则表达式模式以提高性能
        self._compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """编译正则表达式模式"""
        compiled = {}

        pattern_types = ['commercial_patterns', 'informational_patterns', 'transactional_patterns']

        for pattern_type in pattern_types:
            patterns = getattr(self.rules, pattern_type, [])
            compiled[pattern_type] = []

            for pattern in patterns:
                try:
                    compiled_pattern = re.compile(pattern, re.IGNORECASE)
                    compiled[pattern_type].append(compiled_pattern)
                except re.error as e:
                    self.logger.warning(f"无效的正则表达式模式 {pattern}: {e}")

        return compiled

    def analyze_keyword(self, keyword: str) -> KeywordAnalysisResult:
        """
        分析单个关键词

        Args:
            keyword: 待分析的关键词

        Returns:
            关键词分析结果
        """
        try:
            # 基础验证
            is_valid, exclusion_reasons = self._validate_keyword(keyword)

            if not is_valid:
                return KeywordAnalysisResult(
                    keyword=keyword,
                    category="invalid",
                    quality=KeywordQuality.INVALID,
                    commercial_intent_score=0.0,
                    quality_modifier=0.0,
                    detected_patterns=[],
                    exclusion_reasons=exclusion_reasons,
                    recommendations=["关键词不符合基本要求"],
                    is_valid=False
                )

            # 分类识别
            category = self._classify_keyword(keyword)

            # 意图检测
            commercial_intent_score, detected_patterns = self._detect_commercial_intent(keyword)

            # 质量评估
            quality = self._assess_quality(keyword, commercial_intent_score)

            # 质量修饰符
            quality_modifier = self._calculate_quality_modifier(keyword)

            # 生成建议
            recommendations = self._generate_recommendations(
                keyword, category, quality, commercial_intent_score
            )

            return KeywordAnalysisResult(
                keyword=keyword,
                category=category,
                quality=quality,
                commercial_intent_score=commercial_intent_score,
                quality_modifier=quality_modifier,
                detected_patterns=detected_patterns,
                exclusion_reasons=[],
                recommendations=recommendations,
                is_valid=True
            )

        except Exception as e:
            self.logger.error(f"关键词分析失败 {keyword}: {e}")
            return KeywordAnalysisResult(
                keyword=keyword,
                category="unknown",
                quality=KeywordQuality.INVALID,
                commercial_intent_score=0.0,
                quality_modifier=0.0,
                detected_patterns=[],
                exclusion_reasons=[f"分析错误: {str(e)}"],
                recommendations=[],
                is_valid=False
            )

    def _validate_keyword(self, keyword: str) -> Tuple[bool, List[str]]:
        """验证关键词是否符合基本要求"""
        exclusion_reasons = []

        # 长度检查
        if len(keyword) < self.rules.min_keyword_length:
            exclusion_reasons.append(f"关键词长度小于{self.rules.min_keyword_length}")

        if len(keyword) > self.rules.max_keyword_length:
            exclusion_reasons.append(f"关键词长度大于{self.rules.max_keyword_length}")

        # 排除关键词检查
        keyword_lower = keyword.lower()
        for excluded in self.rules.excluded_keywords:
            if excluded.lower() in keyword_lower:
                exclusion_reasons.append(f"包含排除关键词: {excluded}")

        # 基本格式检查
        if not keyword.strip():
            exclusion_reasons.append("关键词为空")

        # 特殊字符检查
        if re.search(r'[^\w\s\-\'\"&.,!?]', keyword):
            exclusion_reasons.append("包含非法特殊字符")

        return len(exclusion_reasons) == 0, exclusion_reasons

    def _classify_keyword(self, keyword: str) -> str:
        """对关键词进行分类"""
        keyword_lower = keyword.lower()

        # 遍历分类映射规则
        for category, keywords in self.rules.category_mappings.items():
            for category_keyword in keywords:
                if category_keyword.lower() in keyword_lower:
                    return category

        # 如果没有匹配到特定分类，返回通用分类
        return "general"

    def _detect_commercial_intent(self, keyword: str) -> Tuple[float, List[str]]:
        """检测商业意图"""
        detected_patterns = []
        intent_scores = {
            'commercial': 0,
            'informational': 0,
            'transactional': 0
        }

        # 检测各种意图模式
        for intent_type, compiled_patterns in self._compiled_patterns.items():
            intent_name = intent_type.replace('_patterns', '')

            for pattern in compiled_patterns:
                matches = pattern.findall(keyword)
                if matches:
                    intent_scores[intent_name] += len(matches)
                    detected_patterns.extend([f"{intent_name}:{match}" for match in matches])

        # 计算商业意图得分
        total_matches = sum(intent_scores.values())
        if total_matches == 0:
            return 0.0, detected_patterns

        # 商业意图和交易意图的权重更高
        commercial_score = (
            intent_scores['commercial'] * 0.8 +
            intent_scores['transactional'] * 1.0 +
            intent_scores['informational'] * 0.3
        ) / total_matches

        return min(1.0, commercial_score), detected_patterns

    def _assess_quality(self, keyword: str, commercial_intent_score: float) -> KeywordQuality:
        """评估关键词质量"""
        quality_score = 0

        # 长度评分（适中长度较好）
        length = len(keyword)
        if 10 <= length <= 50:
            quality_score += 0.3
        elif 5 <= length <= 80:
            quality_score += 0.2
        else:
            quality_score += 0.1

        # 商业意图评分
        quality_score += commercial_intent_score * 0.4

        # 单词数量评分（2-5个单词比较好）
        word_count = len(keyword.split())
        if 2 <= word_count <= 5:
            quality_score += 0.2
        elif word_count == 1 or word_count == 6:
            quality_score += 0.1

        # 特殊字符评分（适量的连字符和撇号是好的）
        special_chars = len(re.findall(r'[-\']', keyword))
        if special_chars <= 2:
            quality_score += 0.1

        # 根据得分判断质量等级
        if quality_score >= 0.8:
            return KeywordQuality.EXCELLENT
        elif quality_score >= 0.6:
            return KeywordQuality.GOOD
        elif quality_score >= 0.4:
            return KeywordQuality.FAIR
        elif quality_score >= 0.2:
            return KeywordQuality.POOR
        else:
            return KeywordQuality.INVALID

    def _calculate_quality_modifier(self, keyword: str) -> float:
        """计算质量修饰符"""
        modifier = 1.0
        keyword_lower = keyword.lower()

        # 应用品质修饰词规则
        for modifier_word, modifier_value in self.rules.quality_modifiers.items():
            if modifier_word.lower() in keyword_lower:
                modifier *= modifier_value

        return modifier

    def _generate_recommendations(
        self,
        keyword: str,
        category: str,
        quality: KeywordQuality,
        commercial_intent_score: float
    ) -> List[str]:
        """生成优化建议"""
        recommendations = []

        # 基于质量的建议
        if quality == KeywordQuality.EXCELLENT:
            recommendations.append("关键词质量优秀，建议优先投入资源")
        elif quality == KeywordQuality.GOOD:
            recommendations.append("关键词质量良好，值得开发")
        elif quality == KeywordQuality.FAIR:
            recommendations.append("关键词质量一般，可以考虑优化")
        elif quality == KeywordQuality.POOR:
            recommendations.append("关键词质量较差，建议重新评估")
        else:
            recommendations.append("关键词无效，不建议使用")

        # 基于商业意图的建议
        if commercial_intent_score > 0.7:
            recommendations.append("商业意图强烈，建议创建转化导向的内容")
        elif commercial_intent_score > 0.4:
            recommendations.append("有一定商业意图，可以结合信息内容和商业元素")
        elif commercial_intent_score > 0.1:
            recommendations.append("主要为信息查询，建议创建教育性内容")
        else:
            recommendations.append("商业意图较弱，适合作为流量入口")

        # 基于分类的建议
        if category != "general":
            recommendations.append(f"属于{category}分类，建议针对该领域深度优化")

        # 基于关键词长度的建议
        word_count = len(keyword.split())
        if word_count == 1:
            recommendations.append("单词关键词竞争激烈，建议扩展为长尾关键词")
        elif word_count > 6:
            recommendations.append("关键词较长，可以考虑拆分为多个短语")

        return recommendations

    def batch_analyze_keywords(
        self,
        keywords: List[str],
        apply_filters: bool = True
    ) -> List[KeywordAnalysisResult]:
        """
        批量分析关键词

        Args:
            keywords: 关键词列表
            apply_filters: 是否应用质量过滤器

        Returns:
            分析结果列表
        """
        results = []

        for keyword in keywords:
            try:
                result = self.analyze_keyword(keyword)

                # 应用过滤器
                if apply_filters and not self._passes_quality_filter(result):
                    result.is_valid = False
                    result.exclusion_reasons.append("未通过质量过滤器")

                results.append(result)

            except Exception as e:
                self.logger.error(f"批量分析失败 {keyword}: {e}")
                # 添加错误结果
                error_result = KeywordAnalysisResult(
                    keyword=keyword,
                    category="error",
                    quality=KeywordQuality.INVALID,
                    commercial_intent_score=0.0,
                    quality_modifier=0.0,
                    detected_patterns=[],
                    exclusion_reasons=[f"分析错误: {str(e)}"],
                    recommendations=[],
                    is_valid=False
                )
                results.append(error_result)

        return results

    def _passes_quality_filter(self, result: KeywordAnalysisResult) -> bool:
        """检查关键词是否通过质量过滤器"""
        # 基本有效性检查
        if not result.is_valid:
            return False

        # 质量等级检查
        if result.quality in [KeywordQuality.INVALID, KeywordQuality.POOR]:
            return False

        # 商业意图检查
        if result.commercial_intent_score < 0.1:
            return False

        return True

    def filter_keywords_by_category(
        self,
        results: List[KeywordAnalysisResult],
        target_categories: List[str]
    ) -> List[KeywordAnalysisResult]:
        """按分类过滤关键词"""
        return [
            result for result in results
            if result.category in target_categories and result.is_valid
        ]

    def get_top_keywords_by_quality(
        self,
        results: List[KeywordAnalysisResult],
        limit: int = 20
    ) -> List[KeywordAnalysisResult]:
        """按质量获取顶级关键词"""
        # 质量等级排序
        quality_order = {
            KeywordQuality.EXCELLENT: 5,
            KeywordQuality.GOOD: 4,
            KeywordQuality.FAIR: 3,
            KeywordQuality.POOR: 2,
            KeywordQuality.INVALID: 1
        }

        valid_results = [r for r in results if r.is_valid]

        # 按质量和商业意图排序
        sorted_results = sorted(
            valid_results,
            key=lambda x: (
                quality_order.get(x.quality, 0),
                x.commercial_intent_score,
                x.quality_modifier
            ),
            reverse=True
        )

        return sorted_results[:limit]

    def generate_quality_report(
        self,
        results: List[KeywordAnalysisResult]
    ) -> Dict[str, Any]:
        """生成质量分析报告"""
        total_keywords = len(results)
        valid_keywords = len([r for r in results if r.is_valid])

        # 统计质量分布
        quality_distribution = {}
        for quality in KeywordQuality:
            count = len([r for r in results if r.quality == quality])
            quality_distribution[quality.value] = {
                'count': count,
                'percentage': (count / total_keywords * 100) if total_keywords > 0 else 0
            }

        # 统计分类分布
        category_distribution = {}
        for result in results:
            if result.category not in category_distribution:
                category_distribution[result.category] = 0
            category_distribution[result.category] += 1

        # 计算平均商业意图得分
        valid_results = [r for r in results if r.is_valid]
        avg_commercial_score = (
            sum(r.commercial_intent_score for r in valid_results) / len(valid_results)
            if valid_results else 0
        )

        # 统计常见排除原因
        exclusion_reasons = {}
        for result in results:
            for reason in result.exclusion_reasons:
                exclusion_reasons[reason] = exclusion_reasons.get(reason, 0) + 1

        return {
            'summary': {
                'total_keywords': total_keywords,
                'valid_keywords': valid_keywords,
                'validity_rate': (valid_keywords / total_keywords * 100) if total_keywords > 0 else 0,
                'avg_commercial_score': round(avg_commercial_score, 3)
            },
            'quality_distribution': quality_distribution,
            'category_distribution': category_distribution,
            'exclusion_reasons': exclusion_reasons,
            'recommendations': self._generate_batch_recommendations(results)
        }

    def _generate_batch_recommendations(
        self,
        results: List[KeywordAnalysisResult]
    ) -> List[str]:
        """为批量分析生成建议"""
        recommendations = []

        valid_results = [r for r in results if r.is_valid]
        total_count = len(results)
        valid_count = len(valid_results)

        if valid_count == 0:
            recommendations.append("没有有效的关键词，建议重新选择关键词来源")
            return recommendations

        validity_rate = valid_count / total_count
        if validity_rate < 0.5:
            recommendations.append(f"有效关键词比例较低({validity_rate:.1%})，建议优化关键词筛选标准")

        # 质量分析
        excellent_count = len([r for r in valid_results if r.quality == KeywordQuality.EXCELLENT])
        if excellent_count / valid_count > 0.2:
            recommendations.append("发现多个优质关键词，建议优先开发这些关键词")
        elif excellent_count == 0:
            recommendations.append("缺乏优质关键词，建议扩大关键词来源或优化筛选条件")

        # 商业意图分析
        high_intent_count = len([r for r in valid_results if r.commercial_intent_score > 0.6])
        if high_intent_count / valid_count > 0.3:
            recommendations.append("发现较多高商业意图关键词，适合商业化内容开发")
        elif high_intent_count / valid_count < 0.1:
            recommendations.append("商业意图关键词较少，建议平衡信息内容和商业内容")

        return recommendations