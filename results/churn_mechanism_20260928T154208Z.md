# micro-ROS churn mechanism: Part 1 (kernel correlation, autosuspend, agent -v6 ping timing)

Written at: 2026-09-28T15:42:08Z. Run by: local Claude Code (read-only
checks, a live journal capture, a `-v6` agent log analysis) and the operator
(sudo: temporary `-v6` systemd drop-in). Listen-only throughout.
**Part 2 (bookended isolation protocol) not started**, per instructions.

Context: the firmware source (`micro_ros_bridge.c:33-39, 585-593`, per the
operator/cloud Claude) tears the session down after **one** failed agent
ping, with a **100 ms** timeout, pinging every **500 ms**, no retries.

## Headline
**In every captured reset, the agent received the ESP32's ping and replied in
under 1 ms, yet the ESP32 treated the ping as failed and tore the session
down exactly one timeout (~100–110 ms) later.** The host side (kernel, USB
power management, agent) is not what is late. The ping *reply* is not reaching
the ESP32, or not being read by it, within 100 ms. With the firmware's
one-strike policy, that is enough to cause every observed reset.

## 1. Kernel/USB event correlation
- Whole boot (booted 2026-09-28 03:29:27 CDT), **123 resets**: the
  kernel logged **nothing** on the ESP32's device (1-2.3), its hub (1-2), the
  USB2 root or the xHCI controller after the first 60 s of boot. The only
  post-boot USB messages were two ZED start-ups (`uvcvideo 2-1.4 … -71`, then
  `usb 1-2.4.2: reset full-speed` for the ZED HID) at boot+205 s and
  boot+4248 s. The nearest reset was 88–182 s away from each. (Plus one
  "power/level is deprecated" line caused by our own `udevadm info -a` read.)
- Live capture (`journalctl -u laksa-microros-agent -f` ∥ `journalctl -k -f`),
  14:44:37–15:01:33Z: **0 natural resets and 0 kernel lines** (a quiet
  spell; the last reset before it was 14:44:15Z). No 600 ms window to
  inspect from the live capture itself; the historical correlation above
  covers the same question across 123 events.
- Inter-reset intervals over 123 resets: min 3.3 s, p10 22.6 s, median
  118 s, p90 397 s, max 1324 s; 19 of 122 under 30 s (clustering).
- `kernel.dmesg_restrict=1`; the kernel journal is readable via the `adm`
  group.

## 2. Autosuspend state (unchanged)
Same as `results/autosuspend_check_20260928T141630Z.md`, re-read at
~14:5xZ: ESP32 1-2.3 `power/control=on`, `runtime_suspended_time=0`;
1-2 and usb1 `auto` but 0 ms suspended; `connected_duration ==
active_duration` (6.2 h). `usbcore.autosuspend=2`.

## 3. Disabling autosuspend: not run (no-op)
The ESP32's `power/control` is already `on`, and its chain never suspended
once across 123 resets, so writing `on` would change nothing and a 15-min
window would only re-measure idle. Autosuspend is ruled out by observation,
not by intervention. **No power settings were changed.**

## usbmon: unavailable
`modprobe usbmon` failed: this L4T kernel has `# CONFIG_USB_MON is not set`
(not built in, no module). It would need a kernel rebuild, so it wasn't
pursued. Substitute: agent `-v6` (below).

## 4. Agent `-v6` ping timing (the decisive data)
Setup: a temporary systemd drop-in
`/etc/systemd/system/laksa-microros-agent.service.d/v6-debug.conf` (the
operator installed it with sudo) runs the same agent with `-v6` and writes
its output to `~/churn_exp/v6/agent_v6.log` (not the journal: ~950 lines/s
would hit journald's 10k/30 s rate limit). Agent restarted 15:36:12Z
(`NRestarts` stays 0; a manual restart). ~6 MB/min of log.

Identification: the ESP32's ping is an XRCE `GET_INFO` (submessage 0x02,
16 bytes, `recv_message`); the agent's answer is `INFO` (0x06, 36 bytes,
`send_message`). Tools: `~/churn_exp/v6/analyze_v6.py` (per-teardown
summary) and `window.py` (full message sequence for a time range).

