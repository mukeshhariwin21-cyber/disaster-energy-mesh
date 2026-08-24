"""
Disaster Energy Mesh
--------------------
Streamlit dashboard entry point.
"""

import time
import streamlit as st

from ai.predictor import run_prediction
from simulation.simulator import Simulator
from dashboard import charts, components


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Disaster Energy Mesh",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# SIMULATOR INITIALIZATION
# ============================================================

if "simulator" not in st.session_state:

    st.session_state.simulator = Simulator()

    st.session_state.last_tick = (
        st.session_state.simulator.step()
    )

if "manual_solar_w" not in st.session_state:

    st.session_state.manual_solar_w = 500.0

if "manual_load_w" not in st.session_state:

    st.session_state.manual_load_w = 300.0

if "manual_battery_w" not in st.session_state:

    st.session_state.manual_battery_w = 200.0


sim: Simulator = st.session_state.simulator


# ============================================================
# HEADER
# ============================================================

components.render_header()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("🎛️ Simulation Controls")

    # --------------------------------------------------------
    # START / PAUSE
    # --------------------------------------------------------

    start_col, pause_col = st.columns(2)

    if start_col.button(
        "▶ Start",
        use_container_width=True,
    ):

        sim.running = True

    if pause_col.button(
        "⏸ Pause",
        use_container_width=True,
    ):

        sim.running = False

    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------

    if st.button(
        "🔄 Reset Simulation",
        use_container_width=True,
    ):

        st.session_state.simulator = Simulator()

        sim = st.session_state.simulator

        # Apply current manual values after reset
        sim.set_manual_energy(
            solar_w=st.session_state.manual_solar_w,
            load_w=st.session_state.manual_load_w,
            battery_w=st.session_state.manual_battery_w,
        )

        st.session_state.last_tick = sim.step()

        st.rerun()

    st.divider()

    # --------------------------------------------------------
    # SIMULATION SPEED
    # --------------------------------------------------------

    speed = st.select_slider(
        "Simulation speed",
        options=[
            0.1,
            0.25,
            0.5,
            1.0,
            2.0,
        ],
        value=sim.dt_hours,
        help="Simulated hours advanced per tick.",
    )

    sim.dt_hours = speed

    # --------------------------------------------------------
    # REFRESH SPEED
    # --------------------------------------------------------

    refresh_seconds = st.slider(
        "Dashboard refresh",
        min_value=0.5,
        max_value=5.0,
        value=1.5,
        step=0.5,
        format="%.1f sec",
    )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    status_icon = (
        "🟢"
        if sim.running
        else "⏸️"
    )

    status_text = (
        "RUNNING"
        if sim.running
        else "PAUSED"
    )

    st.info(
        f"**Simulated Time:** {sim._time_label()}\n\n"
        f"**Status:** {status_icon} {status_text}"
    )

    # --------------------------------------------------------
    # MANUAL STEP
    # --------------------------------------------------------

    if st.button(
        "⏭️ Manual Step",
        use_container_width=True,
    ):

        st.session_state.last_tick = sim.step()

        st.rerun()

    st.divider()

    # ========================================================
    # MANUAL ENERGY INPUT
    # ========================================================

    st.header("⚡ Manual Energy Input")

    st.caption(
        "Enter energy values for testing and demonstration."
    )

    solar_input = st.number_input(
        "☀️ Solar Generation (W)",
        min_value=0.0,
        max_value=10000.0,
        value=float(
            st.session_state.manual_solar_w
        ),
        step=10.0,
    )

    load_input = st.number_input(
        "🏠 Load Demand (W)",
        min_value=0.0,
        max_value=10000.0,
        value=float(
            st.session_state.manual_load_w
        ),
        step=10.0,
    )

    battery_input = st.number_input(
        "🔋 Battery Support (W)",
        min_value=0.0,
        max_value=10000.0,
        value=float(
            st.session_state.manual_battery_w
        ),
        step=10.0,
    )

    if st.button(
        "⚡ Apply Energy Values",
        use_container_width=True,
    ):

        # Save values in Streamlit session
        st.session_state.manual_solar_w = solar_input
        st.session_state.manual_load_w = load_input
        st.session_state.manual_battery_w = battery_input

        # IMPORTANT:
        # Send values to actual simulator
        sim.set_manual_energy(
            solar_w=solar_input,
            load_w=load_input,
            battery_w=battery_input,
        )

        # Immediately calculate new state
        st.session_state.last_tick = sim.step()

        st.success(
            "Energy values applied to simulation."
        )

        st.rerun()

    st.caption(
        f"Solar: "
        f"{st.session_state.manual_solar_w:.1f} W"
    )

    st.caption(
        f"Load: "
        f"{st.session_state.manual_load_w:.1f} W"
    )

    st.caption(
        f"Battery: "
        f"{st.session_state.manual_battery_w:.1f} W"
    )

    st.divider()

    # ========================================================
    # NODE FAULT INJECTION
    # ========================================================

    st.header("⚠️ Node Fault Injection")

    for node in sim.nodes:

        st.markdown(
            f"**{node.node_id}**"
        )

        fail_col, recover_col = st.columns(2)

        # ----------------------------------------------------
        # FAIL
        # ----------------------------------------------------

        if node.status == "HEALTHY":

            if fail_col.button(
                "❌ FAIL",
                key=f"fail_{node.node_id}",
                use_container_width=True,
            ):

                sim.fail_node(
                    node.node_id
                )

                st.session_state.last_tick = (
                    sim.step()
                )

                st.rerun()

        else:

            fail_col.button(
                "❌ FAILED",
                key=f"fail_disabled_{node.node_id}",
                use_container_width=True,
                disabled=True,
            )

        # ----------------------------------------------------
        # RECOVER
        # ----------------------------------------------------

        if node.status == "FAILED":

            if recover_col.button(
                "✅ RECOVER",
                key=f"recover_{node.node_id}",
                use_container_width=True,
            ):

                sim.recover_node(
                    node.node_id
                )

                st.session_state.last_tick = (
                    sim.step()
                )

                st.rerun()

        else:

            recover_col.button(
                "✅ RECOVER",
                key=f"recover_disabled_{node.node_id}",
                use_container_width=True,
                disabled=True,
            )


