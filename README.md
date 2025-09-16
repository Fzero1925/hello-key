# 智能关键词分析工具 🔍

一个专业的关键词获取和商业价值分析工具，支持多数据源集成和智能评估算法。

## ✨ 核心特性

### 🎯 智能分析
- **多源数据集成**: Google Trends、Reddit、YouTube、Amazon、RSS feeds
- **V2增强算法**: 商业价值评估和机会评分系统
- **实时监控**: 持续追踪热点话题变化
- **智能推荐**: 基于数据的内容策略建议

### 🛠️ 技术特性
- **模块化架构**: 高度解耦的功能模块
- **跨平台兼容**: Windows/Linux/macOS全平台支持
- **自动重试**: 网络请求失败自动恢复
- **安全配置**: 环境变量管理，无硬编码凭据
- **编码安全**: UTF-8优先，完善的编码处理

## 📊 项目状态

### ✅ 已完成 (v1.0)
- 🟢 **核心重构完成** - 所有主要模块已重构优化
- 🟢 **配置管理系统** - 统一的环境变量和配置文件管理
- 🟢 **跨平台支持** - Windows编码问题已解决
- 🟢 **安全性改进** - 移除硬编码凭据，增强安全性
- 🟢 **错误处理** - 完善的重试机制和错误恢复

### 🔄 进行中
- 🟡 **Telegram通知集成** - 等待Bot创建和配置
- 🟡 **功能验证测试** - 需要API密钥配置后测试
- 🟡 **文档完善** - 用户手册和配置指南

## 🚀 快速开始

### 1. 环境要求
```bash
Python 3.8+
pip install -r requirements.txt
```

### 2. 配置设置
```bash
# 运行配置验证
python scripts/validate_config.py

# 根据提示设置环境变量
export KEYWORD_TOOL_REDDIT_CLIENT_ID="your_reddit_client_id"
export KEYWORD_TOOL_REDDIT_CLIENT_SECRET="your_reddit_client_secret"
export KEYWORD_TOOL_YOUTUBE_API_KEY="your_youtube_api_key"
# ... 其他API密钥
```

### 3. 基础使用
```bash
# 测试关键词获取
python -m modules.keyword_tools.keyword_fetcher

# 分析关键词价值
python -m modules.keyword_tools.keyword_analyzer

# 话题趋势分析
python -m modules.topic_tools.topic_analyzer

# 启动实时监控
python -m modules.trending.realtime_trigger --interval 30
```

## 📁 项目结构

```
keyword-analysis-tool/
├── 📂 modules/                    # 核心模块
│   ├── 📂 config/                # 配置管理
│   │   ├── config_manager.py     # 统一配置管理器
│   │   └── validator.py          # 配置验证
│   ├── 📂 keyword_tools/         # 关键词工具
│   │   ├── keyword_fetcher.py    # 关键词获取
│   │   ├── keyword_analyzer.py   # 关键词分析
│   │   └── scoring.py            # V2评分算法
│   ├── 📂 topic_tools/           # 话题工具
│   │   ├── topic_fetcher.py      # 话题获取
│   │   └── topic_analyzer.py     # 话题分析
│   ├── 📂 trending/              # 实时分析
│   │   └── realtime_trigger.py   # 实时监控
│   ├── 📂 data_sources/          # 数据源模块
│   │   ├── rss_feed_analyzer.py  # RSS分析
│   │   ├── amazon_scraper.py     # Amazon数据
│   │   └── keyword_cache_manager.py # 缓存管理
│   └── 📂 utils/                 # 工具模块
│       ├── encoding_handler.py   # 编码处理
│       └── network_utils.py      # 网络工具
├── 📂 scripts/                   # 实用脚本
│   └── validate_config.py        # 配置验证
├── 📂 archive/                   # 归档代码
│   └── content_generation/       # 文章生成功能
├── 📂 data/                      # 数据目录
├── 📄 keyword_engine.yml         # 配置文件
├── 📄 PROJECT_STATUS.md          # 项目状态
└── 📄 TODO.md                    # 待办事项
```

## ⚙️ 配置说明

### 必需的环境变量
```bash
# Reddit API
KEYWORD_TOOL_REDDIT_CLIENT_ID=your_client_id
KEYWORD_TOOL_REDDIT_CLIENT_SECRET=your_client_secret

# YouTube API
KEYWORD_TOOL_YOUTUBE_API_KEY=your_api_key

# Telegram通知 (可选)
KEYWORD_TOOL_TELEGRAM_BOT_TOKEN=your_bot_token
KEYWORD_TOOL_TELEGRAM_CHAT_ID=your_chat_id

# 代理设置 (可选)
KEYWORD_TOOL_HTTP_PROXY=http://proxy:port
KEYWORD_TOOL_HTTPS_PROXY=https://proxy:port
```

