# E-stop on live stack — Tx latch → supervisor latch — FAIL (supervisor did not latch)

Run at: 2026-10-02 05:50:44–05:53:44 UTC (press at 05:52:39.922)
Requested change: `sed hardware_estop_enabled: false → true` in `drive_supervisor.yaml`. **Not applied:**
that parameter does not exist in the deployed tree, in `~samyak/src/Project_LAKSA`, or in any commit.
The hardware e-stop check is switched by `hardware_estop_timeout_sec` (default 0.5 s; >0 = on, 0 = off),
so it was already enabled.

## Setup (as found, nothing restarted)
- `drive_supervisor`: `/home/samyak/laksa/current/ws/install/.../drive_supervisor_node.py`,
  params `/home/samyak/laksa/current/src/.../drive_supervisor.yaml`,
  `actuation_enabled:=true autonomy_enabled:=true exploration_max_erpm:=2485 navigation_max_erpm:=1000`
  (full stack live: Nav2, learned_driver, ZED, rtabmap).
- `external_estop_bridge`: `/home/karsha/estop_bridge/external_estop_bridge.py -p run_debounce_reads:=5`, started Oct 1 23:57.
- `/laksa/command`: 1 publisher (drive_supervisor). `/laksa/estop_hw` subscribers: drive_supervisor (+ monitor).
- Car on blocks. Monitor: subscribe-only rclpy node (RELIABLE/VOLATILE) on `/laksa/estop_hw`,
  `/laksa/emergency_stop`, `/laksa/emergency_stop_reason`; logs changes. No publishers.

## Output
```
05:50:44.141 watching for 180s
05:50:44.172 /laksa/estop_hw -> False
05:52:39.922 /laksa/estop_hw -> True
05:52:42.022 /laksa/estop_hw -> False
05:53:44.172 done; message counts: {'/laksa/estop_hw': 3601}
```
Post-test read (`--qos-durability transient_local --qos-reliability reliable`):
`/laksa/emergency_stop: false`, `/laksa/emergency_stop_reason: ''`, `/laksa/command: speed 0.0, steering 0.0, brake true`.

## Human observations (operator, at the car)
- Rx display showed **EMERGENCY STOP** when the Tx latch was pressed.
- Tx was released after ~2 s (matches estop_hw → False at +2.1 s).
- Wheels did **not** move at any point.

## Verdict
| Stage | Result |
|---|---|
| Tx → LoRa → Rx | PASS (operator saw EMERGENCY STOP) |
| Rx → GPIO → bridge → `/laksa/estop_hw` | PASS (True during press; 20.0 Hz, 3601 msgs/180 s, no gaps) |
| Release → RUN | PASS (False at +2.1 s, operator confirms release) |
| `/laksa/estop_hw` → supervisor latch | **FAIL**: no message on `/laksa/emergency_stop` during the window; afterwards `false`, reason empty, no Y press |

**Regression:** the same path latched in 4–5 ms in
[ESTOP-supervisor-follows-Tx](ESTOP-supervisor-follows-Tx_20260930T235347Z.md) and
[EBRAKE-wheelslift-W2W3](EBRAKE-wheelslift-W2W3_20261001T073753Z.md).

Caveat: the monitor used a VOLATILE subscription to a TRANSIENT_LOCAL publisher (QoS-compatible) and received
0 messages on `/laksa/emergency_stop`, meaning the topic publishes on change only. The post-test transient_local
read showing `false` with an empty reason is consistent with "never latched", not "latched then cleared".

Wheels not moving says nothing about the e-stop: `/laksa/command` was already `brake: true` (idle).

**The hardware e-stop cannot currently be relied on to stop the car through the supervisor while actuation is enabled.**

## Next
1. Operator (as samyak) compares the deployed supervisor with the repo copy: `_hardware_estop_callback`,
   `_latch_estop`, and `diff` against `~/src/Project_LAKSA/...`; check the install timestamp. The deployed tree
   is not readable as karsha.
2. Keep the car on blocks or set `actuation_enabled:=false` until the latch is re-verified.
