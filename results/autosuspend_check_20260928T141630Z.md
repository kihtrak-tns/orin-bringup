# USB autosuspend as a cause of micro-ROS session churn: ruled out from sysfs (no change made)

Checked at: 2026-09-28T14:15:31Z. Written up at 2026-09-28T14:16:30Z.
Run by: local Claude Code over SSH, read-only.
**Nothing was changed.** The system is still in its boot-default state, so
there is nothing to revert.

## Verdict
**USB autosuspend is not the mechanism for the churn.** The ESP32's entire
USB path (device → USB2 hub → USB2 root → xHCI controller) has been
continuously active since boot, **zero ms runtime-suspended in 5.77 h**, and
**119 session resets** happened in that same period. Disabling autosuspend
(plan steps 2–3) would therefore be a no-op on that path, and the planned
15-min window would only have re-measured ordinary idle, so it was **not
run**. The optional MAXN/`jetson_clocks` window (step 5) was not run either:
it needs sudo, and the CPU-DVFS part is already largely covered (see below).

## Baseline (step 1)
Global: `/sys/module/usbcore/parameters/autosuspend` = **2** s (kernel
default). Nothing about usbcore on the kernel cmdline.

Per device (`power/control`, `autosuspend_delay_ms`, `runtime_status`,
runtime-suspended ms since boot):

| sysfs | device | control | delay_ms | status | suspended |
|---|---|---|---|---|---|
| usb1 | xHCI root, USB 2.0 | auto | 0 | active | **0** |
| 1-2 | Realtek 4-port USB 2.0 hub 0bda:5489 | auto | 0 | active | **0** |
| **1-2.3** | **ESP32 "LAKSA micro-ROS CDC" 303a:4001** | **on** | 2000 | active | **0** |
| 1-2.1 | LiDAR CP2102 10c4:ea60 | on | 2000 | active | 0 |
| 1-2.4 | hub 0424:2512 (in ZED) | on | 0 | active | 0 |
| 1-2.4.2 | ZED-2i HID 2b03:f881 | on | 2000 | active | 0 |
| 1-3 | Bluetooth 0bda:c822 | on | 2000 | active | 0 |
| usb2 | xHCI root, USB 3.x | auto | 0 | active | 18,862,821 |
| 2-1 | Realtek 4-port USB 3.0 hub 0bda:0489 | auto | 0 | *resuming* | 18,841,477 |
| 2-1.4 | ZED 2i video 2b03:f880 | auto | 2000 | suspended | 18,842,391 |
| platform `3610000.usb` | xHCI controller | auto | — | active | **0** |

USB-specific counters (ms): the ESP32 has `connected_duration` 20,783,608 =
`active_duration` 20,783,612 (never suspended); the same holds for 1-2 and
usb1. By contrast, the USB 3 half (usb2, 2-1, 2-1.4) was active only ~1,920
s, roughly the time the ZED ran tonight (A6 + churn condition c), and
suspended the rest.

ESP32 tty: `/devices/platform/bus@0/3610000.usb/usb1/1-2/1-2.3/1-2.3:1.0/tty/ttyACM0`.
The cdc_acm interface reports `supports_autosuspend=1`, but the device's
`power/control` is `on` (kernel default for this device; no udev rule sets
it). Uptime since 2026-09-28 03:29:27 CDT; 119 `delete_client` since boot.

udev rules touching `power/control`: `/etc/udev/rules.d/99-slabs.rules`
(from the ZED SDK) sets `on` for Stereolabs IDs (incl. f880, f881) and the
0424:2512 hub; `/lib/udev/rules.d/60-autosuspend.rules` (distro,
hwdb-driven `auto`). Oddity, not affecting the ESP32: the ZED video
device f880 currently reads `auto` despite the Stereolabs rule.

Power mode: `nvpmodel` status file `pmode:0001` = **25W** mode. CPU
min/max 729.6/1344 MHz on all 6 A78 cores, GPU 306–918 MHz (min CONF_VAL
0), GPU power control `auto`, EMC cap 3199 MHz. `jetson_clocks`: no
`jetson_clocks.service`, no mention in this boot's journal, and no
`~/.jetsonclocks_conf.txt` (root's copy isn't readable without sudo). No
evidence it has ever been run. (The ZED installer's MAXN/`jetson_clocks`
step is commented out, see A5.)

## What this rules in or out
- **Ruled out:** runtime autosuspend of the ESP32 device, its hub, the USB2
  root or the xHCI controller. None suspended once in 5.77 h, across 119
  resets.
- **Ruled out for idle churn:** USB3-half suspend/resume. It sits suspended
  steadily at idle while idle churn continues at ~23/h. (Its resumes while
  the ZED runs could still contribute to the LiDAR+ZED excess; not tested.)
- **CPU DVFS: largely covered already.** In the churn experiment's
  condition (b), tegrastats showed all 6 cores pinned at 1344 MHz (max) for
  the full 15 min, i.e. no CPU frequency transitions, and churn was 3,
  inside the idle range 2–9. EMC and GPU DVFS were not covered. A MAXN +
  `jetson_clocks` idle window would cover those, but expected value is low.
  Optional, needs sudo, revert afterwards:
  ```
  ssh -t dev-orin 'sudo nvpmodel -q; sudo nvpmodel -m 0 && sudo jetson_clocks --store && sudo jetson_clocks'
  # ... 15-min idle window ...
  ssh -t dev-orin 'sudo jetson_clocks --restore && sudo nvpmodel -m 1'
  ```
  (Check the mode number for 25W on this board: the status file says
  `pmode:0001`, i.e. mode 1.)

## Where that leaves the churn investigation
With autosuspend and CPU (load and DVFS) set aside, the host-side power
management explanations are largely exhausted for the idle churn.
Remaining, in rough priority:
1. **ESP32/firmware or transport side:** the micro-ROS client's
   ping/timeout and reconnect logic (`rmw_uros_ping_agent`), executor
   stalls (e.g. blocking UART reads to the unpowered VESC, I2C), and the
   serial framing at 115200 baud. Agent `-v6` around a teardown would show
   which side gives up first.
2. **Shared hub (for the LiDAR+ZED excess):** move the ESP32 off the shared
   hub to its own port (physical change, needs the operator).
