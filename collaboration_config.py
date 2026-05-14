"""
多职能协作讨论的角色与目标配置。

这里保留轻量元信息，真正发送给大模型的角色提示词由 config/agents/*.yaml
通过 config_loader.get_agent_prompt() 生成。
"""

COLLABORATION_ROLES = [
    {
        "key": "market",
        "name": "市场运营",
        "emoji": "📈",
        "missing_phrase": "缺乏市场运营相关的内容",
    },
    {
        "key": "user",
        "name": "用户运营",
        "emoji": "👥",
        "missing_phrase": "缺乏用户运营相关的内容",
    },
    {
        "key": "community",
        "name": "社区运营",
        "emoji": "💬",
        "missing_phrase": "缺乏社区运营相关的内容",
    },
    {
        "key": "product",
        "name": "产品运营",
        "emoji": "🎮",
        "missing_phrase": "缺乏产品运营相关的内容",
    },
    {
        "key": "event",
        "name": "活动运营",
        "emoji": "🎪",
        "missing_phrase": "缺乏活动运营相关的内容",
    },
    {
        "key": "channel",
        "name": "渠道运营",
        "emoji": "📡",
        "missing_phrase": "缺乏渠道运营相关的内容",
    },
    {
        "key": "data",
        "name": "数据运营",
        "emoji": "📊",
        "missing_phrase": "缺乏数据运营相关的内容",
    },
    {
        "key": "content",
        "name": "内容运营",
        "emoji": "✍️",
        "missing_phrase": "缺乏内容运营相关的内容",
    },
    {
        "key": "version",
        "name": "版本运营",
        "emoji": "🔄",
        "missing_phrase": "缺乏版本运营相关的内容",
    },
    {
        "key": "monetization",
        "name": "商业化运营",
        "emoji": "💰",
        "missing_phrase": "缺乏商业化运营相关的内容",
    },
]

COLLABORATION_GOALS = [
    "无特定目标（综合评估）",
    "用户留存",
    "危机公关",
    "新用户获取",
    "回流用户召回",
    "商业化收入提升",
    "品牌口碑建设",
    "社区活跃度提升",
    "版本质量保障",
    "用户自定义",
]
