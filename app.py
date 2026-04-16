from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="期货账户盈亏分析报表",
    page_icon="📈",
    layout="wide",
)


DEFAULT_METRICS = [
    "上月结存",
    "客户权益",
    "当月存取合计",
    "实有货币资金",
    "当月盈亏",
    "当月总权利金",
    "当月手续费",
    "当月结存",
    "保证金占用",
    "可用资金",
    "风险度",
    "追加保证金",
]


def parse_numeric(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "--":
        return None
    text = text.replace(",", "").replace("%", "").strip()
    try:
        return float(text)
    except ValueError:
        return None


def find_csv_files(base_dir: Path) -> list[Path]:
    return sorted(base_dir.glob("futures_account_status_*.csv"))


@st.cache_data
def load_report(csv_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(csv_path)

    # Clean up column names and string data
    raw.columns = [c.strip() for c in raw.columns]
    # Remove all whitespace from metric names to ensure matching with DEFAULT_METRICS
    raw["指标"] = raw["指标"].astype(str).str.replace(r"\s+", "", regex=True)

    raw["数值"] = raw["值"].map(parse_numeric)

    wide = (
        raw.pivot_table(
            index="交易月份",
            columns="指标",
            values="数值",
            aggfunc="first",
        )
        .reset_index()
        .sort_values("交易月份")
    )

    # Ensure all columns exist, removing spaces from metric names here too just in case
    cleaned_metrics = [m.replace(" ", "").replace("\t", "") for m in DEFAULT_METRICS]
    for metric in cleaned_metrics:
        if metric not in wide.columns:
            wide[metric] = pd.NA

    wide["月份"] = pd.to_datetime(wide["交易月份"] + "-01")
    wide["净入金"] = wide["当月存取合计"].fillna(0.0)
    wide["交易盈亏"] = wide["当月盈亏"].fillna(0.0)
    wide["权利金收支"] = wide["当月总权利金"].fillna(0.0)
    wide["手续费"] = wide["当月手续费"].fillna(0.0)
    wide["净盈亏"] = (
        wide["客户权益"].fillna(0.0)
        - wide["上月结存"].fillna(0.0)
        - wide["净入金"]
    )
    wide["累计净入金"] = wide["净入金"].cumsum()
    wide["累计交易盈亏"] = wide["交易盈亏"].cumsum()
    wide["累计权利金收支"] = wide["权利金收支"].cumsum()
    wide["累计手续费"] = wide["手续费"].cumsum()
    wide["累计净盈亏"] = wide["净盈亏"].cumsum()
    wide["权益峰值"] = wide["客户权益"].cummax()
    wide["回撤比例"] = wide["客户权益"] / wide["权益峰值"] - 1.0
    wide["回撤百分比"] = wide["回撤比例"] * 100
    wide["可用资金占比"] = wide["可用资金"] / wide["客户权益"]
    wide["资金核对差异"] = (
        wide["客户权益"].fillna(0.0)
        - (
            wide["上月结存"].fillna(0.0)
            + wide["净入金"]
            + wide["交易盈亏"]
            + wide["权利金收支"]
            - wide["手续费"]
        )
    )
    wide["月标签"] = wide["月份"].dt.strftime("%Y-%m")

    return raw, wide


def fmt_money(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value:,.2f}"


def fmt_pct(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value:.2%}"


def build_monthly_pnl_chart(df: pd.DataFrame) -> go.Figure:
    plot_df = df[["月标签", "净入金", "交易盈亏", "权利金收支", "手续费", "净盈亏"]].copy()
    plot_df["手续费"] = -plot_df["手续费"]
    melted = plot_df.melt(
        id_vars="月标签",
        var_name="项目",
        value_name="金额",
    )

    fig = px.bar(
        melted,
        x="月标签",
        y="金额",
        color="项目",
        barmode="group",
        color_discrete_map={
            "净入金": "#4C78A8",
            "交易盈亏": "#59A14F",
            "权利金收支": "#B07AA1",
            "手续费": "#E15759",
            "净盈亏": "#F28E2B",
        },
    )
    fig.update_layout(
        title="月度资金变动与盈亏拆解",
        legend_title_text="",
        xaxis_title="交易月份",
        yaxis_title="金额",
        hovermode="x unified",
    )
    return fig


def build_equity_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["月标签"],
            y=df["客户权益"],
            mode="lines+markers",
            name="客户权益",
            line=dict(color="#1F77B4", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["月标签"],
            y=df["累计净入金"],
            mode="lines+markers",
            name="累计净入金",
            line=dict(color="#7F7F7F", width=2, dash="dash"),
        )
    )
    fig.update_layout(
        title="账户权益与累计净入金",
        legend_title_text="",
        xaxis_title="交易月份",
        yaxis_title="金额",
        hovermode="x unified",
    )
    return fig


def build_drawdown_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["月标签"],
            y=df["回撤比例"] * 100,
            name="回撤",
            marker_color="#E15759",
        )
    )
    fig.update_layout(
        title="权益回撤",
        legend_title_text="",
        xaxis_title="交易月份",
        yaxis_title="回撤 (%)",
        hovermode="x unified",
    )
    return fig


