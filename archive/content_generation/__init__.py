"""
Content Generation Package (Archived) - 文章生成包（已归档）

此包包含从主分析流程中分离出来的内容生成功能。
保留这些功能是为了将来可能的独立使用或重新集成。

包含：
- ContentGenerationTrigger: 文章生成触发器
- 相关的配置和历史记录管理

注意：此功能已从实时分析中移除，现在的实时触发器专注于纯分析输出。
"""

from .content_trigger import ContentGenerationTrigger, generate_content_for_topic

__all__ = [
    'ContentGenerationTrigger',
    'generate_content_for_topic'
]