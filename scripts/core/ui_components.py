"""
UI Components - Reusable styled components for the dashboard using Tailwind CSS.
"""

from typing import Any

import streamlit as st


def load_css() -> None:
    """Load minimal custom CSS if needed."""
    st.markdown(
        """
        <style>
            .stApp {
                background-color: #f8fafc;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero_banner(title: str, subtitle: str = "") -> None:
    """Create a hero banner with gradient background."""
    subtitle_html = (
        f'<p class="text-lg md:text-xl text-white/90 font-light">{subtitle}</p>' if subtitle else ""
    )
    html = f"""
<div class="bg-gradient-to-r from-indigo-500 via-blue-500 to-teal-400 p-8 rounded-2xl shadow-xl mb-8 text-center animate-fade-in-down">
    <h1 class="text-4xl md:text-5xl font-bold text-white mb-2 drop-shadow-md font-sans">{title}</h1>
    {subtitle_html}
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


def metric_card(
    label: str,
    value: str,
    delta: str | None = None,
    color: str = "indigo",
    icon: str | None = None,
    help_text: str | None = None,
) -> None:
    """Create a styled metric card using Tailwind."""
    color_map = {
        "purple": "border-indigo-500 text-indigo-600",
        "blue": "border-blue-500 text-blue-600",
        "teal": "border-teal-500 text-teal-600",
        "green": "border-emerald-500 text-emerald-600",
        "orange": "border-orange-500 text-orange-600",
        "red": "border-red-500 text-red-600",
    }

    border_class = color_map.get(color, "border-indigo-500 text-indigo-600")
    border_color = border_class.split(" ")[0]

    delta_html = ""
    if delta:
        is_positive = not delta.startswith("-")
        delta_color = "text-emerald-500" if is_positive else "text-red-500"
        arrow = "↑" if is_positive else "↓"
        display_delta = delta if any(c in delta for c in "↑↓") else f"{arrow} {delta}"
        delta_html = f'<span class="text-sm font-medium {delta_color} ml-2">{display_delta}</span>'

    icon_html = f'<div class="text-2xl mr-3 opacity-80">{icon}</div>' if icon else ""
    help_html = f'<div class="text-xs text-slate-400 mt-2">{help_text}</div>' if help_text else ""

    html = f"""
<div class="bg-white hover:shadow-lg transition-transform hover:-translate-y-1 p-6 rounded-xl shadow-md border-l-4 {border_color} h-full">
    <div class="flex items-center mb-1">
        {icon_html}
        <div class="text-sm font-medium text-slate-500 uppercase tracking-wider truncate" title="{label}">{label}</div>
    </div>
    <div class="flex items-baseline">
        <div class="text-2xl font-bold text-slate-800 truncate" title="{value}">{value}</div>
        {delta_html}
    </div>
    {help_html}
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


def section_header(title: str, icon: str = "") -> None:
    """Create a styled section header."""
    # icon_html = f'<span class="text-2xl mr-3 text-indigo-600">{icon}</span>' if icon else ''
    html = f"""
<div class="flex items-center mb-6 pb-2 border-b-2 border-slate-100 mt-8">
    <h2 class="text-2xl font-bold text-slate-800 font-sans">{title}</h2>
</div>
"""
    # {icon_html}
    st.markdown(html, unsafe_allow_html=True)


def info_box(content: str, box_type: str = "info") -> None:
    """Create an info/alert box using native Streamlit components."""
    if box_type == "info":
        st.info(content)
    elif box_type == "success":
        st.success(content)
    elif box_type == "warning":
        st.warning(content)
    elif box_type == "error":
        st.error(content)
    else:
        st.info(content)


def premium_card(content: str) -> None:
    """Create a premium card container."""
    html = f"""
<div class="bg-white p-6 rounded-xl shadow-md border border-slate-100 hover:shadow-xl transition-shadow duration-300">
    {content}
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


def navigation_card(title: str, description: str, icon: str = "", link: str | None = None) -> None:
    """Create a navigation card."""
    html = f"""
<div class="bg-white p-8 rounded-2xl shadow-md border-2 border-transparent hover:border-indigo-500 hover:-translate-y-1 transition-all duration-300 cursor-pointer h-full text-center group">
    <h3 class="text-xl font-bold text-slate-800 mb-2">{title}</h3>
    <p class="text-slate-600 leading-relaxed">{description}</p>
</div>
"""
    # <div class="text-5xl mb-4 transform group-hover:scale-110 transition-transform duration-300">{icon}</div>
    st.markdown(html, unsafe_allow_html=True)


def badge(text: str, badge_type: str = "primary") -> str:
    """Create a styled badge (returns HTML string)."""
    styles = {
        "primary": "bg-indigo-100 text-indigo-700",
        "success": "bg-emerald-100 text-emerald-700",
        "warning": "bg-amber-100 text-amber-700",
        "info": "bg-blue-100 text-blue-700",
        "neutral": "bg-slate-100 text-slate-700",
    }
    style = styles.get(badge_type, styles["primary"])
    return f'<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {style}">{text}</span>'


def divider() -> None:
    """Create a styled divider."""
    st.markdown('<div class="h-px bg-slate-200 my-8"></div>', unsafe_allow_html=True)


def display_metrics_row(metrics: list[dict[str, Any]], cols: int = 4) -> None:
    """Display a row of metrics using the custom metric_card."""
    columns = st.columns(cols)
    colors = ["purple", "blue", "teal", "green", "orange", "red"]

    for i, metric in enumerate(metrics):
        with columns[i % cols]:
            metric_card(
                label=metric.get("label", ""),
                value=metric.get("value", ""),
                delta=metric.get("delta"),
                help_text=metric.get("help"),
                color=metrics.get("color", colors[i % len(colors)]),
                # icon=metric.get('icon')
            )


def loading_message(text: str = "Loading...") -> None:
    """Display a custom loading message with spinner."""
    html = f"""
<div class="flex flex-col items-center justify-center p-8">
    <div class="animate-spin rounded-full h-10 w-10 border-4 border-indigo-200 border-t-indigo-600"></div>
    <p class="mt-4 text-slate-500 font-medium">{text}</p>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


def page_header(title: str, description: str = "", show_divider: bool = True) -> None:
    """Create a consistent page header."""
    description_html = f'<p class="text-lg text-slate-600">{description}</p>' if description else ""
    html = f"""
<div class="mb-6">
    <h1 class="text-3xl md:text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-blue-500 mb-2">{title}</h1>
    {description_html}
</div>
"""
    st.markdown(html, unsafe_allow_html=True)
    if show_divider:
        divider()


def feature_highlight(features: list[dict[str, str]], title: str = "Platform Capabilities") -> None:
    section_header(title)
    cols = st.columns(len(features))
    for i, feature in enumerate(features):
        with cols[i]:
            html = f"""
<div class="bg-white p-6 rounded-xl shadow border border-slate-100 text-center h-full hover:shadow-md transition-shadow">
    <h4 class="text-lg font-bold text-slate-800 mb-2">{feature.get("title", "")}</h4>
    <p class="text-sm text-slate-500">{feature.get("description", "")}</p>
</div>
"""
            # <div class="text-4xl mb-3">{feature.get('icon', '')}</div>
            st.markdown(html, unsafe_allow_html=True)


def stats_summary(stats: list[dict[str, Any]], title: str = "📊 Quick Stats") -> None:
    st.markdown(f"### {title}")
    display_metrics_row(stats)


def custom_warning(message: str, icon: str = "⚠️") -> None:
    info_box(f"<strong>{icon} Warning:</strong> {message}", "warning")


def custom_success(message: str, icon: str = "✅") -> None:
    info_box(f"<strong>{icon} Success:</strong> {message}", "success")
