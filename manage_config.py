#!/usr/bin/env python3
"""
Keyword Engine v2 Configuration Management Tool
管理和校准关键词引擎的所有配置参数
"""

import os
import sys
import yaml
import json
from datetime import datetime
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    """加载当前配置"""
    config_path = "keyword_engine.yml"
    
    if not os.path.exists(config_path):
        print("❌ 配置文件不存在，将创建默认配置")
        return create_default_config()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 配置文件读取失败: {e}")
        return None

def create_default_config() -> Dict[str, Any]:
    """创建默认配置"""
    default_config = {
        "window_recent_ratio": 0.3,
        "thresholds": {
            "opportunity": 70,
            "search_volume": 10000,
            "urgency": 0.8
        },
        "weights": {
            "T": 0.35,  # Trend weight
            "I": 0.30,  # Intent weight
            "S": 0.15,  # Seasonality weight
            "F": 0.20,  # Site fit weight
            "D_penalty": 0.6  # Difficulty penalty
        },
        "adsense": {
            "ctr_serp": 0.25,
            "click_share_rank": 0.35,
            "rpm_usd": 10
        },
        "amazon": {
            "ctr_to_amazon": 0.12,
            "cr": 0.04,
            "aov_usd": 80,
            "commission": 0.03
        },
        "mode": "max"  # max | sum
    }
    
    save_config(default_config)
    return default_config

def save_config(config: Dict[str, Any]) -> bool:
    """保存配置"""
    try:
        with open("keyword_engine.yml", 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
        print("✅ 配置已保存到 keyword_engine.yml")
        return True
    except Exception as e:
        print(f"❌ 配置保存失败: {e}")
        return False

def update_thresholds(config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """更新阈值配置"""
    for key, value in kwargs.items():
        if key in config['thresholds']:
            old_value = config['thresholds'][key]
            config['thresholds'][key] = value
            print(f"📊 更新阈值 {key}: {old_value} → {value}")
        else:
            print(f"⚠️ 未知阈值配置: {key}")
    
    return config

def update_weights(config: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """更新权重配置"""
    for key, value in kwargs.items():
        if key in config['weights']:
            old_value = config['weights'][key]
            config['weights'][key] = value
            print(f"⚖️ 更新权重 {key}: {old_value} → {value}")
        else:
            print(f"⚠️ 未知权重配置: {key}")
    
    return config

def update_revenue_params(config: Dict[str, Any], platform: str, **kwargs) -> Dict[str, Any]:
    """更新收入参数"""
    if platform not in ['adsense', 'amazon']:
        print(f"❌ 未知平台: {platform}")
        return config
    
    for key, value in kwargs.items():
        if key in config[platform]:
            old_value = config[platform][key]
            config[platform][key] = value
            print(f"💰 更新{platform}参数 {key}: {old_value} → {value}")
        else:
            print(f"⚠️ 未知{platform}参数: {key}")
    
    return config

def show_current_config():
    """显示当前配置"""
    config = load_config()
    if not config:
        return
    
    print("\n📋 当前配置状态:")
    print("=" * 50)
    
    print(f"\n🎯 触发阈值:")
    for key, value in config['thresholds'].items():
        print(f"  {key}: {value}")
    
    print(f"\n⚖️ 评分权重:")
    for key, value in config['weights'].items():
        print(f"  {key}: {value}")
    
    print(f"\n💰 AdSense参数:")
    for key, value in config['adsense'].items():
        print(f"  {key}: {value}")
    
    print(f"\n🛒 Amazon参数:")
    for key, value in config['amazon'].items():
        print(f"  {key}: {value}")
    
    print(f"\n🔧 其他配置:")
    print(f"  window_recent_ratio: {config['window_recent_ratio']}")
    print(f"  mode: {config['mode']}")

def calibrate_from_data(data_file: str = None):
    """根据实际数据校准参数（预留接口）"""
    print("📊 数据校准功能开发中...")
    print("将来此功能将:")
    print("  - 读取GSC/AdSense/联盟后台数据")
    print("  - 自动计算最优CTR/RPM/转化率参数")
    print("  - 基于实际表现调整权重和阈值")

def main():
    """主程序"""
    if len(sys.argv) < 2:
        print("🔧 Keyword Engine v2 配置管理工具")
        print("\n使用方法:")
        print("  python manage_config.py show                    # 显示当前配置")
        print("  python manage_config.py create                  # 创建默认配置")
        print("  python manage_config.py threshold <key> <value> # 更新阈值")
        print("  python manage_config.py weight <key> <value>    # 更新权重")
        print("  python manage_config.py adsense <key> <value>   # 更新AdSense参数")
        print("  python manage_config.py amazon <key> <value>    # 更新Amazon参数")
        print("  python manage_config.py calibrate [data_file]   # 数据校准")
        print("\n示例:")
        print("  python manage_config.py threshold opportunity 75")
        print("  python manage_config.py weight T 0.4")
        print("  python manage_config.py adsense rpm_usd 12")
        return
    
    command = sys.argv[1].lower()
    
    if command == "show":
        show_current_config()
    
    elif command == "create":
        create_default_config()
        print("✅ 默认配置已创建")
    
    elif command == "threshold":
        if len(sys.argv) < 4:
            print("❌ 用法: python manage_config.py threshold <key> <value>")
            return
        
        config = load_config()
        if config:
            key, value = sys.argv[2], float(sys.argv[3])
            config = update_thresholds(config, **{key: value})
            save_config(config)
    
    elif command == "weight":
        if len(sys.argv) < 4:
            print("❌ 用法: python manage_config.py weight <key> <value>")
            return
        
        config = load_config()
        if config:
            key, value = sys.argv[2], float(sys.argv[3])
            config = update_weights(config, **{key: value})
            save_config(config)
    
    elif command in ["adsense", "amazon"]:
        if len(sys.argv) < 4:
            print(f"❌ 用法: python manage_config.py {command} <key> <value>")
            return
        
        config = load_config()
        if config:
            key, value = sys.argv[2], float(sys.argv[3])
            config = update_revenue_params(config, command, **{key: value})
            save_config(config)
    
    elif command == "calibrate":
        data_file = sys.argv[2] if len(sys.argv) > 2 else None
        calibrate_from_data(data_file)
    
    else:
        print(f"❌ 未知命令: {command}")

if __name__ == "__main__":
    main()