def build_risk_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    colors = ["#59A14F" if x < 80 else "#F28E2B" if x < 90 else "#E15759" for x in df["风险度"].fillna(0.0)]
    fig.add_trace(
        go.Bar(
            x=df["月标签"],
            y=df["风险度"],
            marker_color=colors,
            name="风险度",
        )
    )
    fig.add_hline(y=80, line_dash="dash", line_color="#F28E2B")
    fig.add_hline(y=90, line_dash="dash", line_color="#E15759")
    fig.update_layout(
        title="月度风险度",
        legend_title_text="",
        xaxis_title="交易月份",
        yaxis_title="风险度 (%)",
        hovermode="x unified",
    )
    return fig


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    csv_files = find_csv_files(base_dir)
    if not csv_files:
        st.error("当前目录下没有找到 futures_account_status_*.csv 文件。")
        st.stop()

    st.title("期货账户盈亏分析报表")
    st.caption("基于月度账户资金状况表，分析净入金、交易盈亏、手续费、权益曲线、回撤和风险度。")

    with st.sidebar:
        selected_file = st.selectbox(
            "选择数据文件",
            options=csv_files,
            format_func=lambda path: path.name,
        )

    raw_df, monthly_df = load_report(str(selected_file))
    month_options = monthly_df["月标签"].tolist()
    month_range = st.select_slider(
        "分析区间",
        options=month_options,
        value=(month_options[0], month_options[-1]),
    )

    filtered = monthly_df[
        monthly_df["月标签"].between(month_range[0], month_range[1])
    ].copy()
    if filtered.empty:
        st.warning("当前筛选区间没有数据。")
        st.stop()

    latest = filtered.iloc[-1]
    total_net_deposit = filtered["净入金"].sum()
    total_gross_pnl = filtered["交易盈亏"].sum()
    total_premium = filtered["权利金收支"].sum()
    total_fees = filtered["手续费"].sum()
    total_net_pnl = filtered["净盈亏"].sum()
    max_drawdown = filtered["回撤比例"].min()
    profitable_months = int((filtered["净盈亏"] > 0).sum())
    loss_months = int((filtered["净盈亏"] < 0).sum())
    avg_risk = filtered["风险度"].mean() / 100
    max_risk = filtered["风险度"].max() / 100
    max_reconcile_gap = filtered["资金核对差异"].abs().max()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("最新客户权益", fmt_money(latest["客户权益"]))
    c2.metric("累计净入金", fmt_money(total_net_deposit))
    c3.metric("累计交易盈亏", fmt_money(total_gross_pnl))
    c4.metric("累计净盈亏", fmt_money(total_net_pnl))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("累计手续费", fmt_money(total_fees))
    c6.metric("最大回撤", fmt_pct(max_drawdown))
    c7.metric("平均风险度", fmt_pct(avg_risk))
    c8.metric("最高风险度", fmt_pct(max_risk))

    st.info(
        f"分析区间内共有 {len(filtered)} 个月；盈利月份 {profitable_months} 个，亏损月份 {loss_months} 个。"
    )

    if pd.notna(max_reconcile_gap) and max_reconcile_gap > 0.01:
        st.warning(
            f"发现最大资金核对差异为 {fmt_money(max_reconcile_gap)}，请确认原始报表口径。"
        )

    left, right = st.columns((3, 2))
    with left:
        st.plotly_chart(build_monthly_pnl_chart(filtered), use_container_width=True)
    with right:
        best_month = filtered.loc[filtered["净盈亏"].idxmax()]
        worst_month = filtered.loc[filtered["净盈亏"].idxmin()]
        st.subheader("区间摘要")
        st.write(
            f"净盈亏口径按 `客户权益 - 上月结存 - 当月存取合计` 计算，已自动反映手续费和权利金收支。"
        )
        st.write(f"区间内权利金收支合计 `{fmt_money(total_premium)}`。")
        st.write(
            f"表现最好月份：`{best_month['月标签']}`，净盈亏 `{fmt_money(best_month['净盈亏'])}`。"
        )
        st.write(
            f"表现最差月份：`{worst_month['月标签']}`，净盈亏 `{fmt_money(worst_month['净盈亏'])}`。"
        )
        st.write(
            f"区间结束时客户权益 `{fmt_money(latest['客户权益'])}`，可用资金 `{fmt_money(latest['可用资金'])}`。"
        )
        st.write(
            f"当前保证金占用 `{fmt_money(latest['保证金占用'])}`，风险度 `{fmt_pct(latest['风险度'] / 100)}`。"
        )

    tabs = st.tabs(["权益与回撤", "风险度", "月度明细", "原始长表"])

    with tabs[0]:
        st.plotly_chart(build_equity_chart(filtered), use_container_width=True)
        st.plotly_chart(build_drawdown_chart(filtered), use_container_width=True)

    with tabs[1]:
        st.plotly_chart(build_risk_chart(filtered), use_container_width=True)

    with tabs[2]:
        detail_cols = [
            "月标签",
            "上月结存",
            "净入金",
            "交易盈亏",
            "权利金收支",
            "手续费",
            "净盈亏",
            "客户权益",
            "可用资金",
            "保证金占用",
            "风险度",
            "回撤百分比",
        ]
        st.dataframe(
            filtered[detail_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "月标签": st.column_config.TextColumn("交易月份"),
                "风险度": st.column_config.NumberColumn("风险度 (%)", format="%.2f"),
                "回撤比例": st.column_config.NumberColumn("回撤", format="%.2f%%"),
                "上月结存": st.column_config.NumberColumn("上月结存", format="%.2f"),
                "净入金": st.column_config.NumberColumn("净入金", format="%.2f"),
                "交易盈亏": st.column_config.NumberColumn("交易盈亏", format="%.2f"),
                "权利金收支": st.column_config.NumberColumn("权利金收支", format="%.2f"),
                "手续费": st.column_config.NumberColumn("手续费", format="%.2f"),
                "净盈亏": st.column_config.NumberColumn("净盈亏", format="%.2f"),
                "客户权益": st.column_config.NumberColumn("客户权益", format="%.2f"),
                "可用资金": st.column_config.NumberColumn("可用资金", format="%.2f"),
                "保证金占用": st.column_config.NumberColumn("保证金占用", format="%.2f"),
                "回撤百分比": st.column_config.NumberColumn("回撤 (%)", format="%.2f"),
            },
        )

    with tabs[3]:
        st.dataframe(raw_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
