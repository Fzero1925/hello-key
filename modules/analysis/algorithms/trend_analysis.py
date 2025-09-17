"""
趋势分析算法

专门负责趋势检测、时间序列分析和趋势预测
"""

import logging
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import statistics


class TrendDirection(Enum):
    """趋势方向"""
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"
    VOLATILE = "volatile"


class TrendStrength(Enum):
    """趋势强度"""
    VERY_STRONG = "very_strong"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    VERY_WEAK = "very_weak"


@dataclass
class TrendConfig:
    """趋势分析配置"""
    # 时间窗口设置
    short_window: int = 7  # 短期窗口（天）
    long_window: int = 30  # 长期窗口（天）
    trend_threshold: float = 0.1  # 趋势判定阈值

    # 波动性阈值
    volatility_low: float = 0.1
    volatility_moderate: float = 0.3
    volatility_high: float = 0.5

    # 趋势强度阈值
    strength_thresholds: Dict[str, float] = None

    def __post_init__(self):
        if self.strength_thresholds is None:
            self.strength_thresholds = {
                "very_weak": 0.05,
                "weak": 0.15,
                "moderate": 0.30,
                "strong": 0.50,
                "very_strong": 0.70
            }


@dataclass
class TrendAnalysis:
    """趋势分析结果"""
    direction: TrendDirection
    strength: TrendStrength
    trend_score: float
    volatility: float
    momentum: float
    support_level: float
    resistance_level: float
    prediction_confidence: float
    time_series_data: List[Dict[str, Any]]
    insights: List[str]


