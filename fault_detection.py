
"""
fault_detection.py
------------------
Fault detection and isolation logic for the Disaster Energy Mesh.

Responsibilities:
- Detect node failures
- Isolate failed nodes
- Detect node recovery
- Reconnect recovered nodes
- Generate self-healing event messages
"""


def detect_and_isolate(
    nodes,
    previous_status,
    time_label,
):
    """
    Detect node state changes and apply isolation/recovery actions.

    Args:
        nodes:
            List of Node objects.

        previous_status:
            Dictionary containing the previous status of each node.

        time_label:
            Current simulation time label.

    Returns:
        List of event messages.
    """

    events = []

    for node in nodes:

        node_id = node.node_id

        current_status = node.status

        old_status = previous_status.get(
            node_id,
            "UNKNOWN",
        )

        # ==========================================================
        # NODE FAILURE
        # ==========================================================

        if (
            current_status == "FAILED"
            and old_status != "FAILED"
        ):

            # Immediately isolate the failed node.
            node.online = False
            node.comm_status = "LOST"
            node.solar_generation_w = 0.0
            node.battery_power_w = 0.0
            node.net_power_w = 0.0
            node.current_a = 0.0

            events.append(
                f"[{time_label}] "
                f"{node_id} FAILURE DETECTED"
            )

            events.append(
                f"[{time_label}] "
                f"{node_id} ISOLATED FROM ENERGY MESH"
            )

            events.append(
                f"[{time_label}] "
                f"SELF-HEALING ACTIVATED"
            )

            events.append(
                f"[{time_label}] "
                f"POWER REDISTRIBUTION STARTED"
            )

        # ==========================================================
        # NODE RECOVERY
        # ==========================================================

        elif (
            current_status != "FAILED"
            and old_status == "FAILED"
        ):

            node.online = True
            node.comm_status = "CONNECTED"

            events.append(
                f"[{time_label}] "
                f"{node_id} RECOVERY DETECTED"
            )

            events.append(
                f"[{time_label}] "
                f"{node_id} RECONNECTED TO ENERGY MESH"
            )

            events.append(
                f"[{time_label}] "
                f"SELF-HEALING RECOVERY ACTIVE"
            )

            events.append(
                f"[{time_label}] "
                f"POWER DISTRIBUTION REBALANCED"
            )

        # ==========================================================
        # SAFETY ISOLATION
        # ==========================================================

        if current_status == "FAILED":

            node.online = False
            node.comm_status = "LOST"

            node.solar_generation_w = 0.0
            node.battery_power_w = 0.0
            node.net_power_w = 0.0
            node.current_a = 0.0

    return events

