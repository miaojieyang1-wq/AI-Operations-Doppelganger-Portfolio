from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components


def render_html(markup: str) -> None:
    """Render a trusted local HTML snippet."""
    st.markdown(markup, unsafe_allow_html=True)


def render_div(class_name: str, content: str) -> None:
    render_html(f'<div class="{class_name}">{content}</div>')


def open_report_box() -> None:
    render_html('<div class="report-box">')


def close_div() -> None:
    render_html("</div>")


def mark_result_ready() -> None:
    st.session_state.result_focus_pending = True


def render_result_anchor() -> None:
    render_html('<div id="agent-result-top"></div>')
    if st.session_state.pop("result_focus_pending", False):
        render_div(
            "result-location-note",
            "内容已生成，已为您定位到结果区。若页面没有自动跳转，请向下查看当前模块的结果卡片。",
        )
        components.html(
            """
            <script>
            setTimeout(() => {
                const target = window.parent.document.getElementById("agent-result-top");
                if (target) {
                    target.scrollIntoView({behavior: "smooth", block: "start"});
                }
            }, 120);
            </script>
            """,
            height=0,
        )
