# Pinned / documented dependency versions

Per A4 ("pinned dependency versions"). Values marked "settled by evidence"
come straight from `orin_bringup_plan.md`; values marked TODO were not in
either project doc and need to be captured from the actual Orin.

| Component | Version | Source |
|---|---|---|
| L4T (JetPack 6 family) | R36, rev 5.2 | settled by evidence |
| OS | Ubuntu 22.04 | settled by evidence |
| ROS 2 distro | Humble | settled by evidence |
| micro-ROS agent | built on-device from source | settled by evidence (commit/tag: TODO -- capture `git -C <micro_ros_setup checkout> rev-parse HEAD` on the Orin) |
| VESC firmware | 6.06 `no_hw_limits`, hw "60" | settled by evidence (esp32_installed_firmware_findings.md) |
| ESP32 firmware | ESP-IDF v6.0.1, build `cba74e7-dirty`, 5 Sep 2026 16:30:57, SHA-256 `fb31999e69da97f8f99459eee75291f84b673eb0df58d0282d5b41805030a17d` | settled by evidence |
| LiDAR | Slamtec A2M12, 256000 baud (planned, `sllidar_ros2`) | plan (A2, not yet installed) |
| ZED | ZED 2i, SDK version TODO (must match Orin's L4T/CUDA per A5) | plan (A5, not yet installed) |
| rosdep / apt package versions for this workspace | TODO -- run `rosdep install --from-paths src --ignore-src -r -y` on the Orin and capture the resolved package versions here once colcon build succeeds |

Firmware provenance (public repo `Project-LAKSA/project_laksa`, cloned
2026-09-27 to build `laksa_interfaces`):

| Branch | Commit | Used for |
|---|---|---|
| `add_micro_ros_support` | `cba74e7` | base commit the flashed build compiled from (before its uncommitted changes) |
| `autonomy-handoff-2026-09-02` | `4787d05` | `DriveCommand`, `VescState` |
| `production/laksa-mainline` | `1f0db4f` | `Pca9685State`, `VehicleState` |