# ============================================================
# SIMULATION TICK
# ============================================================

if sim.running:

    st.session_state.last_tick = sim.step()


tick = st.session_state.last_tick


# ============================================================
# AI ENERGY INTELLIGENCE
# ============================================================

try:

    prediction = run_prediction(
        sim.nodes,
        sim.sim_time_hours % 24,
    )

    components.render_ai_prediction(
        prediction
    )

except Exception as e:

    st.warning(
        f"AI Energy Intelligence unavailable: {e}"
    )


# ============================================================
# LIVE ENERGY FLOW
# ============================================================

components.render_energy_flow(
    tick
)

st.divider()


# ============================================================
# NODE STATUS
# ============================================================

st.subheader("🔋 Node Status")

node_columns = st.columns(
    len(tick.nodes)
)

for column, node_snapshot in zip(
    node_columns,
    tick.nodes,
):

    with column:

        components.render_node_card(
            node_snapshot
        )


st.divider()


# ============================================================
# POWER DISTRIBUTION
# ============================================================

st.subheader("⚡ Power Distribution")

distribution_columns = st.columns(
    len(tick.nodes)
)

for column, node_snapshot in zip(
    distribution_columns,
    tick.nodes,
):

    with column:

        node_id = node_snapshot["node_id"]

        status = node_snapshot["status"]

        solar = node_snapshot[
            "solar_generation_w"
        ]

        battery = node_snapshot[
            "battery_power_w"
        ]

        net_power = node_snapshot[
            "net_power_w"
        ]

        current = node_snapshot[
            "current_a"
        ]

        if status == "FAILED":

            st.error(
                f"❌ {node_id}\n\n"
                "NODE FAILED\n\n"
                "Power contribution: 0 W"
            )

        else:

            st.success(
                f"🟢 {node_id}"
            )

            st.metric(
                "Solar",
                f"{solar:.1f} W",
            )

            st.metric(
                "Battery",
                f"{battery:.1f} W",
            )

            st.metric(
                "Net Power",
                f"{net_power:.1f} W",
            )

            st.metric(
                "Current",
                f"{current:.2f} A",
            )


