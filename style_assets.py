from __future__ import annotations

import streamlit as st


MAIN_CSS = '\n        <style>\n        :root {\n            --ink: #111827;\n            --muted: #667085;\n            --line: #e5e7eb;\n            --soft: #f8fafc;\n            --accent: #0f766e;\n            --accent-dark: #115e59;\n            --warn: #b45309;\n        }\n        html, body, [class*="css"] {\n            color: var(--ink);\n        }\n        .main .block-container {\n            max-width: 1120px;\n            padding-top: 1.4rem;\n            padding-bottom: 3rem;\n        }\n        div[data-testid="stSidebar"] {\n            background: #f8fafc;\n            border-right: 1px solid #e5e7eb;\n        }\n        .hero-band {\n            border: 1px solid #e5e7eb;\n            border-radius: 8px;\n            background: #ffffff;\n            padding: 1.4rem 1.5rem 1.25rem;\n            margin-bottom: 1rem;\n            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);\n        }\n        .hero-eyebrow {\n            color: #0f766e;\n            font-size: 0.86rem;\n            font-weight: 700;\n            margin-bottom: 0.35rem;\n        }\n        .app-title {\n            font-size: 2.25rem;\n            font-weight: 760;\n            line-height: 1.18;\n            margin: 0 0 0.45rem;\n            color: var(--ink);\n            letter-spacing: 0;\n        }\n        .app-subtitle {\n            color: #475467;\n            font-size: 1.02rem;\n            max-width: 780px;\n            line-height: 1.65;\n            margin-bottom: 0.95rem;\n        }\n        .hero-proof-row {\n            display: flex;\n            flex-wrap: wrap;\n            gap: 0.5rem;\n            margin-top: 0.9rem;\n        }\n        .hero-proof {\n            border: 1px solid #d7e5e1;\n            border-radius: 999px;\n            color: #134e4a;\n            background: #f0fdfa;\n            font-size: 0.84rem;\n            padding: 0.35rem 0.7rem;\n        }\n        div.stButton > button {\n            min-height: 3rem;\n            width: 100%;\n            border-radius: 8px;\n            font-size: 0.98rem;\n            font-weight: 700;\n            border: 1px solid #d0d5dd;\n            box-shadow: none;\n        }\n        div[data-testid="stSidebar"] .stButton {\n            margin-bottom: 0.55rem;\n        }\n        div[data-testid="stSidebar"] div.stButton > button {\n            justify-content: flex-start;\n            padding-left: 0.9rem;\n        }\n        .sidebar-brand {\n            border: 1px solid #e5e7eb;\n            border-radius: 8px;\n            padding: 0.9rem;\n            background: #ffffff;\n            margin-bottom: 1rem;\n        }\n        .sidebar-hello {\n            font-size: 1.7rem;\n            line-height: 1;\n            margin: 0 0 0.55rem;\n        }\n        .sidebar-title {\n            font-size: 1.16rem;\n            font-weight: 760;\n            color: var(--ink);\n            margin-bottom: 0.25rem;\n        }\n        .sidebar-subtitle {\n            color: #667085;\n            font-size: 0.85rem;\n            line-height: 1.55;\n        }\n        div[data-testid="stSidebar"] div[data-testid="stExpander"] {\n            border: 0;\n            background: transparent;\n            margin-top: 1.4rem;\n        }\n        div[data-testid="stSidebar"] div[data-testid="stExpander"] summary {\n            color: #98a2b3;\n            font-size: 0.82rem;\n            font-weight: 500;\n        }\n        .status-line {\n            color: #667085;\n            font-size: 0.86rem;\n            line-height: 1.7;\n            margin: 0.1rem 0;\n        }\n        .status-muted {\n            color: #98a2b3;\n            font-size: 0.82rem;\n            line-height: 1.65;\n        }\n        .mode-strip {\n            display: grid;\n            grid-template-columns: repeat(5, minmax(0, 1fr));\n            gap: 0.75rem;\n            margin: 0 0 1.2rem;\n        }\n        .mode-tile {\n            border: 1px solid #e5e7eb;\n            border-radius: 8px;\n            background: #ffffff;\n            padding: 0.9rem 1rem;\n        }\n        .mode-tile-active {\n            border-color: #99d6cf;\n            background: #f0fdfa;\n        }\n        .mode-label {\n            font-weight: 740;\n            color: #111827;\n            margin-bottom: 0.2rem;\n        }\n        .mode-desc {\n            color: #667085;\n            font-size: 0.9rem;\n            line-height: 1.55;\n        }\n        .task-panel {\n            border: 1px solid #e5e7eb;\n            border-radius: 8px;\n            background: #ffffff;\n            padding: 1.15rem 1.2rem 1.25rem;\n            margin-top: 0.6rem;\n            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.03);\n        }\n        .task-kicker {\n            color: #0f766e;\n            font-size: 0.82rem;\n            font-weight: 760;\n            margin-bottom: 0.2rem;\n        }\n        .task-title {\n            font-size: 1.28rem;\n            font-weight: 760;\n            color: #111827;\n            margin-bottom: 0.25rem;\n        }\n        .task-desc {\n            color: #667085;\n            font-size: 0.95rem;\n            line-height: 1.65;\n            margin-bottom: 0.9rem;\n        }\n        .section-title {\n            color: #111827;\n            font-size: 1.05rem;\n            font-weight: 650;\n            margin: 1.4rem 0 0.5rem;\n        }\n        .report-box {\n            border: 1px solid #e5e7eb;\n            border-radius: 8px;\n            background: #ffffff;\n            margin-top: 1.1rem;\n            padding: 1.1rem 1.2rem;\n            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);\n        }\n        .result-note {\n            color: #667085;\n            font-size: 0.92rem;\n            margin-bottom: 0.8rem;\n        }\n        .result-location-note {\n            color: #155e75;\n            background: #ecfeff;\n            border: 1px solid #a5f3fc;\n            padding: 0.62rem 0.82rem;\n            border-radius: 8px;\n            margin-bottom: 0.85rem;\n            font-size: 0.92rem;\n        }\n        .chat-empty {\n            border: 1px dashed #d0d5dd;\n            border-radius: 8px;\n            background: #ffffff;\n            color: #98a2b3;\n            font-size: 0.92rem;\n            line-height: 1.7;\n            text-align: center;\n            padding: 0.85rem 1rem;\n            margin: 0.8rem 0 0.9rem;\n        }\n        .preset-title {\n            color: #111827;\n            font-size: 0.96rem;\n            font-weight: 700;\n            margin: 0.2rem 0 0.6rem;\n        }\n        .faq-hint {\n            color: #667085;\n            font-size: 0.9rem;\n            line-height: 1.6;\n            margin: 0.2rem 0 0.6rem;\n        }\n        .portfolio-guide {\n            border: 1px solid #99d6cf;\n            border-radius: 8px;\n            background: #f0fdfa;\n            color: #134e4a;\n            font-size: 0.92rem;\n            line-height: 1.65;\n            padding: 0.75rem 0.85rem;\n            margin: 0.85rem 0;\n        }\n        .document-preview-note {\n            border: 1px solid #bfdbfe;\n            border-radius: 8px;\n            background: #eff6ff;\n            color: #1e3a8a;\n            font-size: 0.92rem;\n            line-height: 1.65;\n            padding: 0.75rem 0.85rem;\n            margin: 0.6rem 0 0.9rem;\n        }\n        .document-outline {\n            color: #344054;\n            font-size: 0.92rem;\n            line-height: 1.7;\n        }\n        .decision-hero {\n            border: 1px solid #d7e5e1;\n            border-radius: 8px;\n            background: #ffffff;\n            padding: 1.45rem 1.5rem;\n            margin-bottom: 1rem;\n            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);\n        }\n        .decision-title {\n            color: #111827;\n            font-size: 2rem;\n            font-weight: 780;\n            line-height: 1.2;\n            margin-bottom: 0.35rem;\n        }\n        .decision-subtitle {\n            color: #667085;\n            font-size: 1rem;\n            line-height: 1.65;\n        }\n        .roadmap-overview {\n            border: 1px solid #e5e7eb;\n            border-radius: 8px;\n            background: #ffffff;\n            padding: 1rem 1.1rem;\n            margin: 0 0 1rem;\n            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.03);\n        }\n        .roadmap-chain {\n            display: grid;\n            grid-template-columns: repeat(9, auto);\n            align-items: center;\n            justify-content: center;\n            gap: 0.45rem;\n            margin-bottom: 0.55rem;\n        }\n        .roadmap-dot {\n            width: 1.25rem;\n            height: 1.25rem;\n            border-radius: 999px;\n            border: 1px solid #d0d5dd;\n            background: #f2f4f7;\n            color: #667085;\n            display: inline-flex;\n            align-items: center;\n            justify-content: center;\n            font-size: 0.72rem;\n            font-weight: 800;\n        }\n        .roadmap-dot-active {\n            border-color: #0f766e;\n            background: #ccfbf1;\n            color: #134e4a;\n        }\n        .roadmap-line {\n            width: clamp(1.2rem, 7vw, 5rem);\n            height: 1px;\n            background: #d0d5dd;\n        }\n        .roadmap-line-active {\n            background: #5eead4;\n        }\n        .roadmap-hint {\n            color: #667085;\n            font-size: 0.9rem;\n            text-align: center;\n        }\n        .roadmap-stage-wrap {\n            position: relative;\n        }\n        .roadmap-card {\n            border: 1px solid #e5e7eb;\n            border-radius: 8px;\n            background: #ffffff;\n            padding: 1rem 1.1rem 1.05rem;\n            margin: 0;\n            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.03);\n            display: grid;\n            grid-template-columns: auto 1fr;\n            gap: 0.9rem;\n            align-items: start;\n        }\n        .roadmap-card-active {\n            border-color: #99d6cf;\n            background: #f8fffd;\n            box-shadow: 0 8px 22px rgba(15, 118, 110, 0.08);\n        }\n        .roadmap-number {\n            width: 2.2rem;\n            height: 2.2rem;\n            border-radius: 999px;\n            border: 1px solid #99d6cf;\n            color: #134e4a;\n            background: #ffffff;\n            display: inline-flex;\n            align-items: center;\n            justify-content: center;\n            font-weight: 800;\n            font-size: 1.05rem;\n        }\n        .roadmap-title {\n            color: #111827;\n            font-size: 1.16rem;\n            font-weight: 760;\n            margin-bottom: 0.25rem;\n        }\n        .roadmap-desc {\n            color: #667085;\n            font-size: 0.94rem;\n            line-height: 1.6;\n        }\n        .roadmap-workbench {\n            display: grid;\n            grid-template-columns: minmax(0, 1.05fr) minmax(280px, 0.95fr);\n            gap: 1rem;\n            margin-top: 0.95rem;\n            padding-top: 0.95rem;\n            border-top: 1px solid #e5e7eb;\n        }\n        .roadmap-info-title,\n        .roadmap-action-title {\n            color: #134e4a;\n            font-weight: 760;\n            font-size: 0.94rem;\n            margin: 0 0 0.35rem;\n        }\n        .roadmap-info-text {\n            color: #475467;\n            font-size: 0.92rem;\n            line-height: 1.65;\n            margin-bottom: 0.75rem;\n        }\n        .roadmap-action-desc {\n            color: #667085;\n            font-size: 0.86rem;\n            line-height: 1.55;\n            margin: -0.15rem 0 0.75rem;\n        }\n        .roadmap-next-hint {\n            color: #0f766e;\n            background: #f0fdfa;\n            border: 1px solid #ccfbf1;\n            border-radius: 8px;\n            padding: 0.65rem 0.8rem;\n            margin-top: 0.9rem;\n            font-size: 0.9rem;\n            line-height: 1.55;\n        }\n        .roadmap-connector {\n            height: 2.5rem;\n            display: flex;\n            align-items: center;\n            justify-content: center;\n            color: #99a3b3;\n            font-size: 1rem;\n        }\n        .roadmap-connector-inner {\n            height: 100%;\n            border-left: 1px dashed #b7c0cd;\n            display: flex;\n            align-items: center;\n            justify-content: center;\n            width: 1px;\n            position: relative;\n        }\n        .roadmap-arrow {\n            position: absolute;\n            background: #f8fafc;\n            color: #0f766e;\n            padding: 0.05rem 0;\n            line-height: 1;\n        }\n        .stage-card {\n            border: 1px solid #e5e7eb;\n            border-radius: 8px;\n            background: #ffffff;\n            padding: 1rem 1.1rem 1.05rem;\n            margin: 0 0 0.85rem;\n            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.03);\n        }\n        .stage-title {\n            color: #111827;\n            font-size: 1.16rem;\n            font-weight: 760;\n            margin-bottom: 0.25rem;\n        }\n        .stage-desc {\n            color: #667085;\n            font-size: 0.94rem;\n            line-height: 1.6;\n        }\n        @media (max-width: 820px) {\n            .roadmap-workbench {\n                grid-template-columns: 1fr;\n            }\n            .roadmap-chain {\n                gap: 0.28rem;\n            }\n            .roadmap-line {\n                width: 1.25rem;\n            }\n        }\n        .footer-note {\n            text-align: center;\n            color: #98a2b3;\n            font-size: 0.82rem;\n            margin-top: 2.6rem;\n            padding-top: 1.2rem;\n        }\n        div[data-testid="stDialog"] h2,\n        div[role="dialog"] h2 {\n            display: none;\n        }\n        div[data-testid="stDialog"] div[role="dialog"],\n        div[data-testid="stDialog"] section[role="dialog"] {\n            width: min(1180px, 94vw);\n            max-width: 94vw;\n        }\n        div[data-testid="stDialog"] img {\n            max-height: min(64vh, 620px);\n            object-fit: contain;\n        }\n        div[data-testid="stDialog"] div.stButton > button[kind="primary"] {\n            background: #f0fdfa;\n            color: #134e4a;\n            border: 1px solid #99d6cf;\n            box-shadow: none;\n        }\n        div[data-testid="stDialog"] div.stButton > button[kind="primary"]:hover {\n            background: #ccfbf1;\n            color: #115e59;\n            border-color: #5eead4;\n        }\n        .entry-loading-note {\n            color: #667085;\n            font-size: 0.84rem;\n            text-align: center;\n            line-height: 1.5;\n            margin: 0.35rem 0 0.65rem;\n        }\n        .entry-welcome-copy {\n            color: #344054;\n            font-size: 0.92rem;\n            line-height: 1.58;\n            margin: 0.05rem 0 0.8rem;\n        }\n        .entry-welcome-copy p {\n            margin: 0 0 0.36rem;\n        }\n        .entry-welcome-copy p:first-child {\n            color: #101828;\n            font-size: 1.18rem;\n            font-weight: 800;\n        }\n        .entry-ps {\n            color: #667085;\n            font-size: 0.82rem;\n            line-height: 1.55;\n            margin-top: 0.6rem !important;\n        }\n        @media (max-width: 760px) {\n            .mode-strip {\n                grid-template-columns: 1fr;\n            }\n            .app-title {\n                font-size: 1.75rem;\n            }\n        }\n        </style>\n        '

