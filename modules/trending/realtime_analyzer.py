#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时关键词分析和热点追踪系统 - Realtime Trending Keywords Analyzer
针对欧美时区优化，12小时内热点检测，商业价值实时评估

核心功能：
1. 实时Google Trends分析（每2小时更新）
2. 欧美时区优化的热点检测
3. 商业价值和竞争度即时评估  
4. 热点话题自动触发文章生成
5. 多数据源交叉验证（Reddit, YouTube, Amazon）
"""

import os
import sys
import codecs
import time
import json
import requests
import asyncio
import aiohttp
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple, Optional, Any
import logging
from dataclasses import dataclass, asdict
import pytz
import random
import yaml

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

# 解决Windows编码问题
if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# 时区配置
US_EASTERN = pytz.timezone('US/Eastern')
US_PACIFIC = pytz.timezone('US/Pacific')  
UK_LONDON = pytz.timezone('Europe/London')
CHINA_TIMEZONE = pytz.timezone('Asia/Shanghai')

@dataclass
class TrendingTopic:
    """实时热点话题数据结构"""
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


class RealtimeTrendingAnalyzer:
    """实时热点分析器 - 针对智能家居市场优化"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.data_dir = "data/realtime_trends"
        self.cache_dir = "data/trend_cache"
        self.trends_history = "data/trends_history"
        
        # Load v2 configuration
        self.v2_config = self._load_v2_config()
        
        # 创建必要的目录
        for directory in [self.data_dir, self.cache_dir, self.trends_history]:
            os.makedirs(directory, exist_ok=True)
        
        # 智能家居相关的种子关键词 - 扩展版本
        self.smart_home_seeds = {
            'smart_plugs': [
                'smart plug', 'wifi outlet', 'alexa plug', 'smart switch',
                'energy monitoring plug', 'outdoor smart plug', 'voice control outlet'
            ],
            'security_devices': [
                'security camera', 'video doorbell', 'smart lock', 'doorbell cam',
                'wireless camera', 'outdoor camera', 'home security system'
            ],
            'cleaning_devices': [
                'robot vacuum', 'robotic cleaner', 'smart mop', 'pet hair vacuum',
                'self emptying vacuum', 'mapping vacuum', 'quiet robot vacuum'
            ],
            'climate_control': [
                'smart thermostat', 'wifi thermostat', 'nest thermostat',
                'programmable thermostat', 'energy saving thermostat'
            ],
            'lighting': [
                'smart bulb', 'color changing bulb', 'wifi light', 'smart dimmer',
                'led smart bulb', 'outdoor smart lights', 'motion sensor lights'
            ],
            'speakers_displays': [
                'smart speaker', 'alexa echo', 'google nest', 'smart display',
                'voice assistant', 'smart home hub', 'wifi speaker'
            ],
            'emerging_categories': [
                'smart mirror', 'smart doorbell', 'smart garage door', 'smart garden',
                'smart pet feeder', 'smart air purifier', 'smart blinds'
            ]
        }
        
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

    def _setup_logging(self) -> logging.Logger:
        """设置日志系统"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('data/realtime_trends.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def get_optimal_analysis_time(self) -> Dict[str, Any]:
        """获取欧美时区的最佳分析时间"""
        now_utc = datetime.now(timezone.utc)
        
        # 转换到主要时区
        us_east = now_utc.astimezone(US_EASTERN)
        us_west = now_utc.astimezone(US_PACIFIC)
        uk_time = now_utc.astimezone(UK_LONDON)
        
        # 判断是否为欧美的活跃时间（早上6点-晚上10点）
        active_zones = []
        
        if 6 <= us_east.hour <= 22:
            active_zones.append(('US_East', us_east.hour))
        if 6 <= us_west.hour <= 22:
            active_zones.append(('US_West', us_west.hour))
        if 6 <= uk_time.hour <= 22:
            active_zones.append(('UK', uk_time.hour))
        
        # 计算最佳分析权重
        analysis_weight = len(active_zones) / 3.0
        is_prime_time = analysis_weight >= 0.5
        
        return {
            'timestamp': now_utc.isoformat(),
            'active_zones': active_zones,
            'analysis_weight': analysis_weight,
            'is_prime_time': is_prime_time,
            'us_east_hour': us_east.hour,
            'us_west_hour': us_west.hour,
            'uk_hour': uk_time.hour,
            'recommendation': 'ANALYZE' if is_prime_time else 'WAIT'
        }
    
    async def analyze_realtime_trends(self, force_analysis: bool = False) -> List[TrendingTopic]:
        """实时分析当前热门趋势"""
        timing_info = self.get_optimal_analysis_time()
        
        if not force_analysis and not timing_info['is_prime_time']:
            self.logger.info(f"Not prime time for analysis. Weight: {timing_info['analysis_weight']}")
            return []
        
        self.logger.info(f"🔥 Starting realtime trend analysis. Active zones: {timing_info['active_zones']}")
        
        trending_topics = []
        
        # 并行分析多个数据源
        tasks = [
            self._analyze_google_trends_realtime(),
            self._analyze_social_signals(),
            self._analyze_search_volume_spikes(),
            self._analyze_seasonal_opportunities()
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Task {i} failed: {result}")
                elif isinstance(result, list):
                    trending_topics.extend(result)
                    
        except Exception as e:
            self.logger.error(f"Error in parallel analysis: {e}")
        
        # 去重和排序
        unique_topics = self._deduplicate_and_rank(trending_topics)
        
        # 保存结果
        self._save_trending_results(unique_topics, timing_info)
        
        return unique_topics[:10]  # 返回前10个最热门的
    
    async def _analyze_google_trends_realtime(self) -> List[TrendingTopic]:
        """分析Google Trends实时数据"""
        topics = []
        
        try:
            # 模拟Google Trends数据（实际部署时连接真实API）
            current_trends = await self._get_simulated_google_trends()
            
            for trend_data in current_trends:
                if self._is_smart_home_related(trend_data['query']):
                    topic = TrendingTopic(
                        keyword=trend_data['query'],
                        category=self._categorize_keyword(trend_data['query']),
                        trend_score=trend_data['score'],
                        commercial_value=self._calculate_commercial_value(trend_data['query']),
                        search_volume_est=trend_data['volume'],
                        competition_level=trend_data['competition'],
                        urgency_score=self._calculate_urgency(trend_data),
                        sources=['google_trends'],
                        time_detected=datetime.now(timezone.utc),
                        peak_regions=trend_data.get('regions', ['US', 'UK']),
                        related_terms=trend_data.get('related', []),
                        business_reasoning=self._generate_business_reasoning(trend_data),
                        content_angle=self._suggest_content_angle(trend_data['query']),
                        estimated_revenue=self._estimate_revenue_potential(trend_data),
                        social_signals=trend_data.get('social', {})
                    )
                    topics.append(topic)
                    
        except Exception as e:
            self.logger.error(f"Google Trends analysis failed: {e}")
        
        return topics
    
    async def _analyze_social_signals(self) -> List[TrendingTopic]:
        """分析社交媒体信号"""
        topics = []
        
        # Reddit热点分析
        reddit_trends = await self._get_reddit_trending()
        for trend in reddit_trends:
            if self._is_smart_home_related(trend['title']):
                topic = TrendingTopic(
                    keyword=self._extract_keyword_from_title(trend['title']),
                    category=self._categorize_keyword(trend['title']),
                    trend_score=min(trend['score'] / 1000, 1.0),
                    commercial_value=self._calculate_commercial_value(trend['title']),
                    search_volume_est=trend['score'] * 10,
                    competition_level='Medium',
                    urgency_score=min(trend['comments'] / 100, 1.0),
                    sources=['reddit'],
                    time_detected=datetime.now(timezone.utc),
                    peak_regions=['US', 'UK', 'CA'],
                    related_terms=[],
                    business_reasoning=f"Reddit engagement: {trend['score']} upvotes, {trend['comments']} comments",
                    content_angle=self._suggest_content_angle(trend['title']),
                    estimated_revenue="$200-500/month",
                    social_signals={'reddit_upvotes': trend['score'], 'reddit_comments': trend['comments']}
                )
                topics.append(topic)
        
        return topics
    
    async def _analyze_search_volume_spikes(self) -> List[TrendingTopic]:
        """分析搜索量激增的关键词"""
        topics = []
        
        # 模拟搜索量激增检测
        spike_keywords = [
            {
                'keyword': 'smart plug energy monitoring',
                'current_volume': 25000,
                'baseline_volume': 15000,
                'spike_percentage': 67,
                'regions': ['US', 'UK', 'CA'],
                'trigger_event': 'Energy cost concerns trending'
            },
            {
                'keyword': 'robot vacuum black friday',
                'current_volume': 45000,
                'baseline_volume': 12000,
                'spike_percentage': 275,
                'regions': ['US', 'UK'],
                'trigger_event': 'Pre-holiday shopping surge'
            },
            {
                'keyword': 'outdoor security camera wireless',
                'current_volume': 32000,
                'baseline_volume': 20000,
                'spike_percentage': 60,
                'regions': ['US', 'CA', 'AU'],
                'trigger_event': 'Home security awareness increase'
            }
        ]
        
        for spike in spike_keywords:
            if spike['spike_percentage'] > 50:  # 只关注50%以上的激增
                topic = TrendingTopic(
                    keyword=spike['keyword'],
                    category=self._categorize_keyword(spike['keyword']),
                    trend_score=min(spike['spike_percentage'] / 100, 1.0),
                    commercial_value=0.9,  # 搜索激增通常表示高商业价值
                    search_volume_est=spike['current_volume'],
                    competition_level='Medium-High',
                    urgency_score=0.95,  # 激增关键词具有高紧急度
                    sources=['search_volume_monitor'],
                    time_detected=datetime.now(timezone.utc),
                    peak_regions=spike['regions'],
                    related_terms=[],
                    business_reasoning=f"Search volume spiked {spike['spike_percentage']}% due to: {spike['trigger_event']}",
                    content_angle='Timely buying guide capitalizing on current interest surge',
                    estimated_revenue="$400-800/month",
                    social_signals={}
                )
                topics.append(topic)
        
        return topics
    
    async def _analyze_seasonal_opportunities(self) -> List[TrendingTopic]:
        """分析季节性机会"""
        topics = []
        current_month = datetime.now().month
        
        # 季节性关键词映射
        seasonal_keywords = {
            9: ['back to school smart home', 'dorm room automation'],  # September
            10: ['halloween smart lights', 'security camera motion'],  # October  
            11: ['black friday smart plugs', 'cyber monday deals'],    # November
            12: ['christmas smart lights', 'holiday automation'],      # December
            1: ['new year smart home', 'resolution automation'],       # January
            2: ['valentine smart lights', 'romantic automation'],      # February
            3: ['spring cleaning robot', 'outdoor camera setup'],     # March
            4: ['easter smart decorations', 'garden automation'],     # April
            5: ['mother day smart home', 'gift automation'],          # May
            6: ['father day tech gifts', 'summer automation'],        # June
            7: ['summer outdoor smart', 'vacation security'],         # July
            8: ['back school smart tech', 'student automation']       # August
        }
        
        if current_month in seasonal_keywords:
            for keyword in seasonal_keywords[current_month]:
                topic = TrendingTopic(
                    keyword=keyword,
                    category=self._categorize_keyword(keyword),
                    trend_score=0.75,
                    commercial_value=0.85,
                    search_volume_est=8000 + random.randint(2000, 8000),
                    competition_level='Low-Medium',
                    urgency_score=0.8,
                    sources=['seasonal_analysis'],
                    time_detected=datetime.now(timezone.utc),
                    peak_regions=['US', 'UK', 'CA'],
                    related_terms=[],
                    business_reasoning=f"Seasonal opportunity for {current_month:02d} month - lower competition with targeted demand",
                    content_angle='Seasonal buying guide with timely recommendations',
                    estimated_revenue="$300-600/month",
                    social_signals={}
                )
                topics.append(topic)
        
        return topics
    
    def _is_smart_home_related(self, text: str) -> bool:
        """判断文本是否与智能家居相关"""
        text_lower = text.lower()
        
        # 智能家居相关术语
        smart_home_terms = [
            'smart', 'wifi', 'bluetooth', 'alexa', 'google', 'nest',
            'automation', 'iot', 'connected', 'wireless', 'app control',
            'voice control', 'home assistant', 'smart home', 'robot',
            'security camera', 'doorbell', 'thermostat', 'plug', 'bulb',
            'speaker', 'display', 'hub', 'sensor', 'monitor'
        ]
        
        return any(term in text_lower for term in smart_home_terms)
    
    def _categorize_keyword(self, keyword: str) -> str:
        """为关键词分类"""
        keyword_lower = keyword.lower()
        
        category_mapping = {
            'smart_plugs': ['plug', 'outlet', 'switch'],
            'security_devices': ['camera', 'doorbell', 'lock', 'security'],
            'cleaning_devices': ['vacuum', 'robot', 'cleaner', 'mop'],
            'climate_control': ['thermostat', 'temperature', 'heating', 'cooling'],
            'lighting': ['bulb', 'light', 'lamp', 'dimmer', 'led'],
            'speakers_displays': ['speaker', 'echo', 'display', 'assistant'],
            'general_smart_home': ['smart home', 'automation', 'hub', 'system']
        }
        
        for category, terms in category_mapping.items():
            if any(term in keyword_lower for term in terms):
                return category
        
        return 'general_smart_home'
    
    def _calculate_commercial_value(self, keyword: str) -> float:
        """计算关键词的商业价值"""
        keyword_lower = keyword.lower()
        value = 0.5  # 基础值
        
        # 商业意图信号
        for signal in self.commercial_signals:
            if signal in keyword_lower:
                value += 0.1
        
        # 品牌关键词加分
        brands = ['amazon', 'google', 'nest', 'alexa', 'philips', 'ring', 'arlo']
        if any(brand in keyword_lower for brand in brands):
            value += 0.2
        
        # 年份关键词加分（时效性）
        if '2025' in keyword_lower:
            value += 0.15
        
        return min(value, 1.0)
    
    def _calculate_urgency(self, trend_data: Dict) -> float:
        """计算紧急度评分"""
        urgency = 0.5
        
        # 基于关键词中的紧急信号
        query_lower = trend_data['query'].lower()
        for signal, weight in self.urgency_signals.items():
            if signal in query_lower:
                urgency = max(urgency, weight)
        
        # 基于趋势评分
        if trend_data['score'] > 0.8:
            urgency += 0.2
        
        return min(urgency, 1.0)
    
    def _generate_business_reasoning(self, trend_data: Dict) -> str:
        """生成商业推理分析"""
        query = trend_data['query']
        score = trend_data['score']
        volume = trend_data['volume']
        
        reasoning_templates = [
            f"High trend score ({score:.2f}) with {volume:,} estimated searches indicates strong market interest",
            f"Rising search volume ({volume:,}) suggests emerging opportunity with commercial potential",
            f"Trending keyword with {score:.2f} momentum score - ideal for content creation",
            f"Market demand signal: {volume:,} searches with {score:.2f} trend acceleration"
        ]
        
        return random.choice(reasoning_templates)
    
    def _suggest_content_angle(self, keyword: str) -> str:
        """建议内容角度"""
        keyword_lower = keyword.lower()
        
        if any(word in keyword_lower for word in ['best', 'top', 'review']):
            return "Comprehensive buying guide with honest product comparisons"
        elif 'vs' in keyword_lower:
            return "Head-to-head product comparison with clear winner recommendation"
        elif any(word in keyword_lower for word in ['how', 'guide', 'setup']):
            return "Step-by-step tutorial with practical tips and troubleshooting"
        elif '2025' in keyword_lower:
            return "Future-focused guide with latest technology trends and predictions"
        else:
            return "In-depth product analysis with real-world testing and recommendations"
    
    def _estimate_revenue_potential(self, trend_data: Dict) -> str:
        """估算收益潜力 - 使用v2精确模型"""
        volume = trend_data.get('volume', 0)
        competition = trend_data.get('competition', 'Medium')
        
        # Calculate difficulty score from competition level
        difficulty_map = {'Low': 0.2, 'Medium': 0.5, 'High': 0.8}
        difficulty = difficulty_map.get(competition, 0.5)
        
        # Estimate basic opportunity score for revenue calculation
        # For trending analysis, assume moderate values for other factors
        estimated_opp_score = 100 * (1 - 0.6 * difficulty)  # Simplified calculation
        
        try:
            # Use v2 precise revenue estimation
            est_value = estimate_value(
                search_volume=volume,
                opp_score=estimated_opp_score,
                ads_params=self.v2_config['adsense'],
                aff_params=self.v2_config['amazon'],
                mode=self.v2_config['mode']
            )
            
            # Generate human-friendly range
            revenue_range = make_revenue_range(est_value)
            return revenue_range['range']
            
        except Exception as e:
            self.logger.warning(f"v2 revenue calculation failed: {e}, using fallback")
            # Fallback to original logic
            if volume > 20000 and competition == 'Low':
                return "$500-1000/month"
            elif volume > 15000 and competition == 'Medium':
                return "$300-600/month"
            elif volume > 10000:
                return "$200-400/month"
            else:
                return "$100-250/month"
    
    def _extract_keyword_from_title(self, title: str) -> str:
        """从标题中提取关键词"""
        # 简化的关键词提取逻辑
        title_lower = title.lower()
        
        for category_keywords in self.smart_home_seeds.values():
            for keyword in category_keywords:
                if keyword in title_lower:
                    return keyword
        
        # 如果没有找到匹配的种子关键词，返回前几个重要词
        words = title_lower.split()[:3]
        return ' '.join(words)
    
    def _deduplicate_and_rank(self, topics: List[TrendingTopic]) -> List[TrendingTopic]:
        """去重并按优先级排序"""
        # 按关键词去重
        unique_topics = {}
        for topic in topics:
            if topic.keyword not in unique_topics:
                unique_topics[topic.keyword] = topic
            else:
                # 保留趋势评分更高的
                if topic.trend_score > unique_topics[topic.keyword].trend_score:
                    unique_topics[topic.keyword] = topic
        
        # 按综合评分排序
        sorted_topics = sorted(
            unique_topics.values(),
            key=lambda t: (t.trend_score * 0.4 + t.commercial_value * 0.3 + t.urgency_score * 0.3),
            reverse=True
        )
        
        return sorted_topics
    
    def _save_trending_results(self, topics: List[TrendingTopic], timing_info: Dict):
        """保存分析结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # 保存详细结果
        results = {
            'timestamp': timestamp,
            'timing_info': timing_info,
            'topics_count': len(topics),
            'topics': [asdict(topic) for topic in topics]
        }
        
        filename = f"{self.data_dir}/trending_analysis_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        # 保存简化版本用于快速访问
        simplified = [
            {
                'keyword': t.keyword,
                'category': t.category,
                'trend_score': t.trend_score,
                'commercial_value': t.commercial_value,
                'urgency_score': t.urgency_score,
                'business_reasoning': t.business_reasoning,
                'estimated_revenue': t.estimated_revenue
            }
            for t in topics[:5]
        ]
        
        with open(f"{self.data_dir}/current_trends.json", 'w', encoding='utf-8') as f:
            json.dump(simplified, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"📊 Saved {len(topics)} trending topics to {filename}")
    
    async def _get_simulated_google_trends(self) -> List[Dict]:
        """模拟Google Trends数据（开发阶段使用）"""
        # 实际部署时这里会连接真实的Google Trends API
        simulated_trends = [
            {
                'query': 'smart plug energy monitoring 2025',
                'score': 0.89,
                'volume': 24000,
                'competition': 'Medium',
                'regions': ['US', 'UK', 'CA'],
                'related': ['energy saving', 'wifi smart plug', 'alexa compatible'],
                'social': {'mentions': 145, 'sentiment': 0.8}
            },
            {
                'query': 'robot vacuum pet hair reviews',
                'score': 0.92,
                'volume': 31000,
                'competition': 'High',
                'regions': ['US', 'UK', 'AU'],
                'related': ['pet-friendly vacuum', 'automatic cleaning', 'smart mapping'],
                'social': {'mentions': 203, 'sentiment': 0.9}
            },
            {
                'query': 'wireless security camera solar',
                'score': 0.85,
                'volume': 18500,
                'competition': 'Low-Medium',
                'regions': ['US', 'CA', 'AU'],
                'related': ['outdoor camera', 'battery powered', 'wireless security'],
                'social': {'mentions': 87, 'sentiment': 0.7}
            },
            {
                'query': 'smart thermostat nest vs ecobee',
                'score': 0.78,
                'volume': 15200,
                'competition': 'High',
                'regions': ['US', 'CA'],
                'related': ['smart climate control', 'energy efficiency', 'home automation'],
                'social': {'mentions': 164, 'sentiment': 0.8}
            },
            {
                'query': 'color changing smart bulbs alexa',
                'score': 0.81,
                'volume': 19800,
                'competition': 'Medium',
                'regions': ['US', 'UK', 'DE'],
                'related': ['rgb lighting', 'voice control', 'mood lighting'],
                'social': {'mentions': 119, 'sentiment': 0.9}
            }
        ]
        
        # 添加随机变化以模拟实时性
        for trend in simulated_trends:
            trend['score'] += random.uniform(-0.1, 0.1)
            trend['volume'] += random.randint(-2000, 3000)
            trend['score'] = max(0.1, min(1.0, trend['score']))
            trend['volume'] = max(1000, trend['volume'])
        
        return simulated_trends
    
    async def _get_reddit_trending(self) -> List[Dict]:
        """获取Reddit热门话题（模拟数据）"""
        reddit_trends = [
            {
                'title': 'Best smart plug for energy monitoring in 2025?',
                'score': 342,
                'comments': 67,
                'subreddit': 'smarthome'
            },
            {
                'title': 'Robot vacuum recommendations for pet owners',
                'score': 598,
                'comments': 134,
                'subreddit': 'homeautomation'
            },
            {
                'title': 'Outdoor security camera setup without wiring',
                'score': 276,
                'comments': 45,
                'subreddit': 'homesecurity'
            }
        ]
        
        return reddit_trends
    
    def generate_market_opportunities(self, trending_topics: List[TrendingTopic]) -> List[MarketOpportunity]:
        """基于热门话题生成市场机会分析"""
        opportunities = []
        
        for topic in trending_topics[:5]:  # 分析前5个热门话题
            opportunity = MarketOpportunity(
                keyword=topic.keyword,
                opportunity_score=self._calculate_opportunity_score(topic),
                competition_gap=self._analyze_competition_gap(topic),
                revenue_potential=topic.estimated_revenue,
                time_sensitivity=self._determine_time_sensitivity(topic),
                recommended_action=self._recommend_action(topic),
                content_strategy=self._suggest_content_strategy(topic)
            )
            opportunities.append(opportunity)
        
        return opportunities
    
    def _calculate_opportunity_score(self, topic: TrendingTopic) -> float:
        """计算市场机会评分"""
        # 综合评分：趋势 * 商业价值 * (1 - 竞争度/5)
        competition_factor = {
            'Low': 0.1, 'Low-Medium': 0.25, 'Medium': 0.5, 
            'Medium-High': 0.75, 'High': 0.9
        }.get(topic.competition_level, 0.5)
        
        opportunity = (topic.trend_score * 0.4 + 
                      topic.commercial_value * 0.4 + 
                      (1 - competition_factor) * 0.2)
        
        return min(1.0, opportunity)
    
    def _analyze_competition_gap(self, topic: TrendingTopic) -> str:
        """分析竞争缺口"""
        if topic.competition_level in ['Low', 'Low-Medium']:
            return "Limited quality content available - excellent opportunity for authoritative guide"
        elif topic.competition_level == 'Medium':
            return "Moderate competition - focus on unique angle or superior depth"
        else:
            return "High competition - requires exceptional quality and unique positioning"
    
    def _determine_time_sensitivity(self, topic: TrendingTopic) -> str:
        """确定时间敏感性"""
        if topic.urgency_score > 0.8:
            return "URGENT"
        elif topic.urgency_score > 0.6:
            return "HIGH"
        elif topic.urgency_score > 0.4:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _recommend_action(self, topic: TrendingTopic) -> str:
        """推荐行动方案"""
        if topic.urgency_score > 0.8 and topic.commercial_value > 0.7:
            return "IMMEDIATE CONTENT CREATION - High priority, immediate article generation recommended"
        elif topic.trend_score > 0.8:
            return "FAST TRACK - Create content within 24-48 hours to capitalize on trend"
        elif topic.commercial_value > 0.8:
            return "STRATEGIC CONTENT - Plan comprehensive guide to capture long-term value"
        else:
            return "MONITOR - Track trend development before content creation"
    
    def _suggest_content_strategy(self, topic: TrendingTopic) -> str:
        """建议内容策略"""
        strategies = {
            'URGENT': "Quick publication with high-value insights, follow up with comprehensive guide",
            'HIGH': "Focus on trending angle while maintaining quality and authority",
            'MEDIUM': "Comprehensive analysis with unique positioning and superior depth",
            'LOW': "Evergreen content approach with focus on long-term SEO value"
        }
        
        time_sensitivity = self._determine_time_sensitivity(topic)
        return strategies.get(time_sensitivity, "Balanced approach with quality focus")


