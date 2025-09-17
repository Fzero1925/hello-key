"""
Advanced Keyword Analysis Module

专门负责关键词分析、价值评估和商业洞察
从关键词获取中分离出的纯分析功能
"""

import os
import sys
import time
import random
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import json
from dataclasses import dataclass, asdict
import logging
import yaml

# 导入编码处理器
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
try:
    from modules.utils.encoding_handler import safe_print, get_encoding_handler
except ImportError:
    def safe_print(text, **kwargs):
        print(text, **kwargs)

# Import deduplication system
try:
    from ..deduplication.keyword_deduplicator import KeywordDeduplicator
    DEDUPLICATION_AVAILABLE = True
except ImportError:
    DEDUPLICATION_AVAILABLE = False

# Import v2 scoring functions
try:
    from .scoring import opportunity_score, estimate_value, estimate_adsense, estimate_amazon, explain_selection, make_revenue_range
except ImportError:
    # Fallback implementation
    def opportunity_score(T, I, S, F, D, d_penalty=0.6):
        base = 0.35*T + 0.30*I + 0.15*S + 0.20*F
        return max(0, min(100, 100*base*(1-0.6*D)))

    def estimate_value(search_volume, opp, ads_params=None, aff_params=None, mode='max'):
        ads_params = ads_params or {"ctr_serp":0.25, "click_share_rank":0.35, "rpm_usd":10}
        aff_params = aff_params or {"ctr_to_amazon":0.12, "cr":0.04, "aov_usd":80, "commission":0.03}
        pv = search_volume * ads_params["ctr_serp"] * ads_params["click_share_rank"]
        ra = (pv/1000.0) * ads_params["rpm_usd"]
        rf = (search_volume*aff_params["ctr_to_amazon"])*aff_params["cr"]*aff_params["aov_usd"]*aff_params["commission"]
        base = max(ra, rf)
        return base * (0.6 + 0.4*opp/100.0)

    def explain_selection(trend_pct, intent_hits, difficulty_label):
        return {"trend": f"Trend: {trend_pct:+.0f}%", "intent": f"Intent: {intent_hits}", "difficulty": difficulty_label}

    def make_revenue_range(v):
        return {"point": v, "range": f"${v*0.75:.0f}–${v*1.25:.0f}/mo"}

# Optional dependencies for analysis enhancement
try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False


@dataclass
class KeywordMetrics:
    """Data class for keyword performance metrics"""
    keyword: str
    search_volume: int
    competition_score: float  # 0-1 scale
    trend_score: float       # 0-1 scale (higher = more trending)
    difficulty_score: float  # 0-1 scale (higher = more difficult)
    commercial_intent: float # 0-1 scale (higher = more commercial)
    suggested_topics: List[str]
    related_queries: List[str]
    seasonal_pattern: Dict[str, float]
    last_updated: datetime
    
    # Keyword Engine v2 enhancements
    opportunity_score: Optional[float] = None      # 0-100 scale (higher = better opportunity)
    est_value_usd: Optional[float] = None          # Estimated monthly revenue in USD
    why_selected: Optional[Dict[str, str]] = None  # Explanation of selection reasons
    revenue_breakdown: Optional[Dict[str, float]] = None  # AdSense vs Amazon breakdown
    site_fit_score: Optional[float] = None         # 0-1 scale (higher = better fit)
    seasonality_score: Optional[float] = None      # 0-1 scale (higher = more seasonal)


