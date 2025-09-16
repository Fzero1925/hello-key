#!/usr/bin/env python3
"""
实时热点分析器 - Realtime Trending Analyzer
持续监控和分析高价值热点话题，提供纯分析输出

核心功能：
1. 实时监控热点关键词变化
2. 智能评估话题的商业价值和机会
3. 生成详细的分析报告和建议
4. 即时Telegram通知
5. 提供可操作的商业洞察
"""

import os
import sys
import json
import asyncio
import subprocess
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path
import pytz
import requests
import yaml

# 导入编码处理器
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
try:
    from modules.utils.encoding_handler import safe_print, get_encoding_handler
except ImportError:
    def safe_print(text, **kwargs):
        print(text, **kwargs)

# Import v2 enhancements
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'keyword_tools'))
    from scoring import make_revenue_range
except ImportError:
    def make_revenue_range(v):
        return {"point": v, "range": f"${v*0.75:.0f}–${v*1.25:.0f}/mo"}

# 导入配置管理器
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from modules.config import ConfigManager

# 导入实时分析器
from modules.trending.realtime_analyzer import RealtimeTrendingAnalyzer, TrendingTopic, analyze_current_trends


class RealtimeTrendingMonitor:
    """实时热点监控器"""
    
    def __init__(self):
        self.logger = self._setup_logging()

        # 加载配置管理器
        self.config_manager = ConfigManager()

        self.data_dir = "data/realtime_analysis"
        self.analysis_history = "data/analysis_history"
        self.monitoring_active = False

        # Load v2 configuration
        self.v2_config = self._load_v2_config()
        
        # 创建必要目录
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.analysis_history, exist_ok=True)
        
        # 分析阈值配置 - 与v2配置整合
        self.analysis_thresholds = {
            'high_opportunity_score': self.v2_config['thresholds']['opportunity'],  # 高机会评分线
            'high_trend_score': 0.75,        # 高趋势评分线
            'high_commercial_value': 0.70,    # 高商业价值线
            'high_urgency_score': self.v2_config['thresholds']['urgency'],  # 高紧急度线
            'high_search_volume': self.v2_config['thresholds']['search_volume'],  # 高搜索量线
            'max_acceptable_competition': 'Medium-High'  # 可接受的最高竞争度
        }

        # 分析周期配置
        self.analysis_cooldown_hours = 2  # 同一关键词2小时内不重复深度分析
        self.max_daily_reports = 10  # 每日最大详细报告数
        
        # Telegram配置
        credentials = self.config_manager.get_api_credentials()
        self.telegram_token = credentials.get('telegram_bot_token', '')
        self.telegram_chat_id = credentials.get('telegram_chat_id', '')
    
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
            if hasattr(self, 'logger'):
                self.logger.warning(f"Could not load v2 config: {e}, using defaults")
        
        return default_config
        
    def _setup_logging(self) -> logging.Logger:
        """设置日志系统"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('data/realtime_analysis.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    async def start_monitoring(self, check_interval_minutes: int = 30):
        """启动实时监控"""
        self.monitoring_active = True
        self.logger.info(f"🚀 实时监控启动 - 检查间隔: {check_interval_minutes} 分钟")
        
        while self.monitoring_active:
            try:
                await self.check_and_analyze()
                await asyncio.sleep(check_interval_minutes * 60)  # 转换为秒
                
            except KeyboardInterrupt:
                self.logger.info("⏹️ 收到停止信号，正在关闭监控...")
                self.monitoring_active = False
                break
            except Exception as e:
                self.logger.error(f"❌ 监控循环出错: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟再继续
    
    async def check_and_analyze(self) -> Dict[str, Any]:
        """检查热点并进行深度分析"""
        self.logger.info("🔍 开始检查热点话题...")
        
        # 获取当前趋势分析
        try:
            trends_data = await analyze_current_trends(force_analysis=False)
            trending_topics = [
                TrendingTopic(**topic) for topic in trends_data['trending_topics']
            ]
            
            if not trending_topics:
                self.logger.info("📊 未发现新的热点话题")
                empty_summary = self._generate_analysis_summary([], [])
                empty_summary.update({'status': 'no_trends', 'action': 'none'})
                return empty_summary
                
        except Exception as e:
            self.logger.error(f"❌ 趋势分析失败: {e}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': 'error',
                'action': 'error',
                'analysis_summary': {
                    'total_topics_analyzed': 0,
                    'high_value_topics': 0,
                    'detailed_reports_generated': 0,
                    'recommendations_provided': 0
                },
                'detailed_analyses': [],
                'high_value_topics': [],
                'top_topics_monitored': [],
                'next_monitoring_cycle': (
                    datetime.now(timezone.utc) + timedelta(minutes=30)
                ).isoformat(),
                'message': str(e)
            }
        
        # 评估高价值话题
        high_value_topics = self._evaluate_high_value_topics(trending_topics)

        if not high_value_topics:
            self.logger.info("⏳ 暂无高价值热点话题")
            summary = self._generate_analysis_summary([], trending_topics)
            summary.update({'status': 'no_high_value', 'action': 'monitoring'})
            return summary

        # 生成详细分析报告
        detailed_analyses = []
        for topic in high_value_topics:
            analysis = await self._generate_detailed_analysis(topic)
            detailed_analyses.append(analysis)

        # 汇总报告
        summary = self._generate_analysis_summary(detailed_analyses, trending_topics)

        # 发送Telegram通知
        if detailed_analyses:
            await self._send_analysis_notification(summary)
        
        return summary
    
    def _evaluate_high_value_topics(self, topics: List[TrendingTopic]) -> List[TrendingTopic]:
        """评估高价值话题"""
        high_value_candidates = []

        for topic in topics:
            # 基本条件检查
            if not self._meets_high_value_criteria(topic):
                continue

            # 检查是否最近已深度分析过
            if self._check_recent_analysis(topic.keyword):
                self.logger.info(f"⏭️ 跳过 '{topic.keyword}' - 最近已深度分析")
                continue

            # 检查每日报告限额
            if self._check_daily_report_limit():
                self.logger.info("📊 已达到每日最大报告限额")
                break

            # 通过所有检查，加入高价值列表
            high_value_candidates.append(topic)
            self.logger.info(f"✅ '{topic.keyword}' 符合高价值分析条件")

        # 按综合评分排序，取前5个
        high_value_candidates.sort(key=lambda t: (
            t.urgency_score * 0.4 +
            t.commercial_value * 0.3 +
            t.trend_score * 0.3
        ), reverse=True)

        return high_value_candidates[:5]  # 最多同时分析5个话题
    
    def _meets_high_value_criteria(self, topic: TrendingTopic) -> bool:
        """检查话题是否满足高价值分析门槛"""
        opp = self._estimate_opportunity_score(topic)
        criteria_checks = {
            'trend_score': topic.trend_score >= self.analysis_thresholds['high_trend_score'],
            'commercial_value': topic.commercial_value >= self.analysis_thresholds['high_commercial_value'],
            'urgency_score': topic.urgency_score >= self.analysis_thresholds['high_urgency_score'],
            'search_volume': getattr(topic, 'search_volume_est', 0) >= self.analysis_thresholds['high_search_volume'],
            'competition_ok': self._check_competition_level(getattr(topic, 'competition_level', 'High')),
            'opportunity_score': opp >= self.analysis_thresholds.get('high_opportunity_score', 70)
        }
        
        passed_checks = sum(criteria_checks.values())
        required_checks = 4
        
        if passed_checks >= required_checks:
            self.logger.info(f"✅ '{topic.keyword}' 通过 {passed_checks}/{len(criteria_checks)} 项阈值 (opp={opp:.1f})")
            return True
        else:
            self.logger.debug(f"ℹ️ '{topic.keyword}' 未通过 {passed_checks}/{len(criteria_checks)} 项: {criteria_checks} (opp={opp:.1f})")
            return False

    def _estimate_opportunity_score(self, topic: TrendingTopic) -> float:
        """Estimate opportunity score (0-100) from topic fields and v2 weights."""
        weights = self.v2_config.get('weights', {"T":0.35,"I":0.30,"S":0.15,"F":0.20,"D_penalty":0.6})
        T = max(0.0, min(1.0, float(topic.trend_score)))
        I = max(0.0, min(1.0, float(topic.commercial_value)))
        S = 0.5  # neutral seasonality
        F = 0.8  # site fit approximation
        comp_map = {'Low':0.2,'Low-Medium':0.3,'Medium':0.5,'Medium-High':0.7,'High':0.85}
        D = comp_map.get(topic.competition_level, 0.5)
        base = weights.get('T',0.35)*T + weights.get('I',0.30)*I + weights.get('S',0.15)*S + weights.get('F',0.20)*F
        score = 100.0 * base * (1.0 - weights.get('D_penalty',0.6) * D)
        return max(0.0, min(100.0, round(score, 2)))
    
    def _check_competition_level(self, competition: str) -> bool:
        """检查竞争度是否可接受"""
        competition_levels = {
            'Low': 1, 'Low-Medium': 2, 'Medium': 3,
            'Medium-High': 4, 'High': 5
        }

        current_level = competition_levels.get(competition, 3)
        max_level = competition_levels.get(self.analysis_thresholds['max_acceptable_competition'], 4)
        
        return current_level <= max_level
    
    def _check_recent_analysis(self, keyword: str) -> bool:
        """检查是否最近已深度分析过相似内容"""
        history_file = f"{self.analysis_history}/analysis_log.json"
        
        if not os.path.exists(history_file):
            return False
        
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.analysis_cooldown_hours)
            
            for record in history[-20:]:  # 检查最近20条记录
                if record['keyword'].lower() == keyword.lower():
                    gen_time = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                    if gen_time > cutoff_time:
                        return True
            
        except Exception as e:
            self.logger.error(f"⚠️ 检查分析历史失败: {e}")

        return False

    def _check_daily_report_limit(self) -> bool:
        """检查是否达到每日报告限额"""
        history_file = f"{self.analysis_history}/analysis_log.json"
        
        if not os.path.exists(history_file):
            return False
        
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            today = datetime.now(timezone.utc).date()
            today_count = 0
            
            for record in history[-50:]:  # 检查最近50条记录
                gen_date = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00')).date()
                if gen_date == today:
                    today_count += 1
            
            return today_count >= self.max_daily_reports

        except Exception as e:
            self.logger.error(f"⚠️ 检查每日限额失败: {e}")
            return False
    
    async def _generate_detailed_analysis(self, topic: TrendingTopic) -> Dict[str, Any]:
        """生成详细分析报告"""
        self.logger.info(f"📊 开始为 '{topic.keyword}' 生成详细分析...")

        start_time = datetime.now(timezone.utc)
        
        try:
            # 生成详细的商业分析报告
            opportunity_score = self._estimate_opportunity_score(topic)
            revenue_estimate = make_revenue_range(getattr(topic, 'estimated_revenue', 0) or opportunity_score * 100)

            # 市场分析
            market_analysis = {
                'search_volume': getattr(topic, 'search_volume_est', 'N/A'),
                'competition_level': getattr(topic, 'competition_level', 'Unknown'),
                'trend_momentum': 'Rising' if topic.trend_score > 0.7 else 'Stable' if topic.trend_score > 0.4 else 'Declining',
                'urgency_assessment': 'High' if topic.urgency_score > 0.8 else 'Medium' if topic.urgency_score > 0.5 else 'Low'
            }

            # 商业建议
            business_recommendations = self._generate_business_recommendations(topic, opportunity_score)

            # 风险评估
            risk_assessment = self._assess_market_risks(topic)

            # 成功分析
            analysis_result = {
                'status': 'success',
                'keyword': topic.keyword,
                'category': getattr(topic, 'category', 'Unknown'),
                'start_time': start_time.isoformat(),
                'end_time': datetime.now(timezone.utc).isoformat(),
                'opportunity_score': opportunity_score,
                'revenue_estimate': revenue_estimate,
                'market_analysis': market_analysis,
                'business_recommendations': business_recommendations,
                'risk_assessment': risk_assessment,
                'trend_scores': {
                    'trend_score': topic.trend_score,
                    'commercial_value': topic.commercial_value,
                    'urgency_score': topic.urgency_score
                },
                'data_sources': getattr(topic, 'sources', [])
            }

            # 记录到历史
            self._log_analysis(analysis_result, topic)

            self.logger.info(f"✅ '{topic.keyword}' 详细分析完成")
                
        except Exception as analysis_error:
            # 分析失败
            analysis_result = {
                'status': 'failed',
                'keyword': topic.keyword,
                'error': str(analysis_error),
                'start_time': start_time.isoformat(),
                'end_time': datetime.now(timezone.utc).isoformat()
            }

            self.logger.error(f"❌ '{topic.keyword}' 分析失败: {analysis_error}")
            
        return analysis_result

    def _generate_business_recommendations(self, topic: TrendingTopic, opportunity_score: float) -> List[str]:
        """生成商业建议"""
        recommendations = []

        if opportunity_score > 80:
            recommendations.append("IMMEDIATE ACTION: 高价值机会，建议立即制定内容策略")
            recommendations.append("考虑快速进入市场以抢占先机")

        if topic.urgency_score > 0.8:
            recommendations.append("时间敏感性高，建议在24-48小时内采取行动")

        if getattr(topic, 'competition_level', 'High') in ['Low', 'Low-Medium']:
            recommendations.append("竞争度较低，适合长期投资")

        if topic.trend_score > 0.8:
            recommendations.append("趋势强劲，建议重点关注相关话题扩展")

        if topic.commercial_value > 0.8:
            recommendations.append("商业价值高，可考虑多渠道变现策略")

        return recommendations

    def _assess_market_risks(self, topic: TrendingTopic) -> Dict[str, str]:
        """评估市场风险"""
        risks = {}

        # 竞争风险
        competition = getattr(topic, 'competition_level', 'Unknown')
        if competition in ['High', 'Medium-High']:
            risks['competition'] = '竞争激烈，需要差异化策略'
        else:
            risks['competition'] = '竞争适中，进入相对容易'

        # 趋势风险
        if topic.trend_score < 0.5:
            risks['trend'] = '趋势下降，存在过时风险'
        elif topic.trend_score > 0.8:
            risks['trend'] = '趋势过热，可能存在泡沫'
        else:
            risks['trend'] = '趋势稳定，风险较低'

        # 时效性风险
        if topic.urgency_score > 0.9:
            risks['timing'] = '极高时效性，错过窗口期风险大'
        elif topic.urgency_score < 0.3:
            risks['timing'] = '时效性较低，可长期规划'
        else:
            risks['timing'] = '时效性适中'

        return risks

    def _log_analysis(self, result: Dict, topic: TrendingTopic):
        """记录分析历史"""
        history_file = f"{self.analysis_history}/analysis_log.json"

        log_entry = {
            'timestamp': result['end_time'],
            'keyword': topic.keyword,
            'category': getattr(topic, 'category', 'Unknown'),
            'status': result['status'],
            'analysis_type': 'detailed_realtime',
            'opportunity_score': result.get('opportunity_score', 0),
            'trend_score': topic.trend_score,
            'commercial_value': topic.commercial_value,
            'urgency_score': topic.urgency_score,
            'revenue_estimate': result.get('revenue_estimate', {}),
            'sources': getattr(topic, 'sources', [])
        }
        
        # 读取现有历史
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except Exception as e:
                self.logger.error(f"读取历史记录失败: {e}")
        
        # 添加新记录
        history.append(log_entry)
        
        # 保持最近100条记录
        if len(history) > 100:
            history = history[-100:]
        
        # 保存更新的历史
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存历史记录失败: {e}")
    
    def _generate_analysis_summary(self, results: List[Dict], all_topics: List[TrendingTopic]) -> Dict[str, Any]:
        """生成分析汇总报告"""
        successful_analyses = [r for r in results if r['status'] == 'success']
        failed_analyses = [r for r in results if r['status'] != 'success']
        
        summary = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'analysis_summary': {
                'total_topics_analyzed': len(all_topics),
                'high_value_topics': len(results),
                'detailed_reports_generated': len(successful_analyses),
                'failed_analyses': len(failed_analyses)
            },
            'detailed_analyses': successful_analyses,
            'failed_attempts': failed_analyses,
            'top_topics_monitored': [
                {
                    'keyword': topic.keyword,
                    'trend_score': topic.trend_score,
                    'reason_not_triggered': self._analyze_why_not_triggered(topic)
                }
                for topic in all_topics[:5] 
                if topic.keyword not in [r['keyword'] for r in results]
            ],
            'next_monitoring_cycle': (
                datetime.now(timezone.utc) + timedelta(minutes=30)
            ).isoformat()
        }
        
        return summary
    
    def _analyze_why_not_triggered(self, topic: TrendingTopic) -> str:
        """分析为什么话题未被深度分析 - v2增强版本"""
        reasons = []
        gaps = []  # 记录与阈值的具体差距

        # 优先检查opportunity_score
        opp = self._estimate_opportunity_score(topic)
        min_opp = self.analysis_thresholds['high_opportunity_score']
        if opp < min_opp:
            gap = min_opp - opp
            reasons.append(f"机会评分不足 ({opp:.1f}/100)")
            gaps.append(f"opportunity_score gap: {gap:.1f}")

        # 传统检查项
        if topic.trend_score < self.analysis_thresholds['high_trend_score']:
            gap = self.analysis_thresholds['high_trend_score'] - topic.trend_score
            reasons.append(f"趋势评分过低 ({topic.trend_score:.2f})")
            gaps.append(f"trend_score gap: {gap:.2f}")

        if topic.commercial_value < self.analysis_thresholds['high_commercial_value']:
            gap = self.analysis_thresholds['high_commercial_value'] - topic.commercial_value
            reasons.append(f"商业价值不足 ({topic.commercial_value:.2f})")
            gaps.append(f"commercial_value gap: {gap:.2f}")

        if topic.urgency_score < self.analysis_thresholds['high_urgency_score']:
            gap = self.analysis_thresholds['high_urgency_score'] - topic.urgency_score
            reasons.append(f"紧急度不够 ({topic.urgency_score:.2f})")
            gaps.append(f"urgency_score gap: {gap:.2f}")

        search_vol = getattr(topic, 'search_volume_est', 0)
        if search_vol < self.analysis_thresholds['high_search_volume']:
            gap = self.analysis_thresholds['high_search_volume'] - search_vol
            reasons.append(f"搜索量偏低 ({search_vol:,})")
            gaps.append(f"search_volume gap: {gap:,}")

        competition = getattr(topic, 'competition_level', 'High')
        if not self._check_competition_level(competition):
            reasons.append(f"竞争过于激烈 ({competition})")
            gaps.append("competition_level: too high")

        if self._check_recent_analysis(topic.keyword):
            reasons.append("最近已深度分析过")
            gaps.append("recent_analysis: within cooldown")
        
        # 返回结合原因和差距的详细分析
        main_reason = "; ".join(reasons) if reasons else "未知原因"
        gap_details = " | ".join(gaps) if gaps else ""
        
        return f"{main_reason} [{gap_details}]" if gap_details else main_reason
    
    async def _send_analysis_notification(self, summary: Dict):
        """发送Telegram分析通知"""
        if not self.telegram_token or not self.telegram_chat_id:
            self.logger.warning("⚠️ Telegram配置不完整，跳过通知")
            return
        
        try:
            # 构建通知消息
            message = self._build_notification_message(summary)
            
            # 发送消息
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self.logger.info("📱 Telegram触发通知发送成功")
            else:
                self.logger.error(f"📱 Telegram通知发送失败: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"📱 发送Telegram通知异常: {e}")
    
    def _build_notification_message(self, summary: Dict) -> str:
        """构建通知消息"""
        analysis = summary['analysis_summary']
        detailed_analyses = summary['detailed_analyses']

        # 基础信息
        message = f"""📊 <b>实时热点分析报告</b>

