"""
Data sources module for real-time keyword extraction.
Provides RSS feed analysis and other data collection methods.
"""

from .rss_feed_analyzer import RSSFeedAnalyzer, RSSKeyword

__all__ = [
    'RSSFeedAnalyzer',
    'RSSKeyword'
]