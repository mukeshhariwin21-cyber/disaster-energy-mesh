"""
charts.py
---------
Builds all Plotly figures from the simulator's history. Pure functions:
data in, figure out. No simulation logic lives here.
"""

import plotly.graph_objects as go
import pandas as pd


def history_to_dataframe(history) -> pd.DataFrame:
    rows = []
    for tick in history:
        row = {
            "time_label": tick.time_label,
            "hour": tick.hour_of_day,
            "total_generation_w": tick.total_generation_w,
            "total_available_power_w": tick.total_available_power_w,
            "total_load_demand_w": tick.total_load_demand_w,
            "total_allocated_w": tick.total_allocated_w,
            "surplus_deficit_w": tick.surplus_deficit_w,
        }
        for node in tick.nodes:
            row[f"{node['node_id']}_solar_w"] = node["solar_generation_w"]
            row[f"{node['node_id']}_soc"] = node["soc"]
        rows.append(row)
    return pd.DataFrame(rows)


def solar_generation_chart(df: pd.DataFrame, node_ids):
    fig = go.Figure()
    for node_id in node_ids:
        col = f"{node_id}_solar_w"
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df["time_label"], y=df[col], mode="lines", name=node_id))
    fig.update_layout(
        title="Solar Generation vs Time",
        xaxis_title="Simulated Time",
        yaxis_title="Generation (W)",
        legend_title="Node",
        height=320,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def battery_soc_chart(df: pd.DataFrame, node_ids):
    fig = go.Figure()
    for node_id in node_ids:
        col = f"{node_id}_soc"
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df["time_label"], y=df[col], mode="lines", name=node_id))
    fig.update_layout(
        title="Battery SOC vs Time",
        xaxis_title="Simulated Time",
        yaxis_title="State of Charge (%)",
        yaxis_range=[0, 100],
        legend_title="Node",
        height=320,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def load_demand_chart(df: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["time_label"], y=df["total_load_demand_w"], mode="lines",
                              name="Total Load Demand", line=dict(color="#e74c3c")))
    fig.add_trace(go.Scatter(x=df["time_label"], y=df["total_allocated_w"], mode="lines",
                              name="Load Actually Supplied", line=dict(color="#27ae60", dash="dot")))
    fig.update_layout(
        title="Load Demand vs Time",
        xaxis_title="Simulated Time",
        yaxis_title="Power (W)",
        height=320,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def available_vs_demand_chart(df: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["time_label"], y=df["total_available_power_w"], mode="lines",
                              name="Total Available Power", line=dict(color="#2980b9"),
                              fill="tozeroy"))
    fig.add_trace(go.Scatter(x=df["time_label"], y=df["total_load_demand_w"], mode="lines",
                              name="Total Load Demand", line=dict(color="#e67e22", dash="dash")))
    fig.update_layout(
        title="Total Available Power vs Demand",
        xaxis_title="Simulated Time",
        yaxis_title="Power (W)",
        height=320,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig
def power_balance_chart(df: pd.DataFrame):
    fig = go.Figure()

    if "total_generation_w" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["time_label"],
                y=df["total_generation_w"],
                mode="lines",
                name="Generation",
            )
        )

    if "total_load_demand_w" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["time_label"],
                y=df["total_load_demand_w"],
                mode="lines",
                name="Demand",
            )
        )

    if "total_allocated_w" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["time_label"],
                y=df["total_allocated_w"],
                mode="lines",
                name="Allocated",
            )
        )

    fig.update_layout(
        title="Power Generation vs Demand",
        xaxis_title="Time",
        yaxis_title="Power (W)",
        hovermode="x unified",
    )

    return fig


    fig.update_layout(
        title="Battery State of Charge",
        xaxis_title="Time",
        yaxis_title="SOC",
        yaxis=dict(range=[0, 1]),
        hovermode="x unified",
    )

    return fig