"""
fault_detection.py
-------------------
V2.2 self-healing fault detection engine.

Detects:
- Node failure
- Node isolation
- Communication loss
- Node recovery
- Mesh reconnection

The actual physical isolation is handled by Node.fail().
This module detects state transitions and produces self-healing events.
"""


def detect_and_isolate(
    nodes,
    previous_status: dict,
    time_label: str,
) -> list:

    events = []

    for node in nodes:

        previous = previous_status.get(
            node.node_id,
            "HEALTHY",
        )

        # ==========================================================
        # NODE FAILURE
        # ==========================================================

        if (
            node.status == "FAILED"
            and previous != "FAILED"
        ):

            events.append(
                f"[{time_label}] "
                f"FAULT DETECTED: {node.node_id}"
            )

            events.append(
                f"[{time_label}] "
                f"ISOLATING {node.node_id} from mesh"
            )

            if node.comm_status == "LOST":

                events.append(
                    f"[{time_label}] "
                    f"COMMUNICATION LOST: {node.node_id}"
                )

            events.append(
                f"[{time_label}] "
                f"POWER REDISTRIBUTION STARTED"
            )

            events.append(
                f"[{time_label}] "
                f"AVAILABLE POWER RECALCULATED"
            )

            events.append(
                f"[{time_label}] "
                f"SELF-HEALING ACTIVE"
            )

        # ==========================================================
        # NODE RECOVERY
        # ==========================================================

        elif (
            node.status == "HEALTHY"
            and previous == "FAILED"
        ):

            events.append(
                f"[{time_label}] "
                f"RECOVERY DETECTED: {node.node_id}"
            )

            events.append(
                f"[{time_label}] "
                f"{node.node_id} RECONNECTED TO MESH"
            )

            if node.comm_status == "CONNECTED":

                events.append(
                    f"[{time_label}] "
                    f"COMMUNICATION RESTORED"
                )

            events.append(
                f"[{time_label}] "
                f"POWER REDISTRIBUTION RECALCULATED"
            )

            events.append(
                f"[{time_label}] "
                f"LOAD RESTORATION CHECK"
            )

        # ==========================================================
        # SAVE CURRENT STATE
        # ==========================================================

        previous_status[node.node_id] = node.status

    return events
