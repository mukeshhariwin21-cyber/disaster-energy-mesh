"""
dashboard/components.py
-----------------------
Clean and reusable Streamlit UI components for
the Disaster Energy Mesh dashboard.

This file only displays data.
It does not modify simulator logic.
"""

import streamlit as st


# ============================================================
# HEADER
# ============================================================

def render_header():
    st.title("⚡ DISASTER ENERGY MESH")
    st.caption(
        "Self-Healing · AI-Assisted · Distributed Emergency Microgrid"
    )


# ============================================================
# NODE CARD
# ============================================================

def render_node_card(node: dict):

    node_id = node.get("node_id", "Unknown")
    status = node.get("status", "UNKNOWN")
    health = node.get("health", "UNKNOWN")

    solar = float(node.get("solar_generation_w", 0))
    net_power = float(node.get("net_power_w", 0))
    voltage = float(node.get("voltage_v", 0))
    current = float(node.get("current_a", 0))
    temperature = float(node.get("temperature_c", 0))
    soc = float(node.get("soc", 0))
    comm_status = node.get("comm_status", "UNKNOWN")

    with st.container(border=True):

        st.subheader(f"🔋 {node_id}")

        # Status
        if status == "HEALTHY":
            st.success("🟢 HEALTHY")
        elif status == "FAILED":
            st.error("🔴 FAILED")
        else:
            st.warning(f"🟠 {status}")

        # Health
        if health == "OPTIMAL":
            st.success(f"Health: {health}")
        elif health in ("DEGRADED", "LOW BATTERY"):
            st.warning(f"Health: {health}")
        elif health == "FAILED":
            st.error(f"Health: {health}")
        else:
            st.info(f"Health: {health}")

        # Battery
        st.progress(
            min(max(soc / 100.0, 0.0), 1.0),
            text=f"🔋 Battery SOC: {soc:.1f}%"
        )

        # Power
        c1, c2 = st.columns(2)

        c1.metric(
            "☀️ Solar",
            f"{solar:.1f} W"
        )

        c2.metric(
            "⚡ Net Power",
            f"{net_power:.1f} W"
        )

        # Electrical
        c3, c4 = st.columns(2)

        c3.metric(
            "Voltage",
            f"{voltage:.2f} V"
        )

        c4.metric(
            "Current",
            f"{current:.2f} A"
        )

        # Temperature
        c5, c6 = st.columns(2)

        c5.metric(
            "🌡️ Temperature",
            f"{temperature:.1f} °C"
        )

        if comm_status == "CONNECTED":
            c6.success("🟢 Connected")
        else:
            c6.error("🔴 Disconnected")


# ============================================================
# ENERGY SUMMARY
# ============================================================

def render_energy_summary(tick):

    st.subheader("⚡ Energy Overview")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "☀️ Generation",
        f"{tick.total_generation_w:.1f} W"
    )

    c2.metric(
        "🔋 Available Power",
        f"{tick.total_available_power_w:.1f} W"
    )

    c3.metric(
        "🏠 Load Demand",
        f"{tick.total_load_demand_w:.1f} W"
    )

    balance = tick.surplus_deficit_w

    c4.metric(
        "Power Balance",
        f"{balance:+.1f} W"
    )

    if tick.network_status == "NORMAL":
        st.success("🟢 Network Status: NORMAL")

    elif tick.network_status == "EMERGENCY":
        st.warning("🟠 Network Status: EMERGENCY")

    elif tick.network_status == "CRITICAL":
        st.error("🔴 Network Status: CRITICAL")

    else:
        st.info(
            f"Network Status: {tick.network_status}"
        )


# ============================================================
# LOAD PRIORITY
# ============================================================

def render_load_priority(load_status: dict):

    st.subheader("🔌 Load Priority")

    c1, c2, c3 = st.columns(3)

    # P1
    if load_status.get("Critical", False):
        c1.success("🟢 P1 · CRITICAL\n\nON")
    else:
        c1.error("🔴 P1 · CRITICAL\n\nOFF")

    # P2
    if load_status.get("Essential", False):
        c2.success("🟢 P2 · ESSENTIAL\n\nON")
    else:
        c2.error("🔴 P2 · ESSENTIAL\n\nOFF")

    # P3
    if load_status.get("Non-critical", False):
        c3.success("🟢 P3 · NON-CRITICAL\n\nON")
    else:
        c3.error("🔴 P3 · NON-CRITICAL\n\nOFF")


# ============================================================
# NETWORK TOPOLOGY
# ============================================================