### 配置文件 (keyword_engine.yml)
```yaml
# V2算法参数
window_recent_ratio: 0.3
thresholds:
  opportunity: 70
  search_volume: 10000
  urgency: 0.8

# API参数
adsense:
  ctr_serp: 0.25
  click_share_rank: 0.35
  rpm_usd: 10

amazon:
  ctr_to_amazon: 0.12
  cr: 0.04
  aov_usd: 80
  commission: 0.03
```

## 🔧 主要功能模块

### 1. 关键词获取器 (KeywordFetcher)
```python
from modules.keyword_tools.keyword_fetcher import KeywordFetcher

fetcher = KeywordFetcher()
keywords = fetcher.fetch_all_sources(category='smart_plugs')
```

### 2. 关键词分析器 (KeywordAnalyzer)
```python
from modules.keyword_tools.keyword_analyzer import KeywordAnalyzer

analyzer = KeywordAnalyzer()
metrics = analyzer.analyze_keyword_metrics(['smart home security'])
```

### 3. 话题分析器 (TopicAnalyzer)
```python
from modules.topic_tools.topic_analyzer import TopicAnalyzer

analyzer = TopicAnalyzer()
result = analyzer.analyze_topics(topics_data)
```

### 4. 实时监控 (RealtimeAnalyzer)
```python
from modules.trending.realtime_trigger import RealtimeAnalyzer

analyzer = RealtimeAnalyzer()
# 单次分析
result = analyzer.run_analysis()

# 持续监控
analyzer.start_monitoring(interval_minutes=30)
```

## 📈 输出示例

### 关键词分析报告
```
关键词: smart plug alexa compatible
  搜索量: 15,000
  商业意图: 0.85
  竞争度: 0.65
  机会评分: 78.5
  预估收益: $450-650/月
  推荐角度: 最佳智能插座选购指南
```

### 话题分析结果
```
热门话题: HomeKit智能家居设置
  类别: smart_lighting
  商业价值: 0.82
  紧急度: 0.76
  机会评分: 85.3
  内容建议: 针对Apple用户的智能家居配置教程
```

## 🔍 故障排除

### 常见问题

1. **编码错误 (Windows)**
   ```
   解决方案: 项目已集成编码处理，自动处理UTF-8/GBK转换
   ```

2. **API连接失败**
   ```bash
   # 运行诊断工具
   python scripts/validate_config.py
   ```

3. **网络请求超时**
   ```
   解决方案: 内置重试机制，自动处理网络异常
   ```

### 获得帮助
- 📖 查看 `PROJECT_STATUS.md` 了解详细状态
- 📋 查看 `TODO.md` 了解开发计划
- 🔧 运行 `validate_config.py` 诊断配置问题

## 🤝 贡献指南

1. 保持代码模块化设计
2. 使用 `safe_print` 替代直接 `print`
3. 添加适当的错误处理和重试机制
4. 更新相关文档

## 📄 许可证

本项目为内部工具，请根据实际情况添加许可证信息。

---

## 📞 开发前需要确认的事项

### 🔴 紧急确认项
1. **API密钥配置**
   - 是否已获取Reddit API密钥？
   - 是否已获取YouTube API密钥？
   - 其他数据源的API密钥状态？

2. **Telegram通知需求**
   - 是否需要立即设置Telegram Bot？
   - 通知频率和内容偏好？
   - 哪些事件需要通知？

### 🟡 重要确认项
3. **运行环境**
   - 本地开发还是服务器部署？
   - 操作系统版本 (Windows/Linux版本)？
   - Python环境配置情况？

4. **功能优先级**
   - 最需要测试的功能模块？
   - 是否需要实时监控功能？
   - 数据存储需求 (文件 vs 数据库)？

### 🟢 可选确认项
5. **扩展功能**
   - 是否需要Web管理界面？
   - 是否需要API接口？
   - 是否需要更多数据源？

### 🤔 需要了解的信息
- **使用场景**: 主要用于什么业务场景？
- **运行频率**: 计划多久运行一次分析？
- **数据量级**: 预期处理的关键词数量？
- **性能要求**: 对分析速度有特殊要求吗？

---
*最后更新: 2025-01-XX | 版本: v1.0-重构完成*