Over 15:36:13–15:41:45Z (5.5 min): **646 pings**; the agent's reply latency
was median **0.38 ms**, p99 **0.72 ms** for every in-session ping. The
ESP32's ping cadence was median 506 ms, min 107 ms (the reconnect pings).
**4 teardowns**, all the same shape:

| teardown | last in-session ping | agent reply | ESP32 starts reconnect | old-session cleanup by agent |
|---|---|---|---|---|
| 15:37:22.289Z | 21.567 | 0.42 ms | +107 ms (DELETE burst, then sess-0x80 ping + CREATE_CLIENT at 21.674–.676) | 613 ms |
| 15:38:45.336Z | 44.510 | 0.36 ms | +109 ms | 716 ms |
| 15:41:16.766Z | 16.125 | 0.37 ms | +108 ms | 532 ms |
| 15:41:19.240Z | 18.468 | 0.41 ms | +107 ms | 664 ms |

Full sequence of the first event (from `window.py`): steady WRITE_DATA
(sensor publishes) → **21.567 ping in → 21.568 INFO reply out** → **21.669**
the ESP32 sends READ_DATA/DELETE for all its entities (it has given up) →
21.674 ping on the session-less channel (0x80) + 21.676 CREATE_CLIENT → the
agent deletes the ~20 old DDS entities at **~100 ms per object**
(21.799 … 22.289) → 22.289 old session closed, new session established →
entity re-creation (22.29–22.48) → publishes resume **22.495**. Data outage
≈ 0.94 s, dominated by the agent's slow DDS entity deletion.

## Interpretation
- **Host is prompt:** the agent answers within a millisecond, including in
  the ping that "failed". Not the agent, not the kernel, not USB power
  management, not CPU (see the load experiment).
- **The reply is lost or late on the host→ESP32 leg, or not consumed in
  time on the ESP32.** Candidates:
  1. Host→ESP32 USB delivery delayed > 100 ms (cdc_acm OUT, through the
     shared hub's TT to the full-speed device). No kernel errors, so there
     would be no retries/failures at the URB level.
  2. The ESP32's USB-CDC receive path dropping bytes (TinyUSB RX FIFO or ring
     buffer overflow while the ESP32 is busy streaming WRITE_DATA), which
     corrupts the reply frame, fails the framing CRC, and discards it silently.
  3. The ESP32's transport read or executor not getting to the reply within
     100 ms (task priority/scheduling while publishing; the ping is issued
     from the same loop that publishes).
  Discriminating between these needs ESP32-side instrumentation (count
  framing/CRC errors and RX overflows in the custom transport, log ping
  round-trip time on the ESP32), which is a firmware change.
- **Why load on the shared hub raises the rate:** consistent with (1) or (2):
  more bus traffic, more latency or overflow on the reply path.
- **Why every reset costs ~1 s of data:** a teardown makes the agent delete
  all ~20 DDS entities at ~100 ms each before the new session can be
  established. That's a secondary contributor, on the host side.

## Implications
- The 100 ms / one-strike ping policy is the proximate cause. Given that
  the reply is already on the wire within 1 ms, a **longer timeout and/or
  N consecutive failures before teardown** (firmware change) should remove
  most resets without hiding a real disconnect. The command-freshness
  timeout (500 ms, brake + centre) still guards the actuators independently.
- Every reset re-arms the `/laksa/brake` latch (A1b addendum). A
  command publisher must keep re-releasing it until this is fixed.
- Phase C stays blocked until this is fixed and re-measured.

## State left behind
- **The `-v6` drop-in is still installed** (for Part 2, if the operator
  wants mechanism data per window). Revert:
  `sudo rm -r /etc/systemd/system/laksa-microros-agent.service.d && sudo systemctl daemon-reload && sudo systemctl restart laksa-microros-agent`
- `~/churn_exp/v6/agent_v6.log` grows ~360 MB/h (841 GB free).
- Nothing else changed (power settings at boot defaults, no usbmon).
