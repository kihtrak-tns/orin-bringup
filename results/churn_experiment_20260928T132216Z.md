# micro-ROS session-churn experiment: idle vs CPU load vs LiDAR+ZED

Run at: 2026-09-28T09:06:51Z → 09:56:15Z (three 15-min windows). Analysis
written at 2026-09-28T13:22:16Z. The run finished on schedule, but its
completion notification reached Claude Code ~3.4 h late, and that gap
produced an extra 3.4 h idle sample (see *Extended idle*).
Run by: local Claude Code, unattended, listen-only (no command publisher, no
battery gate). Run directory on the Orin:
`~/churn_exp/run_20260928T090651Z/` (windows.txt, vmstat.txt,
tegrastats.txt, state_arrivals.txt, agent_state.txt, lidar/zed logs).
Scripts: `~/churn_exp/{run_churn.sh,state_probe.py,analyze_churn.py}`.

## Short answer
- **CPU load does not raise churn.** 100% CPU on all 6 cores for 15 min
  gave 3 resets, inside the normal idle range (3–9 per 15 min).
- **LiDAR+ZED running is associated with more churn.** 11 resets, above
  every one of 14 idle 15-min windows observed (max 9), ~1.9× the idle
  mean, at *lower* CPU (38%) than the CPU condition. That points away from
  CPU and toward something the drivers add: shared-hub USB traffic, USB bus
  power draw, or DDS/GPU activity. **n = 1 window per condition, so this is
  suggestive, not proven**, and it can't yet separate USB from those other
  explanations.
- **The churn is substantial even at idle** (~5.7 resets per 15 min, ~23/h,
  with only the agent + health running). Load at most roughly doubles an
  existing problem; it doesn't cause it. The root cause is still open.
- **Every stall is a session reset.** Over 45 min, each `/laksa/state` gap
  over 1 s lined up with a logged teardown/re-create (±2 s); 0 silent stalls,
  0 gaps over 5 s. The "silent, no teardown" mode seen once at 00:42Z did not
  reappear.
- The agent process never crashed: same PID 643, `NRestarts=0` before and
  after every condition. All events are XRCE session resets, not agent
  restarts.

## Step 0: USB topology (sysfs + `lsusb -t` + `lsusb -v`)
Single xHCI controller `3610000.usb` (tegra-xusb). `usb1` (USB 2.0 root,
480M) and `usb2` (USB 3.x root, 10000M) are the two halves of that one
controller. Everything hangs off one external Realtek USB 3.0 hub:
USB3 half `0bda:0489` (2-1) + USB2 half `0bda:5489` (1-2).

| device | sysfs | speed | path |
|---|---|---|---|
| ESP32 "LAKSA micro-ROS CDC" 303a:4001 | 1-2.3 | 12M (Full) | usb1 → hub 1-2 port 3 |
| LiDAR CP2102 10c4:ea60 | 1-2.1 | 12M (Full) | usb1 → hub 1-2 port 1 |
| ZED-2i HID/IMU 2b03:f881 | 1-2.4.2 | 12M | usb1 → hub 1-2 port 4 → hub 0424:2512 port 2 |
| ZED 2i video 2b03:f880 | 2-1.4 | 5000M | usb2 → hub 2-1 port 4 (SuperSpeed lanes) |
| Bluetooth 0bda:c822 | 1-3 | 12M | usb1 root port 3 (not via the hub) |