class TrendAnalyzer:
    """
    趋势分析引擎

    提供多维度的趋势分析功能
    """

    def __init__(self, config: Optional[TrendConfig] = None):
        """
        初始化趋势分析器

        Args:
            config: 趋势分析配置
        """
        self.config = config or TrendConfig()
        self.logger = logging.getLogger(__name__)

    def analyze_search_volume_trend(
        self,
        time_series: List[Dict[str, Any]],
        volume_key: str = "search_volume"
    ) -> TrendAnalysis:
        """
        分析搜索量趋势

        Args:
            time_series: 时间序列数据 [{"date": "2025-01-01", "search_volume": 1000}, ...]
            volume_key: 搜索量字段名

        Returns:
            趋势分析结果
        """
        try:
            if len(time_series) < 2:
                return self._create_error_analysis("数据点不足")

            # 提取数值序列
            values = [item.get(volume_key, 0) for item in time_series]
            values = [float(v) for v in values if v is not None]

            if not values:
                return self._create_error_analysis("无有效数据")

            # 基础统计
            mean_value = statistics.mean(values)
            std_value = statistics.stdev(values) if len(values) > 1 else 0

            # 趋势方向分析
            direction = self._calculate_trend_direction(values)

            # 趋势强度分析
            strength = self._calculate_trend_strength(values)

            # 趋势得分计算
            trend_score = self._calculate_trend_score(values)

            # 波动性分析
            volatility = self._calculate_volatility(values)

            # 动量分析
            momentum = self._calculate_momentum(values)

            # 支撑位和阻力位
            support_level, resistance_level = self._calculate_support_resistance(values)

            # 预测置信度
            prediction_confidence = self._calculate_prediction_confidence(values, volatility)

            # 生成洞察
            insights = self._generate_insights(
                direction, strength, trend_score, volatility, momentum
            )

            return TrendAnalysis(
                direction=direction,
                strength=strength,
                trend_score=round(trend_score, 2),
                volatility=round(volatility, 2),
                momentum=round(momentum, 2),
                support_level=round(support_level, 2),
                resistance_level=round(resistance_level, 2),
                prediction_confidence=round(prediction_confidence, 2),
                time_series_data=time_series,
                insights=insights
            )

        except Exception as e:
            self.logger.error(f"趋势分析失败: {e}")
            return self._create_error_analysis(str(e))

    def _calculate_trend_direction(self, values: List[float]) -> TrendDirection:
        """计算趋势方向"""
        if len(values) < 2:
            return TrendDirection.STABLE

        # 计算线性回归斜率
        n = len(values)
        x = list(range(n))
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return TrendDirection.STABLE

        slope = numerator / denominator

        # 计算相对变化率
        relative_change = slope / y_mean if y_mean != 0 else 0

        # 判断趋势方向
        if abs(relative_change) < self.config.trend_threshold:
            return TrendDirection.STABLE
        elif relative_change > 0:
            return TrendDirection.RISING
        else:
            return TrendDirection.FALLING

    def _calculate_trend_strength(self, values: List[float]) -> TrendStrength:
        """计算趋势强度"""
        if len(values) < 2:
            return TrendStrength.VERY_WEAK

        # 计算R²值（决定系数）
        n = len(values)
        x = list(range(n))
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)

        # 线性回归
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator_x = sum((x[i] - x_mean) ** 2 for i in range(n))
        denominator_y = sum((values[i] - y_mean) ** 2 for i in range(n))

        if denominator_x == 0 or denominator_y == 0:
            return TrendStrength.VERY_WEAK

        r_squared = (numerator ** 2) / (denominator_x * denominator_y)

        # 根据R²值判断强度
        if r_squared >= self.config.strength_thresholds["very_strong"]:
            return TrendStrength.VERY_STRONG
        elif r_squared >= self.config.strength_thresholds["strong"]:
            return TrendStrength.STRONG
        elif r_squared >= self.config.strength_thresholds["moderate"]:
            return TrendStrength.MODERATE
        elif r_squared >= self.config.strength_thresholds["weak"]:
            return TrendStrength.WEAK
        else:
            return TrendStrength.VERY_WEAK

    def _calculate_trend_score(self, values: List[float]) -> float:
        """计算趋势得分 (0-100)"""
        if len(values) < 2:
            return 0

        # 计算多个趋势指标的综合得分
        direction_score = self._get_direction_score(values)
        strength_score = self._get_strength_score(values)
        consistency_score = self._get_consistency_score(values)
        momentum_score = self._get_momentum_score(values)

        # 加权平均
        trend_score = (
            direction_score * 0.3 +
            strength_score * 0.25 +
            consistency_score * 0.25 +
            momentum_score * 0.20
        )

        return max(0, min(100, trend_score))

    def _calculate_volatility(self, values: List[float]) -> float:
        """计算波动性"""
        if len(values) < 2:
            return 0

        mean_val = statistics.mean(values)
        if mean_val == 0:
            return 0

        variance = statistics.variance(values)
        volatility = (variance ** 0.5) / mean_val

        return min(1.0, volatility)

    def _calculate_momentum(self, values: List[float]) -> float:
        """计算动量"""
        if len(values) < 3:
            return 0

        # 计算短期和长期平均值
        short_window = min(self.config.short_window, len(values) // 3)
        long_window = min(self.config.long_window, len(values))

        if short_window == 0 or long_window == 0:
            return 0

        short_avg = statistics.mean(values[-short_window:])
        long_avg = statistics.mean(values[-long_window:])

        if long_avg == 0:
            return 0

        momentum = (short_avg - long_avg) / long_avg

        return max(-1.0, min(1.0, momentum))

    def _calculate_support_resistance(self, values: List[float]) -> Tuple[float, float]:
        """计算支撑位和阻力位"""
        if not values:
            return 0, 0

        # 简单的支撑位和阻力位计算
        sorted_values = sorted(values)
        n = len(sorted_values)

        # 支撑位：下四分位数
        support_index = n // 4
        support_level = sorted_values[support_index]

        # 阻力位：上四分位数
        resistance_index = (3 * n) // 4
        resistance_level = sorted_values[resistance_index]

        return support_level, resistance_level

    def _calculate_prediction_confidence(self, values: List[float], volatility: float) -> float:
        """计算预测置信度"""
        if len(values) < 3:
            return 0.1

        # 基于数据点数量和波动性计算置信度
        data_points_factor = min(1.0, len(values) / 30)  # 30个数据点为理想状态
        volatility_factor = max(0.1, 1.0 - volatility)  # 波动性越低，置信度越高

        confidence = data_points_factor * volatility_factor * 0.9

        return max(0.1, min(0.95, confidence))

    def _get_direction_score(self, values: List[float]) -> float:
        """获取方向得分"""
        direction = self._calculate_trend_direction(values)

        if direction == TrendDirection.RISING:
            return 80
        elif direction == TrendDirection.FALLING:
            return 20
        elif direction == TrendDirection.STABLE:
            return 50
        else:  # VOLATILE
            return 30

    def _get_strength_score(self, values: List[float]) -> float:
        """获取强度得分"""
        strength = self._calculate_trend_strength(values)

        strength_scores = {
            TrendStrength.VERY_STRONG: 90,
            TrendStrength.STRONG: 75,
            TrendStrength.MODERATE: 60,
            TrendStrength.WEAK: 40,
            TrendStrength.VERY_WEAK: 20
        }

        return strength_scores.get(strength, 0)

    def _get_consistency_score(self, values: List[float]) -> float:
        """获取一致性得分"""
        if len(values) < 3:
            return 0

        # 计算连续同向变化的比例
        changes = [values[i] - values[i-1] for i in range(1, len(values))]
        if not changes:
            return 50

        positive_changes = sum(1 for change in changes if change > 0)
        negative_changes = sum(1 for change in changes if change < 0)
        total_changes = len(changes)

        # 计算主要方向的一致性
        consistency = max(positive_changes, negative_changes) / total_changes

        return consistency * 100

    def _get_momentum_score(self, values: List[float]) -> float:
        """获取动量得分"""
        momentum = self._calculate_momentum(values)

        # 将动量从[-1, 1]映射到[0, 100]
        momentum_score = (momentum + 1) * 50

        return max(0, min(100, momentum_score))

    def _generate_insights(
        self,
        direction: TrendDirection,
        strength: TrendStrength,
        trend_score: float,
        volatility: float,
        momentum: float
    ) -> List[str]:
        """生成趋势洞察"""
        insights = []

        # 趋势方向洞察
        if direction == TrendDirection.RISING:
            insights.append("搜索量呈上升趋势，市场兴趣增长")
        elif direction == TrendDirection.FALLING:
            insights.append("搜索量呈下降趋势，需要关注市场变化")
        elif direction == TrendDirection.STABLE:
            insights.append("搜索量相对稳定，市场成熟")
        else:
            insights.append("搜索量波动较大，市场不稳定")

        # 趋势强度洞察
        if strength in [TrendStrength.STRONG, TrendStrength.VERY_STRONG]:
            insights.append("趋势强度高，变化方向明确")
        elif strength == TrendStrength.MODERATE:
            insights.append("趋势强度中等，有一定方向性")
        else:
            insights.append("趋势强度弱，方向性不明确")

        # 波动性洞察
        if volatility < self.config.volatility_low:
            insights.append("波动性低，搜索量稳定")
        elif volatility < self.config.volatility_moderate:
            insights.append("波动性中等，有一定不确定性")
        elif volatility < self.config.volatility_high:
            insights.append("波动性较高，市场变化频繁")
        else:
            insights.append("波动性很高，市场极不稳定")

        # 动量洞察
        if momentum > 0.3:
            insights.append("正向动量强劲，建议密切关注")
        elif momentum > 0.1:
            insights.append("正向动量温和，可考虑投入")
        elif momentum < -0.3:
            insights.append("负向动量强劲，建议谨慎")
        elif momentum < -0.1:
            insights.append("负向动量温和，需要观察")
        else:
            insights.append("动量平衡，趋势不明确")

        # 综合建议
        if trend_score > 70:
            insights.append("综合趋势得分高，推荐优先关注")
        elif trend_score > 50:
            insights.append("综合趋势得分中等，可以考虑")
        else:
            insights.append("综合趋势得分较低，建议观望")

        return insights

    def analyze_seasonal_patterns(
        self,
        time_series: List[Dict[str, Any]],
        date_key: str = "date",
        value_key: str = "search_volume"
    ) -> Dict[str, Any]:
        """
        分析季节性模式

        Args:
            time_series: 时间序列数据
            date_key: 日期字段名
            value_key: 数值字段名

        Returns:
            季节性分析结果
        """
        try:
            if len(time_series) < 12:  # 至少需要一年的数据
                return {"error": "数据不足，无法进行季节性分析"}

            # 按月份分组
            monthly_data = {}
            for item in time_series:
                try:
                    date_str = item.get(date_key, "")
                    if isinstance(date_str, str):
                        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        date_obj = date_str

                    month = date_obj.month
                    value = float(item.get(value_key, 0))

                    if month not in monthly_data:
                        monthly_data[month] = []
                    monthly_data[month].append(value)

                except (ValueError, TypeError):
                    continue

            # 计算月度平均值
            monthly_averages = {}
            for month, values in monthly_data.items():
                if values:
                    monthly_averages[month] = statistics.mean(values)

            if len(monthly_averages) < 6:
                return {"error": "有效月份数据不足"}

            # 计算季节性指数
            overall_average = statistics.mean(monthly_averages.values())
            seasonal_indices = {
                month: avg / overall_average
                for month, avg in monthly_averages.items()
            }

            # 识别峰值和低谷
            sorted_months = sorted(seasonal_indices.items(), key=lambda x: x[1], reverse=True)
            peak_months = sorted_months[:3]
            low_months = sorted_months[-3:]

            return {
                "monthly_averages": monthly_averages,
                "seasonal_indices": seasonal_indices,
                "peak_months": [{"month": m, "index": idx} for m, idx in peak_months],
                "low_months": [{"month": m, "index": idx} for m, idx in low_months],
                "seasonality_strength": max(seasonal_indices.values()) / min(seasonal_indices.values()),
                "recommendations": self._generate_seasonal_recommendations(peak_months, low_months)
            }

        except Exception as e:
            self.logger.error(f"季节性分析失败: {e}")
            return {"error": str(e)}

    def _generate_seasonal_recommendations(
        self,
        peak_months: List[Tuple[int, float]],
        low_months: List[Tuple[int, float]]
    ) -> List[str]:
        """生成季节性建议"""
        recommendations = []

        # 月份名称映射
        month_names = {
            1: "1月", 2: "2月", 3: "3月", 4: "4月", 5: "5月", 6: "6月",
            7: "7月", 8: "8月", 9: "9月", 10: "10月", 11: "11月", 12: "12月"
        }

        # 峰值月份建议
        peak_months_names = [month_names[month] for month, _ in peak_months]
        recommendations.append(f"搜索高峰期: {', '.join(peak_months_names)}，建议在此期间加大内容投入")

        # 低谷月份建议
        low_months_names = [month_names[month] for month, _ in low_months]
        recommendations.append(f"搜索低谷期: {', '.join(low_months_names)}，可用于内容准备和优化")

        return recommendations

    def _create_error_analysis(self, error_msg: str) -> TrendAnalysis:
        """创建错误情况下的默认分析结果"""
        return TrendAnalysis(
            direction=TrendDirection.STABLE,
            strength=TrendStrength.VERY_WEAK,
            trend_score=0,
            volatility=0,
            momentum=0,
            support_level=0,
            resistance_level=0,
            prediction_confidence=0,
            time_series_data=[],
            insights=[f"分析错误: {error_msg}"]
        )