ENTRY_CSS = '\n        <style>\n        .block-container {\n            padding-top: 1.2rem;\n        }\n        div[data-testid="stDialog"] h2,\n        div[role="dialog"] h2 {\n            display: none;\n        }\n        div[data-testid="stDialog"] div[role="dialog"],\n        div[data-testid="stDialog"] section[role="dialog"] {\n            width: min(1180px, 94vw);\n            max-width: 94vw;\n        }\n        div[data-testid="stDialog"] div.stButton > button[kind="primary"] {\n            background: #f0fdfa;\n            color: #134e4a;\n            border: 1px solid #99d6cf;\n            box-shadow: none;\n        }\n        div[data-testid="stDialog"] div.stButton > button[kind="primary"]:hover {\n            background: #ccfbf1;\n            color: #115e59;\n            border-color: #5eead4;\n        }\n        .entry-loading-note {\n            color: #667085;\n            font-size: 0.84rem;\n            text-align: center;\n            line-height: 1.5;\n            margin: 0.35rem 0 0.65rem;\n        }\n        .entry-dialog-image {\n            display: block;\n            width: 100%;\n            max-height: min(64vh, 620px);\n            object-fit: contain;\n        }\n        .entry-welcome-copy {\n            color: #344054;\n            font-size: 0.92rem;\n            line-height: 1.58;\n            margin: 0.05rem 0 0.8rem;\n        }\n        .entry-welcome-copy p {\n            margin: 0 0 0.36rem;\n        }\n        .entry-welcome-copy p:first-child {\n            color: #101828;\n            font-size: 1.18rem;\n            font-weight: 800;\n        }\n        .entry-ps {\n            color: #667085;\n            font-size: 0.82rem;\n            line-height: 1.55;\n            margin-top: 0.6rem !important;\n        }\n        </style>\n        '

