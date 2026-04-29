from __future__ import annotations

import math
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
    return fmt_money_unit(value)


def fmt_pct(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value:.1%}"


def fmt_pct_points(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value:.1f}%"


def fmt_money_unit(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value / 10_000:.1f}万"


def _nice_step(value: float) -> float:
    if value <= 0:
        return 1.0
    exponent = math.floor(math.log10(value))
    fraction = value / (10**exponent)
    if fraction <= 1:
        nice_fraction = 1
    elif fraction <= 2:
        nice_fraction = 2
    elif fraction <= 5:
        nice_fraction = 5
    else:
        nice_fraction = 10
    return nice_fraction * (10**exponent)


def money_tick_values(values: pd.Series | list[float], tick_count: int = 5) -> list[float]:
    series = pd.Series(values, dtype="float64").dropna()
    if series.empty:
        return []

    minimum = float(series.min())
    maximum = float(series.max())
    if minimum == maximum:
        if minimum == 0:
            return [0.0]
        minimum = min(0.0, minimum)
        maximum = max(0.0, maximum)

    step = _nice_step((maximum - minimum) / max(tick_count - 1, 1))
    start = math.floor(minimum / step) * step
    end = math.ceil(maximum / step) * step
    ticks = []
    current = start
    while current <= end + step * 0.5:
        ticks.append(round(current, 6))
        current += step
    return ticks


def apply_money_axis(fig: go.Figure, values: pd.Series | list[float]) -> None:
    ticks = money_tick_values(values)
    if not ticks:
        return
    fig.update_yaxes(
        tickmode="array",
        tickvals=ticks,
        ticktext=[fmt_money_unit(value) for value in ticks],
        separatethousands=False,
    )


def build_monthly_pnl_chart(df: pd.DataFrame) -> go.Figure:
    plot_df = df[["月标签", "净入金", "交易盈亏", "权利金收支", "手续费", "净盈亏"]].copy()
    plot_df["手续费"] = -plot_df["手续费"]
    melted = plot_df.melt(
        id_vars="月标签",
        var_name="项目",
        value_name="金额",
    )
    melted["金额显示"] = melted["金额"].map(fmt_money_unit)

    fig = px.bar(
        melted,
        x="月标签",
        y="金额",
        color="项目",
        custom_data=["金额显示"],
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
    fig.update_traces(
        hovertemplate="交易月份=%{x}<br>金额=%{customdata[0]}<extra>%{fullData.name}</extra>"
    )
    apply_money_axis(fig, melted["金额"])
    return fig


def build_equity_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["月标签"],
            y=df["客户权益"],
            mode="lines+markers",
            name="客户权益",
            customdata=df["客户权益"].map(fmt_money_unit),
            hovertemplate="交易月份=%{x}<br>客户权益=%{customdata}<extra></extra>",
            line=dict(color="#1F77B4", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["月标签"],
            y=df["累计净入金"],
            mode="lines+markers",
            name="累计净入金",
            customdata=df["累计净入金"].map(fmt_money_unit),
            hovertemplate="交易月份=%{x}<br>累计净入金=%{customdata}<extra></extra>",
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
    apply_money_axis(fig, pd.concat([df["客户权益"], df["累计净入金"]]))
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
            customdata=df["风险度"].map(fmt_pct_points),
            hovertemplate="交易月份=%{x}<br>风险度=%{customdata}<extra></extra>",
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
    fig.update_yaxes(ticksuffix="%", tickformat=".1f")
    return fig


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    csv_files = find_csv_files(base_dir)
    if not csv_files:
        st.error("当前目录下没有找到 futures_account_status_*.csv 文件。")
        st.stop()

    st.title("期货账户盈亏分析报表")
    st.caption("基于月度账户资金状况表，分析净入金、交易盈亏、手续费、权益曲线和风险度。")

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
    c6.metric("累计权利金收支", fmt_money(total_premium))
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
        st.plotly_chart(build_monthly_pnl_chart(filtered), width="stretch")
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

    tabs = st.tabs(["权益曲线", "风险度", "月度明细", "原始长表"])

    with tabs[0]:
        st.plotly_chart(build_equity_chart(filtered), width="stretch")

    with tabs[1]:
        st.plotly_chart(build_risk_chart(filtered), width="stretch")

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
        ]
        money_cols = [
            "上月结存",
            "净入金",
            "交易盈亏",
            "权利金收支",
            "手续费",
            "净盈亏",
            "客户权益",
            "可用资金",
            "保证金占用",
        ]
        detail_display = filtered[detail_cols].copy()
        for col in money_cols:
            detail_display[col] = detail_display[col].map(fmt_money_unit)
        detail_display["风险度"] = detail_display["风险度"].map(fmt_pct_points)
        st.dataframe(
            detail_display,
            width="stretch",
            hide_index=True,
            column_config={
                "月标签": st.column_config.TextColumn("交易月份"),
                "风险度": st.column_config.TextColumn("风险度"),
                "上月结存": st.column_config.TextColumn("上月结存"),
                "净入金": st.column_config.TextColumn("净入金"),
                "交易盈亏": st.column_config.TextColumn("交易盈亏"),
                "权利金收支": st.column_config.TextColumn("权利金收支"),
                "手续费": st.column_config.TextColumn("手续费"),
                "净盈亏": st.column_config.TextColumn("净盈亏"),
                "客户权益": st.column_config.TextColumn("客户权益"),
                "可用资金": st.column_config.TextColumn("可用资金"),
                "保证金占用": st.column_config.TextColumn("保证金占用"),
            },
        )

    with tabs[3]:
        st.dataframe(raw_df, width="stretch", hide_index=True)


if __name__ == "__main__":
    main()
