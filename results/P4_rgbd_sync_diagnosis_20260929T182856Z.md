# rgbd_sync / stale map→odom diagnosis (P4, 2026-09-29, read-only investigation)

Session: `~/laksa_sessions/20260929T121449`, launched 12:14:49 CDT (17:14:49Z), dry-run.
Nothing in the running stack was changed. All of the numbers below were measured.

## Summary
There are **two separate problems**. The investigation shows the controller's "stale TF" is *not* explained by
RTAB-Map having stopped publishing:

1. **rgbd_sync stopped after its first ~70 frames.** Its diagnostics report `Events since startup: 70`, then
   `0 Hz / No data since last update`. RTAB-Map processed updates (1)–(3) at 12:15:04, 12:15:08 and 12:15:10, in
   0.09–0.13 s each (limit 0.7 s), and then logged "Did not receive data" 729 times. rgbd_sync's **configuration and
   inputs are fine**: timestamps line up exactly and every frame arrives (see 2b). Something stalls its input
   delivery a few seconds after start. The cause is not identified.
2. **controller_server's TF cache holds map→odom frozen at 12:15:08.088** (`1790702108.088`, 19 s after launch,
   between RTAB-Map updates (2) at 12:15:08.006 and (3) at 12:15:10.278). This causes the bogus "Reached the goal!" /
   "Goal succeeded": the same stamp for all three goals (12:36:34, 13:12:31, 13:13:35).
   - RTAB-Map **is still publishing map→odom at 20.2 Hz with current stamps** (≈ +0.1 s post-dated), value (0, 0).
   - A fresh tf2 listener gets the *current* map→odom. There's no static map→odom on /tf_static.
   - The **local costmap** (same process and TF buffer as the controller) is current: 9 msgs/5 s, age 0.00 s. So that
     buffer still receives /tf (odom→base_footprint); only its map→odom entry stopped updating.
   - Root cause not identified.

## 2a. rgbd_sync parameters (`/laksa/fused_mapping/rgbd_sync`)
approx_sync: true; approx_sync_max_interval: 0.05 s; queue_size / sync_queue_size / topic_queue_size: 10;
qos: 2 (best effort); qos_camera_info: 2; raw transports; decimation 1.
Inputs: `/zed/zed_node/rgb/color/rect/image`, `/zed/zed_node/depth/depth_registered`,
`/zed/zed_node/rgb/color/rect/camera_info`. Output: `/laksa/fused_mapping/rgbd_image`.

## 2b. Timestamps and delivery (30 s sample, independent probe subscribers)
| Topic | Best effort (what rgbd_sync uses) | Reliable |
|---|---|---|
| RGB | 415 msgs (13.8 Hz) | 414 (13.8 Hz) |
| Depth | 410 (13.7 Hz) | 412 (13.7 Hz) |
| camera_info | 415 (13.8 Hz) | — |

- RGB vs depth `header.stamp`: **identical** for 412/414 frames; max |Δ| 133 ms (2 frames); mean +0.5 ms.
- RGB vs camera_info: identical for 415/415.
- Five spaced samples: Δ = +0.0 ms each (e.g. rgb 1790705689.192142 = depth 1790705689.192142).
- Receive latency (wall clock − stamp): median 108 ms, max 308 ms. All frame_ids `zed_left_camera_frame_optical`.

**So there's no timestamp offset and no best-effort drop at a subscriber.** A 50 ms approx-sync window is ample.

## 2c. rgbd_sync output
`/laksa/fused_mapping/rgbd_image`: nothing in 10 s. Diagnostics: Input and Output status level 2 (ERROR), "No events
recorded", actual 0 Hz vs target 10.7 Hz, **events since startup 70**.

## 2d. RTAB-Map (`/laksa/fused_mapping/rtabmap`)
Subscribes to `/laksa/fused_mapping/rgbd_image` + `/laksa/lidar/scan_validated`. Updates (1)–(3) at Rate=2.00 s,
RTAB-Map time 0.09–0.13 s (limit 0.70 s), then 729 × "Did not receive data since 5 seconds".
`/laksa/fused_mapping/info`: nothing received. map→odom on /tf: 20.2 Hz, value (0, 0).

## 2e. Tolerances
- `/controller_server transform_tolerance`: **not set** at server level; `FollowPath.transform_tolerance` = **0.2 s**.
- `/bt_navigator transform_tolerance` = 0.1 s; `/bt_navigator default_server_timeout` = **20 ms**. That is why the
  plan-once BT aborted 6c's first attempt ("Timed out while waiting for action server to acknowledge goal request for
  compute_path_to_pose"). The plan-once tree has no retry, so under load this can abort a goal spuriously (fail-safe).
- With a ~3,400 s-old cached map→odom, **no tolerance value fixes the controller**: its cache has to be current.

## 2f. Alternatives installed
`rtabmap_slam`; **`slam_toolbox` (ros-humble-slam-toolbox 2.6.10)**, which is LiDAR-only and needs no RGB-D.

## 2g. ZED sync-related parameters
grab_frame_rate 15; pub_frame_rate 15.0; pub_resolution CUSTOM, pub_downscale_factor 2.0; depth_mode NEURAL_LIGHT;
depth_stabilization 1; timestamp_reference IMAGE; sdk_timestamp_clock SYSTEM_CLOCK; use_pub_timestamps false;
sensors_image_sync false; async_image_retrieval false; point_cloud_freq 5.0.

## Recommended fix
**No parameter change is justified by the evidence.** The obvious levers (approx_sync_max_interval, queue sizes, qos,
transform_tolerance) are all ruled out by the measurements. Recommended next steps, in order:
1. **Restart only rgbd_sync** and watch whether it stops again after about 70 frames. That separates an internal
   rgbd_sync stall from start-up load. (Not done tonight: "do not restart".)
2. **Controller TF cache:** reset the Nav2 servers (lifecycle reset or restart), then send one dry-run goal and check that
   `nav_controller.log` has no "Transform data too old". If the freeze comes back at start-up, capture a TF debug log
   (`tf2_monitor map odom`) inside the controller's first 30 s to find the cause.
3. **Fallback for floor driving:** `slam_toolbox` (installed) can publish `map`→`odom` from the LiDAR alone, avoiding
   rgbd_sync. That's a launch/configuration change, not a parameter tweak.

## Impact
**Not a 2-minute parameter fix.** Both problems look like stalls shortly after start-up, not bad settings. Floor routes
(P5+) stay **blocked** until the controller's TF cache is shown to be current. The check is cheap: one dry-run goal,
with no "Transform data too old" in `nav_controller.log`.
