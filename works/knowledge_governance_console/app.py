# -*- coding: utf-8 -*-
"""Standalone Streamlit knowledge governance console."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import escape
from typing import Any

import streamlit as st

from utils import (
    generate_kid,
    load_badcase_log,
    load_knowledge_base,
    save_badcase_log,
    save_knowledge_base,
)

KNOWLEDGE_TYPES = ["规则", "事实", "流程片段", "经验总结"]
SOURCES = ["内部运营专家经验", "公开社区共识", "官方公告", "AI辅助推测", "数据分析结论"]
TRUST_RATINGS = ["高置信度经多方验证", "中置信度单方面来源", "低置信度待验证"]
ERROR_LEVELS = [
    "严重导致重大决策偏差",
    "中等影响分析准确性但不影响核心决策",
    "轻微细节偏差",
]
DISCOVERY_SOURCES = [
    "运营人员内部复核发现",
    "玩家社区反馈指正",
    "数据分析结果与之矛盾",
    "定期审计主动发现",
]
LOCAL_TZ = timezone(timedelta(hours=8))


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --kg-bg: #f6f7f9;
            --kg-panel: #ffffff;
            --kg-border: #dde3ea;
            --kg-muted: #64748b;
            --kg-text: #172033;
            --kg-blue: #2563eb;
            --kg-green: #15803d;
            --kg-amber: #b45309;
            --kg-red: #b91c1c;
            --kg-slate: #334155;
        }
        .stApp {
            background: linear-gradient(180deg, #f7f9fc 0%, #f3f5f8 42%, #f6f7f9 100%);
            color: var(--kg-text);
        }
        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--kg-border);
        }
        [data-testid="stSidebar"] [role="radiogroup"] label {
            border-radius: 8px;
            padding: 0.32rem 0.45rem;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: #f1f5f9;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1320px;
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        div[data-testid="stMetric"] {
            background: var(--kg-panel);
            border: 1px solid var(--kg-border);
            border-radius: 8px;
            padding: 1rem 1rem 0.85rem;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
        }
        div[data-testid="stMetric"] label {
            color: var(--kg-muted);
        }
        div[data-testid="stMetricValue"] {
            color: var(--kg-text);
            font-weight: 720;
        }
        .kg-hero {
            background: #ffffff;
            border: 1px solid var(--kg-border);
            border-radius: 8px;
            padding: 1.25rem 1.35rem;
            margin-bottom: 1rem;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.045);
        }
        .kg-eyebrow {
            color: var(--kg-blue);
            font-size: 0.78rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        .kg-hero h1 {
            font-size: 1.72rem;
            line-height: 1.25;
            margin: 0;
        }
        .kg-hero p {
            color: var(--kg-muted);
            margin: 0.42rem 0 0;
            line-height: 1.65;
        }
        .kg-section-title {
            font-size: 1.08rem;
            font-weight: 720;
            margin: 1.1rem 0 0.55rem;
        }
        .kg-card {
            background: #ffffff;
            border: 1px solid var(--kg-border);
            border-radius: 8px;
            padding: 0.92rem 1rem;
            margin-bottom: 0.72rem;
            box-shadow: 0 8px 20px rgba(15, 23, 42, 0.035);
        }
        .kg-card-title {
            font-size: 1rem;
            font-weight: 720;
            margin-bottom: 0.35rem;
        }
        .kg-card-meta {
            color: var(--kg-muted);
            font-size: 0.84rem;
            line-height: 1.75;
        }
        .kg-card-body {
            color: #334155;
            font-size: 0.9rem;
            line-height: 1.7;
            margin-top: 0.55rem;
        }
        .kg-badge {
            display: inline-block;
            border-radius: 999px;
            padding: 0.16rem 0.48rem;
            font-size: 0.76rem;
            font-weight: 650;
            margin-right: 0.28rem;
            border: 1px solid transparent;
            white-space: nowrap;
        }
        .kg-badge-green {
            color: var(--kg-green);
            background: #ecfdf3;
            border-color: #bbf7d0;
        }
        .kg-badge-amber {
            color: var(--kg-amber);
            background: #fffbeb;
            border-color: #fde68a;
        }
        .kg-badge-red {
            color: var(--kg-red);
            background: #fef2f2;
            border-color: #fecaca;
        }
        .kg-badge-blue {
            color: var(--kg-blue);
            background: #eff6ff;
            border-color: #bfdbfe;
        }
        .kg-badge-slate {
            color: var(--kg-slate);
            background: #f1f5f9;
            border-color: #cbd5e1;
        }
        .kg-empty {
            background: #ffffff;
            border: 1px dashed #cbd5e1;
            border-radius: 8px;
            padding: 1.2rem;
            color: var(--kg-muted);
            text-align: center;
        }
        .kg-timeline {
            border-left: 2px solid #dbeafe;
            padding-left: 0.85rem;
            margin: 0.35rem 0 0.8rem 0.2rem;
        }
        .kg-timeline-item {
            margin-bottom: 0.7rem;
            color: #334155;
            line-height: 1.55;
        }
        .kg-timeline-time {
            color: var(--kg-muted);
            font-size: 0.8rem;
        }
        div[data-testid="stForm"] {
            background: #ffffff;
            border: 1px solid var(--kg-border);
            border-radius: 8px;
            padding: 1rem 1rem 0.75rem;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.035);
        }
        .stButton > button, .stDownloadButton > button, div[data-testid="stFormSubmitButton"] button {
            border-radius: 7px;
            font-weight: 650;
        }
        div[data-testid="stExpander"] {
            border: 1px solid var(--kg-border);
            border-radius: 8px;
            background: #ffffff;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.03);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str, eyebrow: str = "知识治理") -> None:
    st.markdown(
        f"""
        <div class="kg-hero">
            <div class="kg-eyebrow">{escape(eyebrow)}</div>
            <h1>{escape(title)}</h1>
            <p>{escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_title(title: str) -> None:
    st.markdown(f'<div class="kg-section-title">{escape(title)}</div>', unsafe_allow_html=True)


def badge(label: Any, tone: str = "slate") -> str:
    return f'<span class="kg-badge kg-badge-{tone}">{escape(str(label or "未指定"))}</span>'


def status_tone(status: Any) -> str:
    if status == "已作废":
        return "red"
    if status in {"待审核", "低置信度待验证"}:
        return "amber"
    if status in {"确认成立", "生效中", "高置信度经多方验证"}:
        return "green"
    if status == "中置信度单方面来源":
        return "blue"
    return "slate"


def render_knowledge_card(item: dict[str, Any], include_body: bool = True) -> None:
    owner = item.get("owner") or "未指定"
    expiry = item.get("expiry_date") or "长期有效"
    body = f'<div class="kg-card-body">{escape(summarize(item.get("content", ""), 150))}</div>' if include_body else ""
    st.markdown(
        f"""
        <div class="kg-card">
            <div class="kg-card-title">{escape(str(item.get("knowledge_id", "")))}｜{escape(str(item.get("title", "")))}</div>
            <div>
                {badge(item.get("status", "生效中"), status_tone(item.get("status", "生效中")))}
                {badge(item.get("knowledge_type", "未分类"), "blue")}
                {badge(item.get("trust_rating", "未评级"), status_tone(item.get("trust_rating")))}
            </div>
            <div class="kg-card-meta">
                责任人：{escape(str(owner))}｜审批人：{escape(str(item.get("approver") or "未指定"))}｜
                生效：{escape(str(item.get("effective_date") or "未设置"))}｜失效：{escape(str(expiry))}
            </div>
            {body}
        </div>
        """,
        unsafe_allow_html=True,
    )


def now_iso() -> str:
    return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")


def parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def summarize(text: str, limit: int = 120) -> str:
    clean_text = " ".join(str(text or "").split())
    return clean_text if len(clean_text) <= limit else f"{clean_text[:limit]}..."


def get_knowledge_label(item: dict[str, Any]) -> str:
    return f"{item.get('knowledge_id', '')}｜{item.get('title', '')}"


def find_knowledge_index(data: list[dict[str, Any]], knowledge_id: str) -> int | None:
    for index, item in enumerate(data):
        if item.get("knowledge_id") == knowledge_id:
            return index
    return None


def increment_version(version: str) -> str:
    try:
        return f"{float(version) + 0.1:.1f}"
    except (TypeError, ValueError):
        return "1.1"


def add_modification_log(item: dict[str, Any], modifier: str, summary: str) -> None:
    logs = item.setdefault("modification_logs", [])
    logs.append(
        {
            "modified_at": now_iso(),
            "modifier": modifier.strip() or "未指定",
            "summary": summary,
        }
    )
    item["updated_at"] = now_iso()


def classify_knowledge(data: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    today = date.today()
    soon = today + timedelta(days=30)
    expired: list[dict[str, Any]] = []
    expiring_soon: list[dict[str, Any]] = []
    owner_missing: list[dict[str, Any]] = []
    pending_verify: list[dict[str, Any]] = []

    for item in data:
        expiry_date = parse_date(item.get("expiry_date"))
        effective_date = parse_date(item.get("effective_date"))
        status = item.get("status", "")
        owner = str(item.get("owner", "")).strip()
        if expiry_date and expiry_date < today and status != "已作废":
            expired.append(item)
        if expiry_date and today <= expiry_date <= soon and status != "已作废":
            expiring_soon.append(item)
        if not owner or owner == "未指定":
            owner_missing.append(item)
        if (
            item.get("trust_rating") == "低置信度待验证"
            and effective_date
            and effective_date <= today - timedelta(days=30)
        ):
            pending_verify.append(item)
    return {
        "expired": expired,
        "expiring_soon": expiring_soon,
        "owner_missing": owner_missing,
        "pending_verify": pending_verify,
    }


def render_knowledge_list(items: list[dict[str, Any]]) -> None:
    if not items:
        st.markdown('<div class="kg-empty">当前没有符合条件的知识单元。</div>', unsafe_allow_html=True)
        return
    for item in items:
        render_knowledge_card(item)


def page_register() -> None:
    render_page_header(
        "知识单元注册中心",
        "把零散经验沉淀成可追溯、可审批、可被下游系统消费的标准知识单元。",
        "生产入口",
    )
    with st.form("knowledge_register_form", clear_on_submit=True):
        left_col, right_col = st.columns([1.25, 1])
        with left_col:
            title = st.text_input("知识标题", placeholder="例如：日本市场付费意愿更多与CV相关")
            content = st.text_area("知识内容", height=190, placeholder="写清楚结论、依据和适用边界。")
            scope = st.text_area("适用范围（可选）", height=90, placeholder="例如：市场运营Agent、竞品雷达模块、日服分析")
        with right_col:
            knowledge_type = st.selectbox("知识类型", KNOWLEDGE_TYPES)
            source = st.selectbox("来源标注", SOURCES)
            trust_rating = st.selectbox("信任度评级", TRUST_RATINGS)
            creator = st.text_input("创建者")
            owner = st.text_input("责任人")
            approver = st.text_input("审批人")
            date_col_1, date_col_2 = st.columns(2)
            with date_col_1:
                effective_date = st.date_input("生效日期", value=date.today())
            with date_col_2:
                has_expiry = st.checkbox("设置失效日期")
                expiry_date = st.date_input(
                    "失效日期",
                    value=date.today() + timedelta(days=365),
                    disabled=not has_expiry,
                )
        submitted = st.form_submit_button("注册知识单元", type="primary")

    if submitted:
        if not title.strip() or not content.strip():
            st.error("知识标题和知识内容不能为空。")
            return
        data = load_knowledge_base()
        new_item = {
            "knowledge_id": generate_kid(),
            "title": title.strip(),
            "content": content.strip(),
            "knowledge_type": knowledge_type,
            "creator": creator.strip(),
            "owner": owner.strip(),
            "approver": approver.strip(),
            "effective_date": effective_date.isoformat(),
            "expiry_date": expiry_date.isoformat() if has_expiry else "",
            "source": source,
            "trust_rating": trust_rating,
            "version": "1.0",
            "scope": scope.strip(),
            "status": "生效中",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "modification_logs": [],
        }
        data.append(new_item)
        save_knowledge_base(data)
        st.success("知识单元已成功注册")


def page_dashboard() -> None:
    render_page_header(
        "知识库健康度仪表盘",
        "集中观察过期、责任缺失、低置信度和即将失效的知识风险。",
        "质量总览",
    )
    data = load_knowledge_base()
    classified = classify_knowledge(data)

    metrics = [
        ("知识总量", len(data), "all"),
        ("已过期知识数量", len(classified["expired"]), "expired"),
        ("即将过期知识数量", len(classified["expiring_soon"]), "expiring_soon"),
        ("无责任人的知识数量", len(classified["owner_missing"]), "owner_missing"),
        ("待验证知识数量", len(classified["pending_verify"]), "pending_verify"),
    ]
    columns = st.columns(len(metrics))
    for column, (label, value, filter_name) in zip(columns, metrics):
        with column:
            st.metric(label, value)
            if st.button("查看清单", key=f"metric_{filter_name}"):
                st.session_state["knowledge_filter"] = filter_name
                st.session_state["page"] = "知识清单"
                st.rerun()

    render_section_title("需要关注")
    attention_items = [
        ("已过期但未作废的知识", classified["expired"]),
        ("责任人缺失的知识", classified["owner_missing"]),
        ("即将在30天内过期的知识", classified["expiring_soon"]),
        ("长期未审核的待验证知识", classified["pending_verify"]),
    ]
    has_attention = False
    for title, items in attention_items:
        if items:
            has_attention = True
            with st.expander(f"{title}（{len(items)}）", expanded=True):
                render_knowledge_list(items)
    if not has_attention:
        st.markdown('<div class="kg-empty">当前没有需要重点关注的知识治理事项。</div>', unsafe_allow_html=True)


def page_knowledge_list() -> None:
    render_page_header(
        "知识清单",
        "从仪表盘钻取到具体知识项，快速定位需要治理的对象。",
        "清单视图",
    )
    data = load_knowledge_base()
    classified = classify_knowledge(data)
    filter_options = {
        "all": "全部知识",
        "expired": "已过期知识",
        "expiring_soon": "即将过期知识",
        "owner_missing": "无责任人知识",
        "pending_verify": "待验证知识",
    }
    selected_filter = st.selectbox(
        "筛选条件",
        list(filter_options.keys()),
        index=list(filter_options.keys()).index(st.session_state.get("knowledge_filter", "all")),
        format_func=lambda value: filter_options[value],
    )
    st.session_state["knowledge_filter"] = selected_filter
    items = data if selected_filter == "all" else classified[selected_filter]
    st.caption(f"当前筛选：{filter_options[selected_filter]}｜共 {len(items)} 条")
    render_knowledge_list(items)


def render_update_form(item: dict[str, Any], item_index: int, data: list[dict[str, Any]], prefix: str) -> None:
    with st.form(f"{prefix}_update_form"):
        new_content = st.text_area("知识内容", value=item.get("content", ""), height=160)
        new_approver = st.text_input("审批人", value=item.get("approver", ""))
        new_trust = st.selectbox(
            "信任度评级",
            TRUST_RATINGS,
            index=TRUST_RATINGS.index(item.get("trust_rating")) if item.get("trust_rating") in TRUST_RATINGS else 0,
        )
        has_expiry = st.checkbox("设置失效日期", value=bool(item.get("expiry_date")), key=f"{prefix}_has_expiry")
        current_expiry = parse_date(item.get("expiry_date")) or date.today()
        new_expiry = st.date_input("失效日期", value=current_expiry, disabled=not has_expiry)
        modifier = st.text_input("修改人", value=item.get("owner", ""))
        submitted = st.form_submit_button("确认更新", type="primary")
    if submitted:
        previous_snapshot = {
            "version": item.get("version"),
            "content_summary": summarize(item.get("content", "")),
            "approver": item.get("approver", ""),
            "trust_rating": item.get("trust_rating", ""),
            "expiry_date": item.get("expiry_date", ""),
        }
        item["content"] = new_content.strip()
        item["approver"] = new_approver.strip()
        item["trust_rating"] = new_trust
        item["expiry_date"] = new_expiry.isoformat() if has_expiry else ""
        item["version"] = increment_version(str(item.get("version", "1.0")))
        add_modification_log(item, modifier, f"更新知识内容与治理字段；旧版本归档：{previous_snapshot}")
        data[item_index] = item
        save_knowledge_base(data)
        st.success("知识单元已更新，版本号已自动递增。")
        st.rerun()


def render_trust_form(item: dict[str, Any], item_index: int, data: list[dict[str, Any]], prefix: str) -> None:
    with st.form(f"{prefix}_trust_form"):
        new_trust = st.selectbox(
            "新的信任度评级",
            TRUST_RATINGS,
            index=TRUST_RATINGS.index(item.get("trust_rating")) if item.get("trust_rating") in TRUST_RATINGS else 0,
        )
        modifier = st.text_input("修改人", value=item.get("owner", ""), key=f"{prefix}_trust_modifier")
        submitted = st.form_submit_button("确认修正信任度")
    if submitted:
        old_trust = item.get("trust_rating", "")
        item["trust_rating"] = new_trust
        add_modification_log(item, modifier, f"信任度评级由“{old_trust}”修正为“{new_trust}”；版本号不变")
        data[item_index] = item
        save_knowledge_base(data)
        st.success("信任度评级已修正。")
        st.rerun()


def render_responsibility_detail(item: dict[str, Any], item_index: int, data: list[dict[str, Any]], prefix: str) -> None:
    render_knowledge_card(item)
    detail_col_1, detail_col_2, detail_col_3 = st.columns(3)
    detail_col_1.markdown(
        f"**创建者**  \n{item.get('creator') or '未指定'}  \n\n"
        f"**责任人**  \n{item.get('owner') or '未指定'}"
    )
    detail_col_2.markdown(
        f"**审批人**  \n{item.get('approver') or '未指定'}  \n\n"
        f"**来源标注**  \n{item.get('source') or '未指定'}"
    )
    detail_col_3.markdown(
        f"**版本号**  \n{item.get('version') or '未指定'}  \n\n"
        f"**失效日期**  \n{item.get('expiry_date') or '长期有效'}"
    )
    logs = item.get("modification_logs", [])
    with st.expander(f"修改日志（{len(logs)}）"):
        if logs:
            st.markdown('<div class="kg-timeline">', unsafe_allow_html=True)
            for log in reversed(logs):
                st.markdown(
                    f"""
                    <div class="kg-timeline-item">
                        <div class="kg-timeline-time">{escape(str(log.get('modified_at') or ''))}</div>
                        <strong>{escape(str(log.get('modifier') or '未指定'))}</strong>｜{escape(str(log.get('summary') or ''))}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("暂无修改日志。")

    render_section_title("修正操作")
    action = st.radio("选择操作", ["作废", "更新", "修正信任度评级"], horizontal=True, key=f"{prefix}_action")
    if action == "作废":
        with st.form(f"{prefix}_void_form"):
            modifier = st.text_input("操作人", value=item.get("owner", ""))
            confirmed = st.checkbox("确认将该知识单元标记为已作废")
            submitted = st.form_submit_button("确认作废")
        if submitted:
            if not confirmed:
                st.warning("请先勾选二次确认。")
                return
            item["status"] = "已作废"
            add_modification_log(item, modifier, "知识状态标记为已作废")
            data[item_index] = item
            save_knowledge_base(data)
            st.success("知识单元已作废。")
            st.rerun()
    elif action == "更新":
        render_update_form(item, item_index, data, prefix)
    else:
        render_trust_form(item, item_index, data, prefix)


def page_trace() -> None:
    render_page_header(
        "责任归属与错误追溯工作台",
        "搜索知识项，查看责任链、版本记录，并在同一工作台完成作废、更新或信任度修正。",
        "追溯工作台",
    )
    data = load_knowledge_base()
    query = st.text_input(
        "按知识ID或关键词搜索",
        value=st.session_state.pop("trace_query", ""),
        placeholder="输入 KID、标题关键词或内容关键词",
    )
    lowered_query = query.strip().lower()
    results = [
        item
        for item in data
        if not lowered_query
        or lowered_query in str(item.get("knowledge_id", "")).lower()
        or lowered_query in str(item.get("title", "")).lower()
        or lowered_query in str(item.get("content", "")).lower()
    ]
    st.caption(f"找到 {len(results)} 条匹配知识")
    for item in results:
        prefix = f"trace_{item.get('knowledge_id')}"
        with st.expander(get_knowledge_label(item)):
            render_knowledge_card(item, include_body=False)
            if st.button("查看责任详情", key=f"{prefix}_detail"):
                st.session_state[f"{prefix}_show_detail"] = True
            if st.session_state.get(f"{prefix}_show_detail"):
                item_index = find_knowledge_index(data, item.get("knowledge_id", ""))
                if item_index is not None:
                    render_responsibility_detail(item, item_index, data, prefix)


def page_badcase() -> None:
    render_page_header(
        "Badcase回流",
        "把错误案例回流到知识治理链路，暴露高频出错知识并推动修正闭环。",
        "反馈闭环",
    )
    data = load_knowledge_base()
    badcases = load_badcase_log()
    knowledge_options = [item.get("knowledge_id", "") for item in data]
    labels = {item.get("knowledge_id", ""): get_knowledge_label(item) for item in data}
    if not knowledge_options:
        st.warning("知识库为空，请先注册知识单元后再提报Badcase。")
        return

    form_col, board_col = st.columns([1.12, 1])
    with form_col:
        with st.form("badcase_form", clear_on_submit=True):
            related_id = st.selectbox(
                "关联知识ID（搜索并自动关联）",
                knowledge_options,
                format_func=lambda value: labels.get(value, value),
            )
            description = st.text_area("错误描述", height=150, placeholder="描述错误表现、触发场景和影响范围。")
            lower_col, right_col = st.columns(2)
            with lower_col:
                error_level = st.selectbox("错误等级", ERROR_LEVELS)
                reporter = st.text_input("提报人")
            with right_col:
                discovery_source = st.selectbox("发现来源", DISCOVERY_SOURCES)
            submitted = st.form_submit_button("提交Badcase", type="primary")
    if submitted:
        if not related_id or not description.strip():
            st.error("关联知识ID和错误描述不能为空。")
        else:
            badcases.append(
                {
                    "badcase_id": f"BC-{datetime.now(LOCAL_TZ).strftime('%Y%m%d%H%M%S')}-{len(badcases) + 1:03d}",
                    "related_knowledge_id": related_id,
                    "description": description.strip(),
                    "error_level": error_level,
                    "discovery_source": discovery_source,
                    "reporter": reporter.strip(),
                    "status": "待审核",
                    "reject_reason": "",
                    "submitted_at": now_iso(),
                    "reviewed_at": "",
                    "reviewer": "",
                }
            )
            save_badcase_log(badcases)
            st.success("Badcase已提交。")
            st.rerun()

    pending = [item for item in badcases if item.get("status") == "待审核"]
    level_counter = Counter(item.get("error_level", "未指定") for item in badcases)
    knowledge_counter = Counter(item.get("related_knowledge_id", "未关联") for item in badcases)

    with board_col:
        st.metric("未处理Badcase数量", len(pending))
        st.write("**按错误等级分布**")
        if level_counter:
            st.bar_chart(dict(level_counter), horizontal=True)
        else:
            st.caption("暂无错误等级数据")
        st.write("**高频关联知识**")
        if knowledge_counter:
            st.bar_chart(dict(knowledge_counter.most_common(8)), horizontal=True)
        else:
            st.caption("暂无关联知识数据")

    render_section_title("最近提交")
    recent_badcases = sorted(badcases, key=lambda item: item.get("submitted_at", ""), reverse=True)
    if not recent_badcases:
        st.markdown('<div class="kg-empty">暂无Badcase记录。</div>', unsafe_allow_html=True)
        return
    for badcase in recent_badcases:
        prefix = f"badcase_{badcase.get('badcase_id')}"
        with st.expander(
            f"{badcase.get('badcase_id')}｜{badcase.get('status')}｜"
            f"{badcase.get('related_knowledge_id')}｜{badcase.get('error_level')}"
        ):
            st.markdown(
                f"""
                <div class="kg-card">
                    <div class="kg-card-title">{escape(str(badcase.get('badcase_id')))}｜{escape(str(badcase.get('related_knowledge_id')))}</div>
                    <div>
                        {badge(badcase.get('status'), status_tone(badcase.get('status')))}
                        {badge(badcase.get('error_level'), 'amber')}
                        {badge(badcase.get('discovery_source'), 'blue')}
                    </div>
                    <div class="kg-card-meta">提报人：{escape(str(badcase.get('reporter') or '未指定'))}｜提交时间：{escape(str(badcase.get('submitted_at') or ''))}</div>
                    <div class="kg-card-body">{escape(str(badcase.get('description') or ''))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if badcase.get("status") != "待审核":
                st.caption(f"审核人：{badcase.get('reviewer') or '未指定'}｜审核时间：{badcase.get('reviewed_at') or '无'}")
                continue
            if st.button("审核", key=f"{prefix}_review_button"):
                st.session_state[f"{prefix}_review"] = True
            if st.session_state.get(f"{prefix}_review"):
                decision = st.radio(
                    "审核结论",
                    ["确认成立并修正", "驳回"],
                    horizontal=True,
                    key=f"{prefix}_decision",
                )
                if decision == "确认成立并修正":
                    reviewer = st.text_input("审核人", key=f"{prefix}_reviewer")
                    if st.button("进入知识修正", key=f"{prefix}_confirm"):
                        badcase["status"] = "确认成立"
                        badcase["reviewed_at"] = now_iso()
                        badcase["reviewer"] = reviewer.strip()
                        save_badcase_log(badcases)
                        st.session_state["trace_query"] = badcase.get("related_knowledge_id", "")
                        st.session_state["page"] = "责任归属与错误追溯工作台"
                        st.success("Badcase已确认，请在追溯工作台完成知识修正。")
                        st.rerun()
                else:
                    with st.form(f"{prefix}_reject_form"):
                        reviewer = st.text_input("审核人")
                        reason = st.text_area("驳回理由")
                        rejected = st.form_submit_button("确认驳回")
                    if rejected:
                        badcase["status"] = "已驳回"
                        badcase["reject_reason"] = reason.strip()
                        badcase["reviewed_at"] = now_iso()
                        badcase["reviewer"] = reviewer.strip()
                        save_badcase_log(badcases)
                        st.success("Badcase已驳回。")
                        st.rerun()


def main() -> None:
    st.set_page_config(page_title="知识治理控制台", layout="wide")
    apply_theme()

    pages = [
        "知识单元注册中心",
        "知识库健康度仪表盘",
        "知识清单",
        "责任归属与错误追溯工作台",
        "Badcase回流",
    ]
    default_page = st.session_state.get("page", pages[0])
    st.sidebar.markdown("### 知识治理控制台")
    st.sidebar.caption("生产、校验与回流知识库质量")
    selected_page = st.sidebar.radio("导航", pages, index=pages.index(default_page) if default_page in pages else 0)
    st.session_state["page"] = selected_page
    st.sidebar.divider()
    st.sidebar.caption("数据文件")
    st.sidebar.code("data/knowledge_base.json\ndata/badcase_log.json", language="text")

    if selected_page == "知识单元注册中心":
        page_register()
    elif selected_page == "知识库健康度仪表盘":
        page_dashboard()
    elif selected_page == "知识清单":
        page_knowledge_list()
    elif selected_page == "责任归属与错误追溯工作台":
        page_trace()
    else:
        page_badcase()


if __name__ == "__main__":
    main()
