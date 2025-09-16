# Content Generation (Archived) - 文章生成功能（已归档）

## 概述

此目录包含从主要关键词分析工具中分离出来的文章生成功能。这些功能被移至归档目录，以保持主分析流程的简洁性和专注性。

## 功能说明

### ContentGenerationTrigger
- 检测高价值热点话题时自动触发文章生成
- 智能判断是否需要立即生成文章
- 防止重复生成和内容冲突
- 记录生成历史和结果

### 主要特性
- **条件评估**: 基于趋势评分、商业价值、紧急度等多维度评估
- **防重复机制**: 6小时冷却期，每日最大生成数限制
- **历史记录**: 完整的生成历史和状态跟踪
- **错误处理**: 超时、失败等异常情况的处理

## 为什么被归档？

1. **功能分离**: 主工具现在专注于关键词和话题的获取与分析
2. **简化流程**: 移除文章生成使实时分析更纯粹
3. **独立性**: 内容生成可以作为独立模块按需使用
4. **维护性**: 更清晰的模块边界，便于维护

## 使用方法

如果需要重新启用文章生成功能：

```python
from archive.content_generation import ContentGenerationTrigger, generate_content_for_topic

# 创建触发器实例
trigger = ContentGenerationTrigger()

# 检查话题是否符合生成条件
eligibility = trigger.check_generation_eligibility(topic)

# 如果符合条件，执行生成
if eligibility['eligible']:
    result = await trigger.execute_content_generation(topic)
```

## 配置要求

使用此功能需要：
1. 配置实际的文章生成脚本路径
2. 确保 `scripts/workflow_quality_enforcer.py` 存在并可执行
3. 适当的环境变量和依赖项

## 注意事项

- 此功能依赖外部的文章生成脚本
- 需要适当的文件权限和目录结构
- 日志文件会写入 `data/content_generation.log`
- 生成历史保存在 `data/generation_history/generation_log.json`

## 重新集成

如果将来需要重新集成到主流程：
1. 从归档目录导入相关模块
2. 在实时触发器中添加内容生成调用
3. 更新配置文件和依赖项
4. 确保所有外部脚本和资源可用