📈 <b>分析概况</b>
• 分析话题: {analysis['total_topics_analyzed']} 个
• 高价值话题: {analysis['high_value_topics']} 个
• 详细报告: {analysis['detailed_reports_generated']} 个
• 分析失败: {analysis['failed_analyses']} 个

"""

        # 成功分析的话题
        if detailed_analyses:
            message += "✅ <b>详细分析完成</b>\n"
            for analysis_result in detailed_analyses:
                message += f"• <code>{analysis_result['keyword']}</code>\n"
                revenue = analysis_result.get('revenue_estimate', {})
                if isinstance(revenue, dict) and 'range' in revenue:
                    message += f"  💰 收益预估: {revenue['range']}\n"
                else:
                    message += f"  💰 收益预估: N/A\n"
                message += f"  🎯 机会评分: {analysis_result.get('opportunity_score', 0):.1f}/100\n\n"

        # 监控中的话题
        monitored = summary.get('top_topics_monitored', [])
        if monitored:
            message += "⏳ <b>监控中话题</b>\n"
            for topic in monitored[:3]:
                message += f"• <code>{topic['keyword']}</code> (评分: {topic['trend_score']:.2f})\n"
        
        # 下次检查时间
        next_check = datetime.fromisoformat(summary['next_monitoring_cycle'].replace('Z', '+00:00'))
        beijing_time = next_check.astimezone(pytz.timezone('Asia/Shanghai'))
        message += f"\n⏰ 下次检查: {beijing_time.strftime('%H:%M')}"
        
        return message
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring_active = False
        self.logger.info("⏹️ 实时监控已停止")


# 手动分析接口
async def manual_analysis_check(force: bool = True) -> Dict[str, Any]:
    """手动触发分析检查（用于测试或紧急情况）"""
    monitor = RealtimeTrendingMonitor()
    return await monitor.check_and_analyze()


# 主要运行接口
async def start_realtime_monitoring(check_interval: int = 30):
    """启动实时监控（主要接口）"""
    monitor = RealtimeTrendingMonitor()
    await monitor.start_monitoring(check_interval)


# 测试和演示
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='实时热点分析监控器')
    parser.add_argument('--mode', choices=['monitor', 'check'], default='check',
                      help='运行模式: monitor=持续监控, check=单次分析')
    parser.add_argument('--interval', type=int, default=30,
                      help='监控间隔（分钟）')

    args = parser.parse_args()

    if args.mode == 'monitor':
        safe_print(f"[快速] 启动实时分析监控模式 - 间隔: {args.interval} 分钟")
        safe_print("按 Ctrl+C 停止监控")
        asyncio.run(start_realtime_monitoring(args.interval))
    else:
        safe_print("[搜索] 执行单次分析检查...")
        result = asyncio.run(manual_analysis_check())
        safe_print(f"[数据] 分析完成: {result['analysis_summary']['detailed_reports_generated']} 个详细报告已生成")