def render_topology(nodes: list):

    st.subheader("🌐 Network Topology")

    if not nodes:
        st.info("No nodes available.")
        return

    cols = st.columns(len(nodes))

    for index, node in enumerate(nodes):

        node_id = node.get("node_id", "Node")
        status = node.get("status", "UNKNOWN")

        with cols[index]:

            st.markdown(f"### {node_id}")

            if status == "HEALTHY":
                st.success("🟢 CONNECTED")

            elif status == "FAILED":
                st.error("🔴 ISOLATED")

            else:
                st.warning(f"🟠 {status}")

    st.caption(
        "🟢 Healthy & connected · 🔴 Failed / isolated"
    )


# ============================================================
# SELF-HEALING EVENT LOG
# ============================================================

def render_event_log(events: list):

    st.subheader("🚨 Self-Healing Event Log")

    if not events:
        st.info(
            "No events yet. "
            "Use FAIL NODE from the sidebar to test self-healing."
        )
        return

    recent_events = list(
        reversed(events[-15:])
    )

    for event in recent_events:

        text = str(event)
        upper = text.upper()

        # Failure
        if (
            "FAIL" in upper
            or "FAULT" in upper
            or "ISOLAT" in upper
            or "COMMUNICATION LOST" in upper
        ):
            st.error(f"🔴 {text}")

        # Recovery
        elif (
            "RECOVER" in upper
            or "RECONNECT" in upper
            or "RESTOR" in upper
            or "COMMUNICATION RESTORED" in upper
        ):
            st.success(f"🟢 {text}")

        # Self-healing
        elif (
            "SELF-HEAL" in upper
            or "REDISTRIBUT" in upper
            or "RECALCULATED" in upper
            or "POWER REDISTRIBUTION" in upper
        ):
            st.warning(f"🟠 {text}")

        # Normal
        else:
            st.info(f"🔵 {text}")


# ============================================================
# AI ENERGY PREDICTION
# ============================================================

def render_ai_prediction(prediction):

    st.subheader("🤖 AI Energy Intelligence")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Current Demand",
        f"{prediction.current_demand_w:.1f} W"
    )

    c2.metric(
        "Predicted Demand",
        f"{prediction.predicted_demand_w:.1f} W"
    )

    c3.metric(
        "Predicted Solar",
        f"{prediction.predicted_solar_w:.1f} W"
    )

    c4.metric(
        "AI Confidence",
        f"{prediction.confidence * 100:.0f}%"
    )

    st.info(
        f"🤖 Recommendation: {prediction.recommendation}"
    )


# ============================================================
# LIVE ENERGY FLOW
# ============================================================

def render_energy_flow(tick):

    st.subheader("⚡ Live Energy Flow")

    generation = float(
        tick.total_generation_w
    )

    load = float(
        tick.total_allocated_w
    )

    balance = generation - load

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "☀️ Solar Generation",
        f"{generation:.1f} W"
    )

    c2.metric(
        "🏠 Load Supplied",
        f"{load:.1f} W"
    )

    if balance >= 0:

        c3.metric(
            "🟢 Energy Surplus",
            f"+{balance:.1f} W"
        )

    else:

        c3.metric(
            "🔴 Energy Deficit",
            f"{balance:.1f} W"
        )

    st.divider()

    flow1, flow2, flow3 = st.columns(3)

    flow1.metric(
        "☀️ SOLAR",
        f"{generation:.1f} W"
    )

    flow2.metric(
        "⚡ MESH BALANCE",
        f"{balance:+.1f} W"
    )

    flow3.metric(
        "🏠 LOADS",
        f"{load:.1f} W"
    )


# ============================================================
# SYSTEM HEALTH
# ============================================================

def render_system_health(nodes: list):

    st.subheader("🩺 System Health")

    if not nodes:
        st.warning("No nodes available.")
        return

    healthy = sum(
        1
        for node in nodes
        if node.get("status") == "HEALTHY"
    )

    failed = len(nodes) - healthy

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Total Nodes",
        len(nodes)
    )

    c2.metric(
        "🟢 Healthy",
        healthy
    )

    c3.metric(
        "🔴 Failed",
        failed
    )


# ============================================================
# SIMULATION STATUS
# ============================================================

def render_simulation_status(sim):

    st.subheader("⏱️ Simulation Status")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Simulation Time",
        sim._time_label()
    )

    c2.metric(
        "Speed",
        f"{sim.dt_hours} h/tick"
    )

    if sim.running:
        c3.success("🟢 RUNNING")
    else:
        c3.warning("⏸️ PAUSED")