- The ESP32 and the LiDAR (plus the ZED's HID) **share the same USB 2.0 hub**
  (480M upstream). The ZED's video is on the **same physical hub chip** but
  over its separate SuperSpeed lanes. All of it is on **one controller**.
- Hub TT type: `1-2` and `1-2.4` both have **bDeviceProtocol 2 = multi-TT
  ("TT per port")**. Each Full-speed device gets its own transaction
  translator, so the ESP32 is *not* squeezed into a single shared 12 Mbit/s
  TT with the LiDAR and ZED HID. That weakens the simplest "full-speed
  bandwidth starvation" theory. Shared hub, shared upstream, shared
  controller and shared VBUS power remain.

## Method
- **Reset signal:** agent journal lines `Root.cpp | delete_client` (session
  teardown, always immediately followed by `establish_session`), timestamped
  by the agent's own epoch field, counted inside each window. Same signal as
  A6 and the earlier notes.
- **Stall signal:** a listen-only rclpy probe (`state_probe.py`, BEST_EFFORT)
  logged the arrival time of every `/laksa/state` message for the whole run.
  Stall = inter-arrival gap > 1 s.
- **Load measurement:** `vmstat -t 60` (15 samples per window) and
  `tegrastats --interval 5000` (180 samples per window; per-core CPU and
  GR3D GPU).
- **Conditions,** each exactly 15 min 0 s, back to back, with ~60–80 s
  uncounted settle periods between:
  - **a. idle:** boot services only (agent + health), plus the probe and
    monitors.
  - **b. CPU:** `stress-ng` is not installed, and it was not installed
    (it would need sudo). Fallback: 6 bash busy-loops (one per core,
    `nproc`=6), started 20 s before the window and killed at its end.
    Validity check at +1 min: tegrastats `CPU [100%@1344 ×6]`, vmstat us=99
    id=0 r=6. **Valid.**
  - **c. LiDAR+ZED:** same invocations as A2/A5, started ~55 s before the
    window. Pre-window check at 09:40:57Z: `/scan` 12.7 Hz,
    `/zed/zed_node/odom` 36.3 Hz. Stopped with SIGINT after the window.

## Results

| condition | window (UTC) | resets | stalls >1 s | stalls >5 s | stalls w/o reset | `/laksa/state` Hz | CPU % (tegrastats avg) | CPU % (vmstat us+sy) | run queue | GPU % |
|---|---|---|---|---|---|---|---|---|---|---|
| a. idle | 09:07:51–09:22:51 | **2** | 1 | 0 | 0 | 7.81 | 1.6 | 2.1 | 0.2 | 0.0 |
| b. CPU busy-loop | 09:24:11–09:39:11 | **3** | 2 | 0 | 0 | 7.83 | **100.0** | **100.0** | 6.1 | 0.0 |
| c. LiDAR+ZED | 09:41:05–09:56:05 | **11** | 10 | 0 | 0 | 7.74 | 37.9 | 38.6 | 2.1 | 10.7 |

Reset times (UTC):
- a: 09:08:29, 09:09:21
- b: 09:31:25, 09:32:10, 09:36:41
- c: 09:43:17, 09:43:30, 09:45:17, 09:45:30, 09:46:35, 09:47:02, 09:47:16,
  09:53:45, 09:54:01, 09:54:11, 09:54:58

Stalls (start, length): a: 09:09:20 2.49 s. b: 09:32:10 1.99 s, 09:36:40
1.02 s. c: 09:43:17 2.00, 09:43:29 1.13, 09:45:16 1.99, 09:45:29 2.03,
09:46:34 1.65, 09:47:01 1.85, 09:47:15 1.24, 09:53:45 1.94, 09:54:00 1.01,
09:54:57 2.06 s. Each lines up with a reset. Some resets have no >1 s stall
(the reconnect was fast enough to lose <1 s of data).

Resets in (c) come in **clusters** 13–27 s apart (09:43:17/09:43:30,
09:45:17/09:45:30, 09:46:35/09:47:02/09:47:16, 09:53:45/09:54:01/09:54:11),
separated by quiet stretches of several minutes.

## Extended idle (unplanned, post-run)
From RUN_END 09:56:15Z to 13:21Z (3.43 h), nothing else ran: no drivers,
probe, loads or bags (checked). The only SSH logins were Claude Code's own
at ~13:20Z, after the data. **78 resets**, in 13 full 15-min buckets:

`[5, 9, 4, 4, 5, 7, 9, 7, 7, 4, 3, 7, 3]`: mean **5.69**, median 5, min 3,
max 9, stdev 2.10.

Across all 14 idle windows (a + these 13), 15-min counts range **2–9**.
Condition (a)'s 2 was the quietest idle window observed.

## What the data does and doesn't support
- **Supported:** 100% CPU doesn't increase churn (b = 3, inside the idle
  range). **Plain CPU starvation of the agent is not the mechanism.**
- **Supported, with moderate confidence:** running LiDAR+ZED raises churn.
  (c) = 11 is above all 14 idle windows (p ≈ 1/15 if it were just another
  idle window; about +2.5 sd from the idle mean). It is a single window,
  though, and the idle rate itself swings 2–9. A repeat of (c), plus a
  second long idle run, would firm this up.
- **Not separated:** *which* part of the drivers matters. (c) differs from
  idle in several ways at once:
  1. USB traffic on the shared hub/controller: LiDAR on the same USB2 hub,
     ZED video on the same hub chip's USB3 half, ZED HID on the USB2 half.
  2. USB bus power: the ZED 2i and the LiDAR motor draw from the same hub's
     VBUS as the ESP32. A sag could disturb the ESP32's USB-CDC without a
     full re-enumeration (still 0 re-enumerations in the kernel log).
  3. DDS traffic on the Orin (ZED publishes large images; the agent shares
     the DDS domain).
  4. GPU load (10.7% avg) and the power/thermal state that goes with it.

  CPU was *lower* in (c) than in (b), so CPU isn't the confound.
- **Not supported:** load as the root cause. Churn runs at ~23/h with
  nothing running, so the core defect is present at rest.

## Suggested next experiments (not run)
In rough order of information per effort:
1. **Separate LiDAR and ZED:** 15 min LiDAR-only and 15 min ZED-only, ideally
   twice each, and repeat LiDAR+ZED. Tells us which driver matters.
2. **Physical separation:** move the ESP32 to a different Orin USB port
   (not via the shared hub, e.g. a root-port USB-A if the board has one
   free), then rerun idle and LiDAR+ZED. If the (c) excess disappears, that
   points strongly at the shared hub (traffic or power). Needs the operator
   (physical change).
3. **Power:** a powered hub for the ZED/LiDAR, or ZED on its own port.
4. **Firmware/transport side (idle churn):** agent `-v6` for per-message
   timing around a teardown; `rmw_uros_ping_agent` timeouts in the ESP32
   firmware; ESP32 serial console for resets. The idle rate (~23/h) is the
   bigger problem for Phase C and has to be fixed regardless of load.

## Cleanup
Nothing left running at the end (busy-loops, drivers, probe, vmstat,
tegrastats all stopped; checked at 09:56Z and again at 13:21Z). The LiDAR
driver logged `Stop motor` and "process has finished cleanly" this time
(unlike A2/A6), so the motor-stop command was sent. **The operator should
still glance at the LiDAR to confirm it isn't spinning.** Not blocking.
