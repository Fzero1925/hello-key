"""
关键词分析器 V2 - 基于新analysis模块架构

使用模块化的分析算法和规则引擎进行关键词分析
"""

import os
import sys
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

# 导入编码处理器
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
try:
    from modules.utils.encoding_handler import safe_print
except ImportError:
    def safe_print(text, **kwargs):
        print(text, **kwargs)

# 导入新的analysis模块
from modules.analysis.analyzer_factory import AnalyzerFactory
from modules.analysis.models.analysis_models import (
    AnalysisResult, KeywordAnalysisData, ScoreMetrics,
    create_keyword_analysis_result, merge_analysis_results
)

# 导入数据源管理器
from modules.data_sources.base import DataSourceManager
from modules.cache import CacheManager


class KeywordAnalyzerV2:
    """
    关键词分析器 V2

    基于新的模块化架构，使用分析工厂创建的组件进行关键词分析
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        cache_manager: Optional[CacheManager] = None
    ):
        """
        初始化关键词分析器V2

        Args:
            config_path: 配置文件路径
            cache_manager: 缓存管理器
        """
        self.logger = logging.getLogger(__name__)

        # 初始化分析工厂
        try:
            self.analyzer_factory = AnalyzerFactory(config_path)
            self.logger.info("分析器工厂初始化成功")
        except Exception as e:
            self.logger.error(f"分析器工厂初始化失败: {e}")
            raise

        # 初始化缓存管理器
        self.cache_manager = cache_manager or CacheManager(cache_dir="data/analysis_cache")

        # 创建分析组件
        self._initialize_analyzers()

        # 性能统计
        self.stats = {
            'total_analyzed': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'average_processing_time_ms': 0.0
        }

        self.logger.info("关键词分析器V2初始化完成")

    def _initialize_analyzers(self):
        """初始化分析组件"""
        try:
            # 获取关键词分析套件
            self.analysis_suite = self.analyzer_factory.create_analysis_suite("keyword")

            # 解包分析器组件
            self.scoring_engine = self.analysis_suite['scoring_engine']
            self.intent_detector = self.analysis_suite['intent_detector']
            self.keyword_rule_engine = self.analysis_suite['keyword_rule_engine']
            self.value_estimator = self.analysis_suite['value_estimator']

            self.logger.info("分析组件初始化成功")

        except Exception as e:
            self.logger.error(f"分析组件初始化失败: {e}")
            raise

    def analyze_keyword(
        self,
        keyword: str,
        keyword_data: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> AnalysisResult:
        """
        分析单个关键词

        Args:
            keyword: 要分析的关键词
            keyword_data: 关键词的基础数据（搜索量、竞争度等）
            use_cache: 是否使用缓存

        Returns:
            分析结果
        """
        start_time = time.time()

        try:
            # 检查缓存
            cache_key = f"keyword_analysis_v2:{keyword}"
            if use_cache:
                cached_result = self.cache_manager.get(cache_key)
                if cached_result:
                    self.logger.debug(f"从缓存获取分析结果: {keyword}")
                    return cached_result

            # 准备关键词数据
            keyword_data = keyword_data or {}
            search_volume = keyword_data.get('search_volume', 0)

            # 1. 规则引擎分析
            rule_analysis = self.keyword_rule_engine.analyze_keyword(keyword)

            if not rule_analysis.is_valid:
                # 关键词不符合规则，返回无效结果
                result = self._create_invalid_result(keyword, rule_analysis.exclusion_reasons)
                processing_time = (time.time() - start_time) * 1000
                result.processing_time_ms = processing_time
                return result

            # 2. 意图检测
            intent_analysis = self.intent_detector.analyze_intent(keyword)

            # 3. 评分计算
            score_metrics = self._calculate_scores(
                keyword, rule_analysis, intent_analysis, keyword_data
            )

            # 4. 价值评估
            value_estimates = self._calculate_value_estimates(
                keyword, search_volume, intent_analysis.commercial_value, rule_analysis.category
            )

            # 5. 构建关键词分析数据
            analysis_data = self._build_keyword_analysis_data(
                keyword, rule_analysis, intent_analysis, value_estimates, keyword_data
            )

            # 6. 生成洞察和建议
            insights, recommendations = self._generate_insights_and_recommendations(
                keyword, rule_analysis, intent_analysis, score_metrics, value_estimates
            )

            # 7. 创建最终结果
            result = create_keyword_analysis_result(
                keyword=keyword,
                keyword_data=analysis_data,
                score_metrics=score_metrics,
                insights=[],  # 将在下面设置
                recommendations=recommendations,
                confidence=self._calculate_confidence(rule_analysis, intent_analysis),
                quality_grade=rule_analysis.quality.value
            )

            # 设置洞察
            result.insights = insights

            # 计算处理时间
            processing_time = (time.time() - start_time) * 1000
            result.processing_time_ms = processing_time

            # 更新统计
            self.stats['total_analyzed'] += 1
            self.stats['successful_analyses'] += 1
            self.stats['average_processing_time_ms'] = (
                (self.stats['average_processing_time_ms'] * (self.stats['total_analyzed'] - 1) + processing_time) /
                self.stats['total_analyzed']
            )

            # 缓存结果
            if use_cache:
                self.cache_manager.set(cache_key, result, ttl=3600)  # 缓存1小时

            self.logger.debug(f"关键词分析完成: {keyword} (耗时: {processing_time:.2f}ms)")
            return result

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self.logger.error(f"关键词分析失败 {keyword}: {e}")

            # 更新失败统计
            self.stats['total_analyzed'] += 1
            self.stats['failed_analyses'] += 1

            # 创建错误结果
            result = self._create_error_result(keyword, str(e))
            result.processing_time_ms = processing_time
            return result

    def _calculate_scores(
        self,
        keyword: str,
        rule_analysis,
        intent_analysis,
        keyword_data: Dict[str, Any]
    ) -> ScoreMetrics:
        """计算评分指标"""
        try:
            # 从各种分析中提取评分因子
            trend_score = keyword_data.get('trend_score', 0.5)
            intent_score = intent_analysis.commercial_value
            search_volume = keyword_data.get('search_volume', 0)

            # 将搜索量标准化到0-1范围
            search_volume_score = min(1.0, search_volume / 100000) if search_volume > 0 else 0.1

            # 新鲜度评分（基于关键词特征）
            freshness_score = self._calculate_freshness_score(keyword, keyword_data)

            # 竞争难度评分
            difficulty_score = keyword_data.get('competition_score', 0.5)

            # 使用评分引擎计算机会评分
            opportunity_score = self.scoring_engine.calculate_opportunity_score(
                trend=trend_score,
                intent=intent_score,
                search_volume=search_volume_score,
                freshness=freshness_score,
                difficulty=difficulty_score
            )

            # 计算商业价值评分（基于质量修饰符调整）
            commercial_value = intent_score * rule_analysis.quality_modifier

            return ScoreMetrics(
                total_score=opportunity_score / 100.0,  # 转换为0-1范围
                opportunity_score=opportunity_score,
                commercial_value=commercial_value,
                trend_score=trend_score,
                intent_score=intent_score,
                search_volume_score=search_volume_score,
                freshness_score=freshness_score,
                difficulty_score=difficulty_score,
                weights={
                    'trend': 0.35,
                    'intent': 0.30,
                    'search_volume': 0.15,
                    'freshness': 0.20
                },
                explanations={
                    'opportunity': f"基于多因子评分模型，机会评分为{opportunity_score:.1f}",
                    'commercial': f"商业价值结合意图得分({intent_score:.2f})和质量调整({rule_analysis.quality_modifier:.2f})"
                }
            )

        except Exception as e:
            self.logger.error(f"评分计算失败 {keyword}: {e}")
            return ScoreMetrics()  # 返回默认评分

    def _calculate_freshness_score(self, keyword: str, keyword_data: Dict[str, Any]) -> float:
        """计算新鲜度评分"""
        try:
            # 基于关键词特征判断新鲜度
            freshness_indicators = ['new', 'latest', '2025', '2024', 'updated', 'recent']
            keyword_lower = keyword.lower()

            freshness_score = 0.4  # 基础分数

            # 检查新鲜度指示词
            for indicator in freshness_indicators:
                if indicator in keyword_lower:
                    freshness_score += 0.2
                    break

            # 检查是否包含年份
            import re
            if re.search(r'202[4-9]', keyword):
                freshness_score += 0.3

            # 从数据中获取时间相关信息
            if 'first_seen' in keyword_data:
                try:
                    first_seen = keyword_data['first_seen']
                    if isinstance(first_seen, str):
                        first_seen = datetime.fromisoformat(first_seen)

                    days_old = (datetime.now() - first_seen).days
                    if days_old < 7:
                        freshness_score += 0.3
                    elif days_old < 30:
                        freshness_score += 0.2
                    elif days_old < 90:
                        freshness_score += 0.1

                except Exception:
                    pass

            return min(1.0, freshness_score)

        except Exception:
            return 0.5  # 默认中等新鲜度

    def _calculate_value_estimates(
        self,
        keyword: str,
        search_volume: int,
        commercial_value: float,
        category: str
    ) -> Dict[str, Any]:
        """计算价值估算"""
        try:
            # 使用价值评估器计算多种收益模型
            estimates = self.value_estimator.compare_models(
                search_volume=search_volume,
                keyword_data={
                    'commercial_value': commercial_value,
                    'category': category,
                    'competition_level': 0.5  # 默认中等竞争
                }
            )

            # 转换为字典格式
            value_estimates = {}
            for estimate in estimates:
                value_estimates[estimate.revenue_model] = {
                    'monthly_estimate': estimate.monthly_estimate,
                    'annual_estimate': estimate.annual_estimate,
                    'confidence': estimate.confidence_level,
                    'range_low': estimate.range_low,
                    'range_high': estimate.range_high,
                    'risk_factors': estimate.risk_factors
                }

            return value_estimates

        except Exception as e:
            self.logger.error(f"价值估算失败 {keyword}: {e}")
            return {}

    def _build_keyword_analysis_data(
        self,
        keyword: str,
        rule_analysis,
        intent_analysis,
        value_estimates: Dict[str, Any],
        keyword_data: Dict[str, Any]
    ) -> KeywordAnalysisData:
        """构建关键词分析数据"""
        # 计算估算收益
        estimated_revenue = {}
        for model, data in value_estimates.items():
            estimated_revenue[model] = data.get('monthly_estimate', 0)

        # 确定收益潜力
        max_revenue = max(estimated_revenue.values()) if estimated_revenue else 0
        if max_revenue > 500:
            revenue_potential = "high"
        elif max_revenue > 100:
            revenue_potential = "medium"
        else:
            revenue_potential = "low"

        return KeywordAnalysisData(
            keyword=keyword,
            category=rule_analysis.category,
            search_volume=keyword_data.get('search_volume', 0),
            competition_level=keyword_data.get('competition_level', 'medium'),
            commercial_intent=intent_analysis.commercial_value,
            trend_direction=keyword_data.get('trend_direction', 'stable'),
            trend_strength=keyword_data.get('trend_score', 0.0),
            seasonality_score=keyword_data.get('seasonality_score', 0.0),
            estimated_cpc=keyword_data.get('estimated_cpc', 0.0),
            estimated_revenue=estimated_revenue,
            revenue_potential=revenue_potential,
            top_competitors=keyword_data.get('competitors', []),
            content_gaps=rule_analysis.recommendations[:3],  # 使用前3个建议作为内容空缺
            ranking_difficulty=rule_analysis.quality.value,
            related_keywords=keyword_data.get('related_keywords', []),
            long_tail_opportunities=self._generate_long_tail_opportunities(keyword)
        )

    def _generate_long_tail_opportunities(self, keyword: str) -> List[str]:
        """生成长尾关键词机会"""
        # 简单的长尾关键词生成逻辑
        base_modifiers = [
            "best", "top", "how to", "review", "guide", "2025",
            "cheap", "vs", "for beginners", "comparison"
        ]

        long_tail = []
        for modifier in base_modifiers[:3]:  # 只生成3个示例
            if modifier not in keyword.lower():
                long_tail.append(f"{modifier} {keyword}")

        return long_tail

    def _generate_insights_and_recommendations(
        self,
        keyword: str,
        rule_analysis,
        intent_analysis,
        score_metrics: ScoreMetrics,
        value_estimates: Dict[str, Any]
    ) -> tuple:
        """生成洞察和建议"""
        insights = []
        recommendations = []

        # 基于评分生成洞察
        if score_metrics.opportunity_score > 70:
            insights.append(f"关键词'{keyword}'具有高机会评分({score_metrics.opportunity_score:.1f})，投资潜力大")
        elif score_metrics.opportunity_score < 30:
            insights.append(f"关键词'{keyword}'机会评分较低({score_metrics.opportunity_score:.1f})，需要谨慎评估")

        # 基于意图生成洞察
        if intent_analysis.commercial_value > 0.7:
            insights.append(f"检测到强烈的商业意图({intent_analysis.commercial_value:.2f})，适合商业化内容")
        elif intent_analysis.commercial_value < 0.3:
            insights.append(f"商业意图较弱({intent_analysis.commercial_value:.2f})，更适合信息性内容")

        # 基于价值估算生成洞察
        if value_estimates:
            max_revenue = max(
                data.get('monthly_estimate', 0) for data in value_estimates.values()
            )
            if max_revenue > 200:
                insights.append(f"预估最高月收益可达${max_revenue:.0f}，具有良好的盈利潜力")

        # 合并规则引擎的建议
        recommendations.extend(rule_analysis.recommendations)
        recommendations.extend(intent_analysis.recommendations)

        # 添加基于分析结果的建议
        if score_metrics.difficulty_score > 0.8:
            recommendations.append("竞争激烈，建议专注于长尾关键词策略")

        if score_metrics.trend_score > 0.7:
            recommendations.append("趋势向好，建议尽快创建相关内容抢占先机")

        return insights, recommendations

    def _calculate_confidence(self, rule_analysis, intent_analysis) -> float:
        """计算分析置信度"""
        confidence_factors = [
            intent_analysis.intent_confidence,
            0.8,  # 规则引擎置信度（假设较高）
            0.9 if rule_analysis.is_valid else 0.1  # 规则验证置信度
        ]

        return sum(confidence_factors) / len(confidence_factors)

    def batch_analyze_keywords(
        self,
        keywords: List[str],
        keywords_data: Optional[List[Dict[str, Any]]] = None,
        use_cache: bool = True,
        max_workers: int = 1  # 暂时不支持并行，保持简单
    ) -> List[AnalysisResult]:
        """
        批量分析关键词

        Args:
            keywords: 关键词列表
            keywords_data: 关键词数据列表
            use_cache: 是否使用缓存
            max_workers: 最大工作线程数

        Returns:
            分析结果列表
        """
        results = []
        keywords_data = keywords_data or [{}] * len(keywords)

        start_time = time.time()
        self.logger.info(f"开始批量分析 {len(keywords)} 个关键词")

        for i, keyword in enumerate(keywords):
            try:
                keyword_data = keywords_data[i] if i < len(keywords_data) else {}
                result = self.analyze_keyword(keyword, keyword_data, use_cache)
                results.append(result)

                # 进度输出
                if (i + 1) % 10 == 0:
                    self.logger.info(f"批量分析进度: {i + 1}/{len(keywords)}")

            except Exception as e:
                self.logger.error(f"批量分析失败 {keyword}: {e}")
                error_result = self._create_error_result(keyword, str(e))
                results.append(error_result)

        total_time = time.time() - start_time
        self.logger.info(f"批量分析完成，耗时: {total_time:.2f}秒")

        return results

    def analyze_keywords_with_data_source(
        self,
        category: str = "smart_plugs",
        limit: int = 20,
        data_source_manager: Optional[DataSourceManager] = None
    ) -> List[AnalysisResult]:
        """
        结合数据源管理器分析关键词

        Args:
            category: 关键词分类
            limit: 数量限制
            data_source_manager: 数据源管理器

        Returns:
            分析结果列表
        """
        try:
            if data_source_manager is None:
                self.logger.warning("未提供数据源管理器，无法获取关键词数据")
                return []

            # 从数据源获取关键词
            keyword_data_list = data_source_manager.get_keywords(category=category, limit=limit)

            # 转换为分析所需的格式
            keywords = []
            keywords_data = []

            for kw_data in keyword_data_list:
                keywords.append(kw_data.keyword)
                keywords_data.append({
                    'search_volume': kw_data.search_volume or 0,
                    'trend_score': kw_data.trend_score,
                    'source': kw_data.source,
                    'confidence': kw_data.confidence,
                    'metadata': kw_data.metadata or {}
                })

            # 批量分析
            results = self.batch_analyze_keywords(keywords, keywords_data)

            self.logger.info(f"完成数据源关键词分析: {len(results)} 个结果")
            return results

        except Exception as e:
            self.logger.error(f"数据源关键词分析失败: {e}")
            return []

    def get_top_opportunities(
        self,
        results: List[AnalysisResult],
        limit: int = 10,
        min_score: float = 0.5
    ) -> List[AnalysisResult]:
        """获取顶级机会关键词"""
        # 过滤有效结果
        valid_results = [
            r for r in results
            if r.status.value == "success" and r.metrics.score >= min_score
        ]

        # 按评分排序
        sorted_results = sorted(
            valid_results,
            key=lambda x: (x.metrics.score, x.metrics.commercial_value),
            reverse=True
        )

        return sorted_results[:limit]

    def generate_analysis_report(
        self,
        results: List[AnalysisResult],
        report_title: str = "关键词分析报告"
    ) -> Dict[str, Any]:
        """生成分析报告"""
        try:
            # 使用analysis模块的merge功能
            batch_result = merge_analysis_results(results)

            # 添加更多统计信息
            valid_results = [r for r in results if r.status.value == "success"]
            high_value_count = len([r for r in valid_results if r.metrics.commercial_value > 0.7])
            low_competition_count = len([
                r for r in valid_results
                if r.data.get('keyword_data', {}).ranking_difficulty in ['excellent', 'good']
            ])

            report = {
                'title': report_title,
                'generated_at': datetime.now().isoformat(),
                'summary': batch_result.summary_statistics,
                'total_keywords': batch_result.total_items,
                'successful_analyses': batch_result.successful_items,
                'failed_analyses': batch_result.failed_items,
                'high_commercial_value_count': high_value_count,
                'low_competition_count': low_competition_count,
                'average_processing_time_ms': batch_result.total_processing_time_ms / max(1, batch_result.total_items),
                'top_opportunities': [
                    {
                        'keyword': r.target,
                        'score': r.metrics.score,
                        'commercial_value': r.metrics.commercial_value,
                        'category': r.data.get('keyword_data', {}).category if hasattr(r.data.get('keyword_data', {}), 'category') else 'unknown'
                    }
                    for r in self.get_top_opportunities(results, limit=10)
                ],
                'recommendations': self._generate_batch_recommendations(results),
                'analyzer_stats': self.stats.copy()
            }

            return report

        except Exception as e:
            self.logger.error(f"报告生成失败: {e}")
            return {'error': str(e)}

    def _generate_batch_recommendations(self, results: List[AnalysisResult]) -> List[str]:
        """生成批量分析建议"""
        recommendations = []

        valid_results = [r for r in results if r.status.value == "success"]
        if not valid_results:
            recommendations.append("所有关键词分析失败，建议检查数据质量和配置")
            return recommendations

        # 基于成功率的建议
        success_rate = len(valid_results) / len(results)
        if success_rate < 0.8:
            recommendations.append(f"分析成功率较低({success_rate:.1%})，建议优化关键词筛选条件")

        # 基于得分分布的建议
        high_score_count = len([r for r in valid_results if r.metrics.score > 0.7])
        if high_score_count == 0:
            recommendations.append("缺乏高分关键词，建议扩大关键词来源或调整评分标准")
        elif high_score_count > len(valid_results) * 0.3:
            recommendations.append("发现较多高分关键词，建议优先投入资源开发")

        # 基于商业价值的建议
        avg_commercial_value = sum(r.metrics.commercial_value for r in valid_results) / len(valid_results)
        if avg_commercial_value < 0.4:
            recommendations.append("平均商业价值较低，建议增加商业意图更强的关键词")

        return recommendations

    def _create_invalid_result(self, keyword: str, exclusion_reasons: List[str]) -> AnalysisResult:
        """创建无效关键词的结果"""
        return AnalysisResult(
            analysis_type=AnalysisResult.__annotations__['analysis_type'].__args__[0].KEYWORD,
            target=keyword,
            status=AnalysisResult.__annotations__['status'].__args__[0].WARNING,
            error_message="关键词不符合规则要求",
            warnings=exclusion_reasons,
            recommendations=["请检查关键词是否符合基本规则要求"]
        )

    def _create_error_result(self, keyword: str, error_msg: str) -> AnalysisResult:
        """创建错误结果"""
        return AnalysisResult(
            analysis_type=AnalysisResult.__annotations__['analysis_type'].__args__[0].KEYWORD,
            target=keyword,
            status=AnalysisResult.__annotations__['status'].__args__[0].ERROR,
            error_message=error_msg,
            recommendations=["请检查关键词数据和系统配置"]
        )

    def get_analyzer_status(self) -> Dict[str, Any]:
        """获取分析器状态"""
        factory_status = self.analyzer_factory.get_factory_status()

        return {
            'analyzer_version': 'V2.0',
            'initialization_status': 'ready',
            'factory_status': factory_status,
            'cache_enabled': self.cache_manager is not None,
            'analysis_components': list(self.analysis_suite.keys()),
            'performance_stats': self.stats.copy()
        }


# 向后兼容性: 提供旧接口别名
KeywordAnalyzer = KeywordAnalyzerV2


# 示例使用
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    safe_print("=== 关键词分析器V2测试 ===\n")

    try:
        # 创建分析器
        analyzer = KeywordAnalyzerV2()

        # 测试单个关键词分析
        test_keyword = "best smart plug 2025"
        test_data = {
            'search_volume': 15000,
            'trend_score': 0.8,
            'competition_level': 'medium'
        }

        safe_print(f"--- 分析关键词: {test_keyword} ---")
        result = analyzer.analyze_keyword(test_keyword, test_data)

        safe_print(f"分析状态: {result.status.value}")
        safe_print(f"机会评分: {result.metrics.score:.3f}")
        safe_print(f"商业价值: {result.metrics.commercial_value:.3f}")
        safe_print(f"处理时间: {result.processing_time_ms:.2f}ms")

        if result.insights:
            safe_print("\n洞察:")
            for insight in result.insights:
                safe_print(f"  • {insight}")

        if result.recommendations:
            safe_print("\n建议:")
            for rec in result.recommendations[:3]:
                safe_print(f"  • {rec}")

        # 测试批量分析
        safe_print(f"\n--- 批量分析测试 ---")
        test_keywords = [
            "smart home security camera",
            "wifi smart plug outlet",
            "alexa compatible devices"
        ]

        batch_results = analyzer.batch_analyze_keywords(test_keywords)
        safe_print(f"批量分析完成，共 {len(batch_results)} 个结果")

        # 获取顶级机会
        top_opportunities = analyzer.get_top_opportunities(batch_results, limit=3)
        safe_print(f"发现 {len(top_opportunities)} 个高价值机会")

        # 生成报告
        report = analyzer.generate_analysis_report(batch_results)
        safe_print(f"\n--- 分析报告 ---")
        safe_print(f"成功分析: {report['successful_analyses']}/{report['total_keywords']}")
        safe_print(f"平均处理时间: {report['average_processing_time_ms']:.2f}ms")

        # 显示状态
        status = analyzer.get_analyzer_status()
        safe_print(f"\n--- 分析器状态 ---")
        safe_print(f"版本: {status['analyzer_version']}")
        safe_print(f"组件数: {len(status['analysis_components'])}")

        safe_print("\n✅ 关键词分析器V2测试完成！")

    except Exception as e:
        safe_print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()