class KeywordAnalyzer:
    """
    关键词分析器 - 专门负责关键词价值评估和商业洞察
    不包含数据获取功能，专注于分析能力
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._get_default_config()
        self.cache_dir = "data/keyword_cache"
        self.cache_expiry = timedelta(hours=24)

        # Load Keyword Engine v2 configuration
        self.v2_config = self._load_v2_config()

        # Initialize deduplication system
        self.deduplicator = None
        if DEDUPLICATION_AVAILABLE:
            try:
                self.deduplicator = KeywordDeduplicator()
                logging.getLogger(__name__).info("Deduplication system initialized successfully")
            except Exception as e:
                logging.getLogger(__name__).warning(f"Failed to initialize deduplicator: {e}")

        # Setup logging
        self.logger = logging.getLogger(__name__)

        # Smart home product categories (for analysis reference)
        self.smart_home_categories = {
            'smart_plugs': [
                'smart plug', 'wifi outlet', 'alexa plug', 'google home plug',
                'smart outlet', 'energy monitoring plug', 'outdoor smart plug'
            ],
            'smart_speakers': [
                'alexa echo', 'google home', 'smart speaker', 'voice assistant',
                'echo dot', 'google nest', 'homepod', 'smart display'
            ],
            'security_cameras': [
                'security camera', 'wifi camera', 'outdoor camera', 'doorbell camera',
                'surveillance camera', 'ip camera', 'wireless camera', 'night vision camera'
            ],
            'robot_vacuums': [
                'robot vacuum', 'robotic cleaner', 'automatic vacuum', 'smart vacuum',
                'roomba', 'mapping vacuum', 'self emptying vacuum', 'pet hair vacuum'
            ],
            'smart_thermostats': [
                'smart thermostat', 'wifi thermostat', 'programmable thermostat',
                'nest thermostat', 'ecobee', 'learning thermostat', 'energy saving thermostat'
            ],
            'smart_lighting': [
                'smart bulb', 'led smart light', 'color changing bulb', 'dimmer switch',
                'smart light strip', 'outdoor smart lights', 'motion sensor lights'
            ]
        }

        # Commercial intent indicators
        self.commercial_indicators = [
            'best', 'review', 'buy', 'price', 'cheap', 'deal', 'sale', 'discount',
            'compare', 'vs', 'alternative', 'recommendation', 'guide', 'how to choose'
        ]

        # Optional: Initialize Google Trends for trend analysis
        if PYTRENDS_AVAILABLE:
            try:
                self.pytrends = TrendReq(hl='en-US', tz=360)
                self.logger.info("Google Trends initialized for analysis")
            except Exception as e:
                self.logger.warning(f"Failed to initialize pytrends: {e}")
                self.pytrends = None

        # Create cache directory
        os.makedirs(self.cache_dir, exist_ok=True)



    def infer_category(self, keyword: str) -> str:
        """推断关键词所属的智能家居类别"""
        kw = (keyword or '').lower()
        for cat, seeds in self.smart_home_categories.items():
            if any(s in kw for s in seeds):
                return cat
        return 'general'
    
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

    def _get_default_config(self) -> Dict:
        """Get default configuration settings"""
        return {
            'max_keywords_per_batch': 5,  # Google Trends limit
            'request_delay': 1.0,         # Seconds between requests
            'cache_enabled': True,
            'include_seasonal_data': True,
            'min_search_volume': 100,
            'max_difficulty_score': 0.8,
            'enable_reddit_trends': True,
            'enable_youtube_trends': True,
            'enable_amazon_trends': True,
            'reddit_subreddits': [
                'smarthome', 'homeautomation', 'amazonecho', 'googlehome',
                'homekit', 'homesecurity', 'amazonalexa', 'internetofthings',
                'gadgets', 'technology', 'buyitforlife', 'reviews'
            ],
            'youtube_search_regions': ['US', 'GB', 'CA', 'AU'],
            'max_reddit_posts': 120,  # Increased for larger subreddit list
            'max_youtube_videos': 25
        }
    
    
    def _calculate_trend_score_from_series(self, trend_data: pd.Series) -> float:
        """Calculate a normalized trend score based on recent growth"""
        if len(trend_data) < 2:
            return 0.0
        
        # Recent period (last 30% of data points)
        recent_size = max(1, int(len(trend_data) * 0.3))
        recent_avg = trend_data.tail(recent_size).mean()
        overall_avg = trend_data.mean()
        
        # Calculate growth rate
        if overall_avg > 0:
            growth_rate = (recent_avg - overall_avg) / overall_avg
        else:
            growth_rate = 0
        
        # Normalize to 0-1 scale
        trend_score = min(1.0, max(0.0, (growth_rate + 1) / 2))
        return round(trend_score, 3)
    
    
    def _is_relevant_keyword(self, keyword: str, category: str) -> bool:
        """Check if a keyword is relevant to the smart home category (EXPANDED LOGIC)"""
        keyword_lower = keyword.lower()

        # Category-specific relevance check
        category_terms = self.smart_home_categories.get(category, [])
        for term in category_terms:
            if any(word in keyword_lower for word in term.lower().split()):
                return True

        # EXPANDED: General smart home terms
        smart_home_terms = [
            'smart', 'wifi', 'bluetooth', 'alexa', 'google', 'home', 'automation',
            'iot', 'connected', 'wireless', 'app', 'control', 'remote'
        ]

        # EXPANDED: Specific smart home products
        product_terms = [
            'plug', 'outlet', 'switch', 'dimmer', 'bulb', 'light', 'lamp',
            'camera', 'doorbell', 'lock', 'thermostat', 'sensor', 'detector',
            'hub', 'bridge', 'gateway', 'router', 'speaker', 'display',
            'vacuum', 'robot', 'cleaner', 'security', 'alarm', 'monitor'
        ]

        # EXPANDED: Popular smart home brands
        brand_terms = [
            'ring', 'nest', 'philips', 'hue', 'tp-link', 'kasa', 'wyze',
            'ecobee', 'honeywell', 'arlo', 'eero', 'samsung', 'smartthings',
            'apple', 'homekit', 'amazon', 'echo', 'sonos', 'blink'
        ]

        # EXPANDED: Smart home protocols and technologies
        tech_terms = [
            'zigbee', 'zwave', 'thread', 'matter', 'wifi6', 'mesh',
            'voice', 'assistant', 'siri', 'cortana', 'bixby'
        ]

        # Check all term categories
        all_terms = smart_home_terms + product_terms + brand_terms + tech_terms

        # More lenient matching: if ANY relevant term is found
        for term in all_terms:
            if term in keyword_lower:
                return True

        # Additional patterns for smart home relevance
        smart_patterns = [
            'home security', 'energy saving', 'energy monitor', 'motion detect',
            'temperature control', 'lighting control', 'door lock', 'smart home',
            'home automation', 'voice control', 'mobile app', 'wireless setup'
        ]

        for pattern in smart_patterns:
            if pattern in keyword_lower:
                return True

        return False
    
    def analyze_keyword_metrics(self, keywords: List[str]) -> List[KeywordMetrics]:
        """
        Comprehensive analysis of keyword metrics including difficulty, volume, and intent
        
        Args:
            keywords: List of keywords to analyze
            
        Returns:
            List of KeywordMetrics objects
        """
        metrics_list = []
        
        for keyword in keywords:
            try:
                # Check cache first
                cached_metrics = self._get_cached_metrics(keyword)
                if cached_metrics:
                    metrics_list.append(cached_metrics)
                    continue
                
                # Calculate various metrics
                search_volume = self._estimate_search_volume(keyword)
                competition_score = self._calculate_competition_score(keyword)
                commercial_intent = self._calculate_commercial_intent(keyword)
                difficulty_score = self._calculate_difficulty_score(keyword)
                
                # Get related data
                suggested_topics = self._generate_topic_suggestions(keyword)
                related_queries = self._get_related_queries(keyword)
                seasonal_pattern = self._analyze_seasonal_pattern(keyword)
                
                # Calculate v2 enhanced features
                trend_score = self._calculate_trend_score_from_series(pd.Series([1.0, 1.2, 1.1]))  # Fallback data
                site_fit_score = self._calculate_site_fit_score(keyword)
                seasonality_score = self._calculate_seasonality_score(keyword, seasonal_pattern)
                
                # Calculate opportunity score using v2 algorithm
                opp_score = opportunity_score(
                    T=trend_score,
                    I=commercial_intent,
                    S=seasonality_score,
                    F=site_fit_score,
                    D=difficulty_score,
                    d_penalty=self.v2_config['weights']['D_penalty']
                )
                
                # Calculate estimated value
                est_value = estimate_value(
                    search_volume=search_volume,
                    opp_score=opp_score,
                    ads_params=self.v2_config['adsense'],
                    aff_params=self.v2_config['amazon'],
                    mode=self.v2_config['mode']
                )
                
                # Generate revenue breakdown
                revenue_breakdown = {
                    'adsense': estimate_adsense(search_volume, **self.v2_config['adsense']),
                    'amazon': estimate_amazon(search_volume, **self.v2_config['amazon'])
                }
                
                # Generate explanation
                trend_pct = (trend_score - 0.5) * 100  # Convert to percentage change
                intent_hits = self._identify_intent_words(keyword)
                difficulty_label = self._get_difficulty_label(difficulty_score)
                why_selected = explain_selection(trend_pct, intent_hits, difficulty_label)
                
                # Create metrics object
                metrics = KeywordMetrics(
                    keyword=keyword,
                    search_volume=search_volume,
                    competition_score=competition_score,
                    trend_score=trend_score,
                    difficulty_score=difficulty_score,
                    commercial_intent=commercial_intent,
                    suggested_topics=suggested_topics,
                    related_queries=related_queries,
                    seasonal_pattern=seasonal_pattern,
                    last_updated=datetime.now(),
                    # v2 enhancements
                    opportunity_score=opp_score,
                    est_value_usd=est_value,
                    why_selected=why_selected,
                    revenue_breakdown=revenue_breakdown,
                    site_fit_score=site_fit_score,
                    seasonality_score=seasonality_score
                )
                
                metrics_list.append(metrics)
                
                # Cache the results
                self._cache_metrics(metrics)

                # Respectful delay
                time.sleep(0.5)

            except Exception as e:
                safe_print(f"分析关键词'{keyword}'时出错: {str(e)}")
                continue
        
        return metrics_list
    
    def _estimate_search_volume(self, keyword: str) -> int:
        """Estimate search volume using available data sources"""
        # This is a simplified estimation - in production you'd use paid APIs
        base_volume = 1000
        
        # Adjust based on keyword characteristics
        word_count = len(keyword.split())
        if word_count == 1:
            base_volume *= 2  # Single words tend to have higher volume
        elif word_count > 3:
            base_volume *= 0.5  # Long-tail keywords have lower volume
        
        # Adjust for commercial intent
        commercial_intent = self._calculate_commercial_intent(keyword)
        base_volume = int(base_volume * (1 + commercial_intent))
        
        return max(100, base_volume)
    
    def _calculate_competition_score(self, keyword: str) -> float:
        """Calculate competition score based on keyword characteristics"""
        score = 0.5  # Base competition level
        
        # High competition indicators
        high_comp_terms = ['best', 'top', 'review', 'vs', 'comparison']
        if any(term in keyword.lower() for term in high_comp_terms):
            score += 0.2
        
        # Brand keywords typically have higher competition
        brands = ['amazon', 'google', 'apple', 'samsung', 'philips', 'nest']
        if any(brand in keyword.lower() for brand in brands):
            score += 0.1
        
        # Generic vs specific keywords
        if len(keyword.split()) == 1:
            score += 0.2  # Single words more competitive
        
        return min(1.0, max(0.0, score))
    
    def _calculate_commercial_intent(self, keyword: str) -> float:
        """Calculate commercial intent score"""
        keyword_lower = keyword.lower()
        intent_score = 0.0
        
        # Strong commercial indicators
        strong_indicators = ['buy', 'price', 'deal', 'sale', 'cheap', 'discount', 'coupon']
        for indicator in strong_indicators:
            if indicator in keyword_lower:
                intent_score += 0.2
        
        # Medium commercial indicators  
        medium_indicators = ['best', 'review', 'compare', 'vs', 'alternative', 'recommendation']
        for indicator in medium_indicators:
            if indicator in keyword_lower:
                intent_score += 0.1
        
        # Product-specific terms
        product_terms = ['smart', 'wifi', 'bluetooth', 'wireless', 'device']
        if any(term in keyword_lower for term in product_terms):
            intent_score += 0.05
        
        return min(1.0, intent_score)
    
    def _calculate_difficulty_score(self, keyword: str) -> float:
        """Calculate keyword difficulty score"""
        # Simplified difficulty calculation
        difficulty = 0.3  # Base difficulty
        
        # Length affects difficulty
        word_count = len(keyword.split())
        if word_count == 1:
            difficulty += 0.4  # Single words are harder
        elif word_count > 4:
            difficulty -= 0.2  # Long-tail easier
        
        # Commercial keywords are more difficult
        commercial_score = self._calculate_commercial_intent(keyword)
        difficulty += commercial_score * 0.3
        
        return min(1.0, max(0.0, difficulty))
    
    def _generate_topic_suggestions(self, keyword: str) -> List[str]:
        """Generate related topic suggestions for content creation"""
        suggestions = []
        keyword_words = keyword.lower().split()
        
        # Common content angles for smart home products
        content_angles = [
            f"How to choose the best {keyword}",
            f"{keyword} installation guide",
            f"{keyword} troubleshooting tips",
            f"{keyword} vs alternatives",
            f"Budget {keyword} options",
            f"{keyword} for beginners",
            f"Professional {keyword} review",
            f"{keyword} buying guide 2025"
        ]
        
        # Filter relevant suggestions
        for angle in content_angles[:5]:  # Limit to 5 suggestions
            suggestions.append(angle)
        
        return suggestions
    
    def _get_related_queries(self, keyword: str) -> List[str]:
        """Get related query suggestions"""
        related = []
        
        # Generate variations
        base_variations = [
            f"best {keyword}",
            f"{keyword} review",
            f"cheap {keyword}",
            f"{keyword} 2025",
            f"{keyword} comparison"
        ]
        
        related.extend(base_variations[:3])  # Limit to 3
        return related
    
    def _calculate_site_fit_score(self, keyword: str) -> float:
        """计算关键词与网站匹配度评分"""
        keyword_lower = keyword.lower()

        # 智能家居相关性评分
        if self._is_relevant_keyword(keyword, 'general'):
            base_score = 0.8
        else:
            base_score = 0.4

        # 根据关键词类型调整
        if any(term in keyword_lower for term in ['best', 'review', 'guide']):
            base_score += 0.1  # 内容友好

        if any(term in keyword_lower for term in ['smart', 'wifi', 'automation']):
            base_score += 0.1  # 高度相关

        return min(1.0, base_score)

    def _calculate_seasonality_score(self, keyword: str, seasonal_pattern: Dict[str, float]) -> float:
        """计算季节性评分"""
        if not seasonal_pattern:
            return 0.5  # 默认中等季节性

        # 计算季节性变化程度
        values = list(seasonal_pattern.values())
        if len(values) < 2:
            return 0.5

        max_val = max(values)
        min_val = min(values)

        # 季节性越强，评分越高（对于某些产品是好事）
        if max_val > 0:
            seasonality = (max_val - min_val) / max_val
        else:
            seasonality = 0

        return min(1.0, max(0.0, seasonality))

    def _identify_intent_words(self, keyword: str) -> List[str]:
        """识别商业意图词汇列表"""
        keyword_lower = keyword.lower()
        intent_words = []

        for indicator in self.commercial_indicators:
            if indicator in keyword_lower:
                intent_words.append(indicator)

        return intent_words

    def _get_difficulty_label(self, difficulty_score: float) -> str:
        """获取难度标签"""
        if difficulty_score <= 0.3:
            return "简单"
        elif difficulty_score <= 0.6:
            return "中等"
        else:
            return "困难"

    def _analyze_seasonal_pattern(self, keyword: str) -> Dict[str, float]:
        """Analyze seasonal trends for the keyword"""
        # This is a simplified version - real implementation would use historical data
        seasons = {
            'spring': 0.8,
            'summer': 1.0,
            'fall': 0.9,
            'winter': 1.1  # Higher in winter (indoor activities)
        }
        
        # Adjust based on keyword type
        if 'outdoor' in keyword.lower():
            seasons.update({
                'spring': 1.2,
                'summer': 1.3,
                'fall': 0.7,
                'winter': 0.3
            })
        elif 'holiday' in keyword.lower() or 'christmas' in keyword.lower():
            seasons.update({
                'spring': 0.5,
                'summer': 0.4,
                'fall': 0.8,
                'winter': 1.5
            })
        
        return seasons
    
    def _get_cached_metrics(self, keyword: str) -> Optional[KeywordMetrics]:
        """Retrieve cached keyword metrics if available and not expired"""
        if not self.config['cache_enabled']:
            return None
        
        cache_file = os.path.join(self.cache_dir, f"{keyword.replace(' ', '_')}.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Check if cache is expired
                last_updated = datetime.fromisoformat(data['last_updated'])
                if datetime.now() - last_updated < self.cache_expiry:
                    # Convert back to KeywordMetrics object
                    data['last_updated'] = last_updated
                    return KeywordMetrics(**data)
            except Exception as e:
                safe_print(f"读取缓存失败 {keyword}: {str(e)}")
        
        return None
    
    def _cache_metrics(self, metrics: KeywordMetrics):
        """Cache keyword metrics to disk"""
        if not self.config['cache_enabled']:
            return
        
        cache_file = os.path.join(self.cache_dir, f"{metrics.keyword.replace(' ', '_')}.json")
        
        try:
            # Convert to dict and handle datetime serialization
            data = asdict(metrics)
            data['last_updated'] = data['last_updated'].isoformat()
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            safe_print(f"缓存指标失败 {metrics.keyword}: {str(e)}")
    
    
    def export_keyword_report(self, metrics_list: List[KeywordMetrics], 
                            output_file: str = None) -> str:
        """Export comprehensive keyword analysis report"""
        if not output_file:
            output_file = f"data/keyword_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        
        # Convert to DataFrame for easy export
        report_data = []
        for metrics in metrics_list:
            row = {
                'keyword': metrics.keyword,
                'search_volume': metrics.search_volume,
                'competition_score': metrics.competition_score,
                'trend_score': metrics.trend_score,
                'difficulty_score': metrics.difficulty_score,
                'commercial_intent': metrics.commercial_intent,
                'suggested_topics': '; '.join(metrics.suggested_topics),
                'related_queries': '; '.join(metrics.related_queries),
                'last_updated': metrics.last_updated
            }
            report_data.append(row)
        
        df = pd.DataFrame(report_data)
        df.to_csv(output_file, index=False)
        
        return output_file
    

# 示例使用
if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.INFO)

    # 创建关键词分析器
    analyzer = KeywordAnalyzer()

    safe_print("=== 关键词分析器测试 ===")

    # 测试关键词列表
    test_keywords = [
        'smart plug alexa compatible',
        'best robot vacuum pet hair',
        'outdoor security camera wireless',
        'smart thermostat energy saving',
        'wireless doorbell camera'
    ]

    safe_print("\n分析关键词指标...")
    metrics = analyzer.analyze_keyword_metrics(test_keywords)

    for metric in metrics:
        safe_print(f"\n关键词: {metric.keyword}")
        safe_print(f"  搜索量: {metric.search_volume:,}")
        safe_print(f"  商业意图: {metric.commercial_intent:.2f}")
        safe_print(f"  竞争度: {metric.competition_score:.2f}")
        safe_print(f"  趋势评分: {metric.trend_score:.2f}")
        safe_print(f"  难度评分: {metric.difficulty_score:.2f}")
        safe_print(f"  建议话题: {'; '.join(metric.suggested_topics[:2])}")

    # 导出报告
    safe_print("\n导出分析报告...")
    report_file = analyzer.export_keyword_report(metrics)
    safe_print(f"报告已导出到: {report_file}")

    # 测试单个关键词深度分析
    safe_print("\n单个关键词深度分析...")
    single_keyword = "smart home automation system"
    category = analyzer.infer_category(single_keyword)
    commercial_intent = analyzer._calculate_commercial_intent(single_keyword)
    difficulty = analyzer._calculate_difficulty_score(single_keyword)

    safe_print(f"关键词: {single_keyword}")
    safe_print(f"推断类别: {category}")
    safe_print(f"商业意图: {commercial_intent:.2f}")
    safe_print(f"难度评分: {difficulty:.2f}")

    safe_print("\n分析完成！此模块专注于关键词价值评估和商业洞察。")