# 主要接口函数
async def analyze_current_trends(force_analysis: bool = False) -> Dict[str, Any]:
    """分析当前趋势的主要接口"""
    analyzer = RealtimeTrendingAnalyzer()
    
    trending_topics = await analyzer.analyze_realtime_trends(force_analysis)
    market_opportunities = analyzer.generate_market_opportunities(trending_topics)
    
    return {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'trending_topics': [asdict(topic) for topic in trending_topics],
        'market_opportunities': [asdict(opp) for opp in market_opportunities],
        'analysis_summary': {
            'total_topics': len(trending_topics),
            'urgent_topics': len([t for t in trending_topics if t.urgency_score > 0.8]),
            'high_commercial_value': len([t for t in trending_topics if t.commercial_value > 0.8]),
            'recommended_immediate_action': len([opp for opp in market_opportunities if 'IMMEDIATE' in opp.recommended_action])
        }
    }


# 测试和演示
if __name__ == "__main__":
    async def main():
        print("[REALTIME] 实时关键词分析系统启动...")
        
        # 分析当前趋势
        results = await analyze_current_trends(force_analysis=True)
        
        print(f"\n[ANALYSIS] 分析完成！发现 {results['analysis_summary']['total_topics']} 个热门话题")
        print(f"[URGENT] 紧急话题: {results['analysis_summary']['urgent_topics']} 个")
        print(f"[COMMERCIAL] 高商业价值: {results['analysis_summary']['high_commercial_value']} 个")
        print(f"[ACTION] 立即行动建议: {results['analysis_summary']['recommended_immediate_action']} 个")
        
        print("\n[TOP] Top 3 热门话题:")
        for i, topic in enumerate(results['trending_topics'][:3]):
            print(f"{i+1}. {topic['keyword']}")
            print(f"   趋势评分: {topic['trend_score']:.2f} | 商业价值: {topic['commercial_value']:.2f}")
            print(f"   推理: {topic['business_reasoning']}")
            print()
        
        # 保存完整结果
        with open('data/realtime_analysis_demo.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        print("[SAVE] 完整分析结果已保存到 data/realtime_analysis_demo.json")
    
    # 运行演示
    asyncio.run(main())