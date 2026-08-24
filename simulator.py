"""
simulator.py
------------
The Simulator is the single source of truth for the mesh's state. The
Streamlit UI (app.py) only ever reads from it and calls its control
methods (step, fail_node, recover_node, reset). No display value is
ever fabricated in the UI layer -- everything shown on the dashboard is
produced by this engine.

Energy balance per tick:
  1. Compute each healthy node's solar generation from the time-of-day
     daylight curve.
  2. Sum total generation and total available battery discharge power
     across healthy nodes -> total available power.
  3. Allocate available power to Priority 1/2/3 loads (control/load_management.py).
  4. Whatever power is left over (surplus) charges batteries; a deficit
     is drawn from batteries. Both are split proportionally across
     healthy nodes' available headroom / reserves.
  5. Update each node's electrical readings (V, I, P), temperature and
     health.
  6. Run fault detection to log any state transitions.
"""

from dataclasses import dataclass, field
from simulation.node import Node
from simulation.energy import solar_daylight_factor, PRIORITY_LOADS
from control import fault_detection, load_management


@dataclass
class TickResult:
    time_label: str
    hour_of_day: float
    total_generation_w: float
    total_battery_available_w: float
    total_available_power_w: float
    total_load_demand_w: float
    total_allocated_w: float
    surplus_deficit_w: float
    load_status: dict
    network_status: str
    nodes: list
    events: list


class Simulator:
    def __init__(self):
        self.nodes = [
            Node(node_id="Node 1", solar_capacity_w=200, battery_capacity_wh=500, initial_soc=85),
            Node(node_id="Node 2", solar_capacity_w=150, battery_capacity_wh=400, initial_soc=70),
            Node(node_id="Node 3", solar_capacity_w=100, battery_capacity_wh=300, initial_soc=60),
        ]
        self.sim_time_hours = 6.0     # simulated clock, starts at 06:00
        self.dt_hours = 0.25          # simulated hours advanced per tick (15 min)
        self.running = False
        self.event_log = []
        self._previous_status = {n.node_id: n.status for n in self.nodes}
        self.history = []             # list of TickResult snapshots (as dicts) for charting
        self._log(f"[{self._time_label()}] Simulation initialized. 3 nodes online.")

    # ------------------------------------------------------------------
    # Time helpers
    # ------------------------------------------------------------------
    def _time_label(self) -> str:
        h = int(self.sim_time_hours % 24)
        m = int(round((self.sim_time_hours % 1) * 60))
        if m == 60:
            m = 0
            h = (h + 1) % 24
        return f"{h:02d}:{m:02d}"

    def _log(self, message: str):
        self.event_log.append(message)
        # keep the log bounded so the dashboard stays readable
        self.event_log = self.event_log[-200:]

    # ------------------------------------------------------------------
    # Fault control (called directly from dashboard buttons)
    # ------------------------------------------------------------------
    def fail_node(self, node_id: str):
        for node in self.nodes:
            if node.node_id == node_id and node.status != "FAILED":
                node.fail()

    def recover_node(self, node_id: str):
        for node in self.nodes:
            if node.node_id == node_id and node.status == "FAILED":
                node.recover()

    def reset(self):
        self.__init__()

    # ------------------------------------------------------------------
    # Core tick
    # ------------------------------------------------------------------
    def step(self) -> TickResult:
        time_label = self._time_label()
        daylight_factor = solar_daylight_factor(self.sim_time_hours)

        healthy_nodes = [n for n in self.nodes if n.online]

        # 1. Solar generation per node
        for node in self.nodes:
            node.compute_solar_generation(daylight_factor)

        total_generation = sum(n.solar_generation_w for n in healthy_nodes)
        total_battery_available = sum(n.battery.max_discharge_power_w() / self.dt_hours
                                       for n in healthy_nodes) if self.dt_hours > 0 else 0.0
        total_available_power = total_generation + total_battery_available

        # 2. Allocate loads by priority
        load_status, remaining_power, total_allocated, load_events = load_management.allocate_loads(
            total_available_power, time_label
        )
        net_power = total_available_power - total_allocated  # surplus (+) or would-be deficit (0, since we clamp)

        # 3. Distribute the *actual* physical surplus/deficit across battery banks.
        #    Physical net = generation - allocated_load (can be negative => batteries discharge)
        physical_net = total_generation - total_allocated

        if physical_net >= 0:
            # Surplus: charge batteries proportional to their charge headroom
            total_headroom = sum(n.battery.max_charge_power_w() for n in healthy_nodes)
            for node in healthy_nodes:
                share = (node.battery.max_charge_power_w() / total_headroom) if total_headroom > 0 else 0
                node.battery_power_w = node.battery.apply_power(physical_net * share, self.dt_hours)
        else:
            # Deficit: discharge batteries proportional to their available (above-reserve) energy
            deficit = abs(physical_net)
            total_reserve_avail = sum(n.battery.max_discharge_power_w() for n in healthy_nodes)
            for node in healthy_nodes:
                share = (node.battery.max_discharge_power_w() / total_reserve_avail) if total_reserve_avail > 0 else 0
                node.battery_power_w = node.battery.apply_power(-deficit * share, self.dt_hours)

        # Failed nodes contribute nothing and hold their last SOC frozen
        for node in self.nodes:
            if not node.online:
                node.battery_power_w = 0.0

        # 4. Update readings, temperature, health for every node
        for node in self.nodes:
            node.update_electrical_readings()
            node.update_temperature(self.sim_time_hours % 24)
            node.update_health()

        # 5. Fault detection / event log
        events = fault_detection.detect_and_isolate(self.nodes, self._previous_status, time_label)
        events += load_events
        for e in events:
            self._log(e)

        network_status = load_management.classify_network_status(load_status)
        total_load_demand = sum(l.demand_w for l in PRIORITY_LOADS)

        result = TickResult(
            time_label=time_label,
            hour_of_day=self.sim_time_hours % 24,
            total_generation_w=total_generation,
            total_battery_available_w=total_battery_available,
            total_available_power_w=total_available_power,
            total_load_demand_w=total_load_demand,
            total_allocated_w=total_allocated,
            surplus_deficit_w=physical_net,
            load_status=load_status,
            network_status=network_status,
            nodes=[n.snapshot() for n in self.nodes],
            events=events,
        )
        self.history.append(result)
        self.history = self.history[-500:]

        # advance simulated clock
        self.sim_time_hours += self.dt_hours
        if self.sim_time_hours >= 48:
            self.sim_time_hours -= 24  # keep the number bounded, wraps like a real clock

        return result
