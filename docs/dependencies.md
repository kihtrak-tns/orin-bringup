# Pinned / documented dependency versions

Per A4 ("pinned dependency versions"). Values marked "settled by evidence"
come straight from `orin_bringup_plan.md`; values marked TODO were not in
either project doc and need to be captured from the actual Orin.

| Component | Version | Source |
|---|---|---|
| L4T (JetPack 6 family) | R36, rev 5.2 (`nvidia-l4t-core 36.5.2-20260716114719`, GCID 46426093) = JetPack 6.2.2; `nvidia-jetpack` meta not installed | settled by evidence (verified live, A5, 2026-09-28) |
| Board | Jetson Orin Nano Engineering Reference Developer Kit Super; nvpmodel 25W | verified live (A5) |
| CUDA | 12.6 (`cuda-runtime-12-6`, cudart 12.6.68); `cuda-nvcc-12-6 12.6.68-1` added in A5 (needed by the ZED SDK CMake config) | verified live (A5) |
| cuDNN / TensorRT | `libcudnn9-cuda-12 9.3.0.75` / `tensorrt-libs 10.3.0.30+cuda12.5` | verified live (A5) |
| OS | Ubuntu 22.04 | settled by evidence |
| ROS 2 distro | Humble | settled by evidence |
| micro-ROS agent | built on-device from source | settled by evidence (commit/tag: TODO -- capture `git -C <micro_ros_setup checkout> rev-parse HEAD` on the Orin) |
| VESC firmware | 6.06 `no_hw_limits`, hw "60" | settled by evidence (esp32_installed_firmware_findings.md) |
| ESP32 firmware | ESP-IDF v6.0.1, build `cba74e7-dirty`, 5 Sep 2026 16:30:57, SHA-256 `fb31999e69da97f8f99459eee75291f84b673eb0df58d0282d5b41805030a17d` | settled by evidence |
| LiDAR | Slamtec A2M12, 256000 baud; device firmware 1.32, hw rev 6 | settled by evidence (A2 driver log, 2026-09-28) |
| sllidar_ros2 | source, `github.com/Slamtec/sllidar_ros2` @ `34300099fadfc772965962dec837bf436706188f` (main, 2024-06-17; no release tags upstream), package 1.0.1, SLLIDAR SDK 2.1.0; built in `~/laksa_ws/src/sllidar_ros2` (sibling of this repo, not vendored in it). No apt package for Humble. | settled by evidence (A2, 2026-09-28) |
| ZED SDK | **5.5.0** for JetPack 6.2.2 / L4T 36.5 (CUDA 12.6), `ZED_SDK_Tegra_L4T36.5_v5.5.0.zstd.run`, SHA-256 `3039e37d90c75fe846baf9358917c0a018dc8e86f660dd2a6e5986775a779fe1`; URL `https://download.stereolabs.com/zedsdk/5.5/l4t36.5/jetsons` (from stereolabs.com/developers/release, 2026-09-28); installed `-- silent skip_python` to `/usr/local/zed` | settled by evidence (A5) |
| ZED 2i unit | S/N 38400764, camera FW 1523, sensors FW 778 | verified live (A5) |
| zed-ros2-wrapper | TODO (A5 step 7, not started) | — |
| rosdep / apt package versions for this workspace | TODO -- run `rosdep install --from-paths src --ignore-src -r -y` on the Orin and capture the resolved package versions here once colcon build succeeds |

Firmware provenance (public repo `Project-LAKSA/project_laksa`, cloned
2026-09-27 to build `laksa_interfaces`):

| Branch | Commit | Used for |
|---|---|---|
| `add_micro_ros_support` | `cba74e7` | base commit the flashed build compiled from (before its uncommitted changes) |
| `autonomy-handoff-2026-09-02` | `4787d05` | `DriveCommand`, `VescState` |
| `production/laksa-mainline` | `1f0db4f` | `Pca9685State`, `VehicleState` |
