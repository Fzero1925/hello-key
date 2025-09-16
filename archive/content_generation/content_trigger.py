#!/usr/bin/env python3
"""
文章生成触发器 - Content Generation Trigger (Archived)
从实时分析中触发文章生成的功能模块

注意：此模块已归档，用于保留文章生成功能。
实时触发器现在专注于纯分析输出。
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
import yaml

# 添加项目根目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from modules.keyword_tools.scoring import make_revenue_range
except ImportError:
    def make_revenue_range(v):
        return {"point": v, "range": f"${v*0.75:.0f}–${v*1.25:.0f}/mo"}

from modules.trending.realtime_analyzer import TrendingTopic


class ContentGenerationTrigger:
    """文章生成触发器（已归档）"""

    def __init__(self):
        self.logger = self._setup_logging()
        self.data_dir = "data/content_generation"
        self.generation_history = "data/generation_history"

        # 创建必要目录
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.generation_history, exist_ok=True)

        # 触发条件配置
        self.trigger_thresholds = {
            'min_opportunity_score': 70,
            'min_trend_score': 0.75,
            'min_commercial_value': 0.70,
            'min_urgency_score': 0.8,
            'min_search_volume': 10000,
            'max_competition_level': 'Medium-High'
        }

        # 防重复生成配置
        self.cooldown_hours = 6
        self.max_daily_generations = 4

    def _setup_logging(self) -> logging.Logger:
        """设置日志系统"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('data/content_generation.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)

    async def execute_content_generation(self, topic: TrendingTopic) -> Dict[str, Any]:
        """执行内容生成"""
        self.logger.info(f"🚀 开始为 '{topic.keyword}' 生成文章...")

        start_time = datetime.now(timezone.utc)

        try:
            # 判断文章角度
            angle = 'use-case' if any(k in topic.keyword.lower() for k in
                ['outdoor','pet','apartment','garage','wireless','energy']) else 'best'

            # 准备单个关键词的lineup
            one_item_lineup = [{
                'keyword': topic.keyword,
                'category': topic.category,
                'angle': angle,
                'trend_score': topic.trend_score,
                'reason': 'Content generation trigger'
            }]

            # 保存lineup文件
            os.makedirs('data', exist_ok=True)
            with open('data/daily_lineup_latest.json', 'w', encoding='utf-8') as f:
                json.dump(one_item_lineup, f, indent=2, ensure_ascii=False)

            # 调用文章生成脚本 (需要实际的脚本路径)
            result = subprocess.run([
                'python', 'scripts/workflow_quality_enforcer.py',
                '--count', '1',
            ], capture_output=True, text=True, timeout=600)

            if result.returncode == 0:
                # 生成成功
                generation_result = {
                    'status': 'success',
                    'keyword': topic.keyword,
                    'category': topic.category,
                    'start_time': start_time.isoformat(),
                    'end_time': datetime.now(timezone.utc).isoformat(),
                    'trigger_reason': getattr(topic, 'business_reasoning', 'Content generation'),
                    'estimated_revenue': getattr(topic, 'estimated_revenue', 'N/A'),
                    'urgency_score': topic.urgency_score,
                    'stdout': result.stdout,
                    'stderr': result.stderr if result.stderr else None
                }

                # 记录到历史
                self._log_generation(generation_result, topic)

                self.logger.info(f"✅ '{topic.keyword}' 文章生成成功")

            else:
                # 生成失败
                generation_result = {
                    'status': 'failed',
                    'keyword': topic.keyword,
                    'error': result.stderr or 'Unknown error',
                    'return_code': result.returncode,
                    'start_time': start_time.isoformat(),
                    'end_time': datetime.now(timezone.utc).isoformat()
                }

                self.logger.error(f"❌ '{topic.keyword}' 文章生成失败: {result.stderr}")

        except subprocess.TimeoutExpired:
            generation_result = {
                'status': 'timeout',
                'keyword': topic.keyword,
                'error': 'Generation process timed out after 10 minutes',
                'start_time': start_time.isoformat(),
                'end_time': datetime.now(timezone.utc).isoformat()
            }
            self.logger.error(f"⏰ '{topic.keyword}' 文章生成超时")

        except Exception as e:
            generation_result = {
                'status': 'error',
                'keyword': topic.keyword,
                'error': str(e),
                'start_time': start_time.isoformat(),
                'end_time': datetime.now(timezone.utc).isoformat()
            }
            self.logger.error(f"💥 '{topic.keyword}' 生成过程异常: {e}")

        return generation_result

    def _log_generation(self, result: Dict, topic: TrendingTopic):
        """记录生成历史"""
        history_file = f"{self.generation_history}/generation_log.json"

        log_entry = {
            'timestamp': result['end_time'],
            'keyword': topic.keyword,
            'category': topic.category,
            'status': result['status'],
            'trigger_type': 'content_generation',
            'trend_score': topic.trend_score,
            'commercial_value': topic.commercial_value,
            'urgency_score': topic.urgency_score,
            'estimated_revenue': getattr(topic, 'estimated_revenue', 'N/A'),
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

    def check_generation_eligibility(self, topic: TrendingTopic) -> Dict[str, Any]:
        """检查话题是否符合生成条件"""
        checks = {
            'trend_score': topic.trend_score >= self.trigger_thresholds['min_trend_score'],
            'commercial_value': topic.commercial_value >= self.trigger_thresholds['min_commercial_value'],
            'urgency_score': topic.urgency_score >= self.trigger_thresholds['min_urgency_score'],
            'search_volume': getattr(topic, 'search_volume_est', 0) >= self.trigger_thresholds['min_search_volume'],
            'competition_ok': self._check_competition_level(getattr(topic, 'competition_level', 'High')),
            'no_recent_generation': not self._check_recent_generation(topic.keyword),
            'under_daily_limit': not self._check_daily_limit()
        }

        passed = sum(checks.values())
        eligible = passed >= 5  # 需要通过至少5项检查

        return {
            'eligible': eligible,
            'checks_passed': passed,
            'total_checks': len(checks),
            'details': checks,
            'reason': self._get_eligibility_reason(checks) if not eligible else "符合生成条件"
        }

    def _check_competition_level(self, competition: str) -> bool:
        """检查竞争度是否可接受"""
        competition_levels = {
            'Low': 1, 'Low-Medium': 2, 'Medium': 3,
            'Medium-High': 4, 'High': 5
        }

        current_level = competition_levels.get(competition, 3)
        max_level = competition_levels.get(self.trigger_thresholds['max_competition_level'], 4)

        return current_level <= max_level

    def _check_recent_generation(self, keyword: str) -> bool:
        """检查是否最近已生成过相似内容"""
        history_file = f"{self.generation_history}/generation_log.json"

        if not os.path.exists(history_file):
            return False

        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)

            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.cooldown_hours)

            for record in history[-20:]:
                if record['keyword'].lower() == keyword.lower():
                    gen_time = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                    if gen_time > cutoff_time:
                        return True

        except Exception as e:
            self.logger.error(f"⚠️ 检查生成历史失败: {e}")

        return False

    def _check_daily_limit(self) -> bool:
        """检查是否达到每日生成限额"""
        history_file = f"{self.generation_history}/generation_log.json"

        if not os.path.exists(history_file):
            return False

        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)

            today = datetime.now(timezone.utc).date()
            today_count = 0

            for record in history[-50:]:
                gen_date = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00')).date()
                if gen_date == today:
                    today_count += 1

            return today_count >= self.max_daily_generations

        except Exception as e:
            self.logger.error(f"⚠️ 检查每日限额失败: {e}")
            return False

    def _get_eligibility_reason(self, checks: Dict[str, bool]) -> str:
        """获取不符合生成条件的原因"""
        failed_checks = [key for key, value in checks.items() if not value]

        reason_map = {
            'trend_score': '趋势评分过低',
            'commercial_value': '商业价值不足',
            'urgency_score': '紧急度不够',
            'search_volume': '搜索量偏低',
            'competition_ok': '竞争过于激烈',
            'no_recent_generation': '最近已生成相似内容',
            'under_daily_limit': '已达每日生成限额'
        }

        reasons = [reason_map.get(check, check) for check in failed_checks]
        return '; '.join(reasons)


# 便捷接口函数
async def generate_content_for_topic(topic: TrendingTopic) -> Dict[str, Any]:
    """为指定话题生成内容"""
    trigger = ContentGenerationTrigger()
    eligibility = trigger.check_generation_eligibility(topic)

    if eligibility['eligible']:
        return await trigger.execute_content_generation(topic)
    else:
        return {
            'status': 'not_eligible',
            'keyword': topic.keyword,
            'reason': eligibility['reason'],
            'eligibility_details': eligibility
        }


# 演示和测试
if __name__ == "__main__":
    # 演示内容生成功能
    print("📝 文章生成触发器演示")
    print("此模块已归档，用于保留文章生成功能")
    print("实际使用需要配置完整的文章生成脚本路径")