# ------------------------------------------------------------
# Total power distribution
# ------------------------------------------------------------

total_node_power = sum(
    node["net_power_w"]
    for node in tick.nodes
)

st.info(
    f"**Total distributed node power: "
    f"{total_node_power:.1f} W**"
)

st.divider()


# ============================================================
# ENERGY + LOAD + TOPOLOGY
# ============================================================

left, right = st.columns(
    [2, 1],
    gap="large",
)


with left:

    components.render_energy_summary(
        tick
    )

    st.write("")

    components.render_load_priority(
        tick.load_status
    )


with right:

    components.render_topology(
        tick.nodes
    )

    st.write("")

    components.render_event_log(
        sim.event_log
    )


st.divider()


# ============================================================
# SYSTEM HEALTH + SIMULATION STATUS
# ============================================================

health_col, status_col = st.columns(
    2,
    gap="large",
)

with health_col:

    components.render_system_health(
        tick.nodes
    )


with status_col:

    components.render_simulation_status(
        sim
    )


st.divider()


# ============================================================
# HISTORICAL CHARTS
# ============================================================

st.subheader(
    "📊 Historical Energy Analytics"
)

df = charts.history_to_dataframe(
    sim.history
)

node_ids = [
    node["node_id"]
    for node in tick.nodes
]


if not df.empty:

    # --------------------------------------------------------
    # Row 1
    # --------------------------------------------------------

    chart_col1, chart_col2 = st.columns(
        2,
        gap="large",
    )

    with chart_col1:

        st.plotly_chart(
            charts.solar_generation_chart(
                df,
                node_ids,
            ),
            use_container_width=True,
        )

    with chart_col2:

        st.plotly_chart(
            charts.battery_soc_chart(
                df,
                node_ids,
            ),
            use_container_width=True,
        )

    # --------------------------------------------------------
    # Row 2
    # --------------------------------------------------------

    chart_col3, chart_col4 = st.columns(
        2,
        gap="large",
    )

    with chart_col3:

        st.plotly_chart(
            charts.load_demand_chart(
                df
            ),
            use_container_width=True,
        )

    with chart_col4:

        st.plotly_chart(
            charts.available_vs_demand_chart(
                df
            ),
            use_container_width=True,
        )

else:

    st.info(
        "Run the simulation to generate historical charts."
    )


# ============================================================
# CURRENT MANUAL ENERGY VALUES
# ============================================================

st.divider()

st.subheader(
    "⚡ Current Manual Energy Configuration"
)

c1, c2, c3 = st.columns(3)

c1.metric(
    "☀️ Solar Input",
    f"{st.session_state.manual_solar_w:.1f} W",
)

c2.metric(
    "🏠 Load Input",
    f"{st.session_state.manual_load_w:.1f} W",
)

c3.metric(
    "🔋 Battery Support",
    f"{st.session_state.manual_battery_w:.1f} W",
)


# ============================================================
# FOOTER
# ============================================================

st.divider()

footer_col1, footer_col2 = st.columns(2)

with footer_col1:

    st.caption(
        "⚡ Disaster Energy Mesh | "
        "Self-Healing Emergency Microgrid"
    )

with footer_col2:

    st.caption(
        f"Simulation time: "
        f"{sim._time_label()}"
    )


# ============================================================
# AUTO REFRESH
# ============================================================

if sim.running:

    time.sleep(
        refresh_seconds
    )

    st.rerun()