MOTION_CSS = """
        <style>
        @keyframes aiFadeUp {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes aiSoftPulse {
            0%, 100% { box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04); }
            50% { box-shadow: 0 10px 28px rgba(15, 118, 110, 0.12); }
        }
        @keyframes aiRing {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        @keyframes aiProgress {
            0% { transform: translateX(-70%); }
            100% { transform: translateX(160%); }
        }
        @keyframes aiDash {
            from { background-position: 0 0; }
            to { background-position: 34px 0; }
        }
        @keyframes aiStepGlow {
            0%, 100% {
                background: #ffffff;
                border-color: #d7e5e1;
                color: #667085;
            }
            42% {
                background: #ccfbf1;
                border-color: #5eead4;
                color: #134e4a;
            }
        }
        @keyframes aiTinyScan {
            0% { transform: translateX(-110%); opacity: 0; }
            20% { opacity: 1; }
            80% { opacity: 1; }
            100% { transform: translateX(110%); opacity: 0; }
        }
        .hero-band,
        .decision-hero,
        .task-panel,
        .report-box,
        .roadmap-overview,
        .roadmap-card,
        .stage-card,
        .portfolio-guide,
        .document-preview-note {
            animation: aiFadeUp 420ms ease both;
        }
        .mode-tile,
        .roadmap-card,
        .stage-card,
        div.stButton > button {
            transition: transform 160ms ease, border-color 160ms ease, background 160ms ease, box-shadow 160ms ease;
        }
        .mode-tile:hover,
        .roadmap-card:hover,
        .stage-card:hover {
            transform: translateY(-2px);
            border-color: #99d6cf;
            box-shadow: 0 9px 24px rgba(16, 24, 40, 0.08);
        }
        .mode-tile-active {
            position: relative;
            overflow: hidden;
            animation: aiSoftPulse 2.8s ease-in-out infinite;
        }
        .mode-tile-active::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 4px;
            background: linear-gradient(180deg, #0f766e, #38bdf8);
        }
        div.stButton > button:hover:not(:disabled) {
            transform: translateY(-1px);
            box-shadow: 0 8px 18px rgba(16, 24, 40, 0.08);
        }
        div.stButton > button[kind="primary"] {
            background: #0f766e;
            color: #ffffff;
            border-color: #0f766e;
            position: relative;
            overflow: hidden;
        }
        div.stButton > button[kind="primary"]:hover:not(:disabled) {
            background: #115e59;
            color: #ffffff;
            border-color: #115e59;
        }
        div.stButton > button[kind="primary"]:disabled {
            background: #d0d5dd;
            color: #667085;
            border-color: #d0d5dd;
        }
        div.stButton > button[kind="primary"]::after {
            content: "";
            position: absolute;
            inset: auto 12px 6px 12px;
            height: 2px;
            border-radius: 999px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.82), transparent);
            transform: translateX(-120%);
            transition: transform 320ms ease;
        }
        div.stButton > button[kind="primary"]:hover::after {
            transform: translateX(120%);
        }
        .roadmap-line-active {
            background: repeating-linear-gradient(90deg, #5eead4 0 14px, #38bdf8 14px 22px);
            background-size: 34px 1px;
            animation: aiDash 1.2s linear infinite;
        }
        .processing-panel {
            border: 1px solid #a7f3d0;
            border-radius: 8px;
            background: linear-gradient(135deg, #f0fdfa 0%, #ffffff 56%, #eff6ff 100%);
            padding: 0.85rem 0.95rem;
            margin: 0.75rem 0 1rem;
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 0.8rem;
            align-items: center;
            overflow: hidden;
            position: relative;
            animation: aiFadeUp 240ms ease both;
        }
        .processing-panel::after {
            content: "";
            position: absolute;
            left: 0;
            right: 0;
            bottom: 0;
            height: 3px;
            background: linear-gradient(90deg, transparent, #0f766e, #38bdf8, transparent);
            animation: aiProgress 1.35s ease-in-out infinite;
        }
        .processing-ring {
            width: 2.15rem;
            height: 2.15rem;
            border-radius: 999px;
            border: 3px solid #ccfbf1;
            border-top-color: #0f766e;
            border-right-color: #38bdf8;
            animation: aiRing 900ms linear infinite;
        }
        .processing-title {
            color: #134e4a;
            font-weight: 760;
            font-size: 0.96rem;
            margin-bottom: 0.12rem;
        }
        .processing-copy {
            color: #475467;
            font-size: 0.88rem;
            line-height: 1.55;
        }
        .processing-steps {
            display: flex;
            flex-wrap: wrap;
            gap: 0.38rem;
            margin-top: 0.52rem;
        }
        .processing-step {
            position: relative;
            overflow: hidden;
            border: 1px solid #d7e5e1;
            border-radius: 999px;
            background: #ffffff;
            color: #667085;
            font-size: 0.76rem;
            font-weight: 700;
            line-height: 1.2;
            padding: 0.26rem 0.55rem;
            animation: aiStepGlow 2.4s ease-in-out infinite;
        }
        .processing-step::after {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.82), transparent);
            animation: aiTinyScan 2.4s ease-in-out infinite;
        }
        .processing-step-2,
        .processing-step-2::after {
            animation-delay: 0.35s;
        }
        .processing-step-3,
        .processing-step-3::after {
            animation-delay: 0.7s;
        }
        @media (prefers-reduced-motion: reduce) {
            *,
            *::before,
            *::after {
                animation-duration: 1ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 1ms !important;
            }
        }
        </style>
        """


def apply_main_styles() -> None:
    st.markdown(MAIN_CSS, unsafe_allow_html=True)
    st.markdown(MOTION_CSS, unsafe_allow_html=True)


def apply_entry_styles() -> None:
    st.markdown(ENTRY_CSS, unsafe_allow_html=True)
    st.markdown(MOTION_CSS, unsafe_allow_html=True)
