# Console REARM diagnostic: root cause of Check A item 5 FAIL, confirmed

Run at: 2026-10-02 07:40:46–07:44:46 UTC. Main battery unplugged (VESC off), actuation_enabled=false,
supervisor latched since 07:15:45 (Check A). Subscribe-only monitor on /laksa/estop_hw, /laksa/emergency_stop,
/laksa/emergency_stop_reason, /joy (logs button changes).
Follows [Check A](ESTOP-checkA-hw-latch_20261002T071545Z.md).

## Hypothesis tested
The supervisor rearms only on a Y rising edge (`y_pressed and not self._previous_y`, drive_supervisor_node.py ~633).
Console REARM (console_node.py:627) publishes Y=1 at 20 Hz for 0.6 s, then publishes **nothing** unless a
HOLD heartbeat is alive ("Otherwise publish nothing"). `_previous_y` therefore stays True after a console REARM,
and the next REARM has no rising edge. The Xbox joy_node is silent with no controller (/joy: 0 msgs in 6 s),
so killing it (as proposed) would not change anything.

## Output
```
07:40:46.657 watching for 240s
07:40:46.673 /laksa/estop_hw -> False
07:41:08.812 /joy buttons -> Y            <- REARM #1
07:41:20.463 /joy buttons -> A            <- HOLD tap
07:41:31.613 /joy buttons -> Y            <- REARM #2
07:41:31.614 /laksa/emergency_stop -> False
07:41:31.615 /laksa/emergency_stop_reason -> ''
```

## Verdict
CONFIRMED. REARM #1 published Y and was ignored (stale `_previous_y` from the 06:59:51 rearm). A HOLD tap
published A with Y=0, resetting it, and REARM #2 cleared the latch 1 ms after Y.
Console STOP (B pulse) has the same edge flaw: a second console STOP with no other /joy message in between is
ignored. The hardware e-stop path is unaffected.

## Workaround (no code change)
While **latched**: tap HOLD briefly, then REARM. Caution: HOLD publishes **A**. When not latched, A held for
`auto_hold_sec` (1.0 s) starts LiDAR cruise. Use the tap only while latched, and keep it short.

## Proposed fix (not applied; needs review and a samyak redeploy)
- console_node: after a pulse expires, publish one all-zero /joy frame; or
- supervisor: reset `_previous_{a,b,x,y}` to False when /joy goes stale (joy_timeout_sec), which covers any publisher.

## State left
Supervisor rearmed (emergency_stop false), actuation_enabled=false, battery unplugged.
