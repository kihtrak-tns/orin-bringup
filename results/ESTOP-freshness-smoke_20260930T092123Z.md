# ESTOP-freshness-smoke — drive_supervisor /laksa/estop_hw freshness patch

Run at: 20260930T092123Z (09:17–09:21 UTC). Battery unplugged, no Xbox controller (Y injected on /joy by agent).
Patch: ~/estop_freshness.patch (base SamyakGangwal/Project_LAKSA feature/learned-driver da3b513). Samyak applied it
with /tmp/estop_freshness/apply_and_restart.sh; git apply --check was clean; the install path is a symlink to the source.
Supervisor relaunched with the original args **plus -p require_operator:=false** (override for this test; the service default is True).
Bridge: ~/estop_bridge/external_estop_bridge.py, run_debounce_reads:=5, run_is_high=True.

## Results
| Step | Result | Evidence |
|---|---|---|
| 1 start, no bridge | PASS | estop=True, reason "hardware e-stop link lost" (log 09:16:48.458) |
| 2 bridge up, Y | PASS | hw RUN 09:18:33.120; Y 09:18:34.330 → estop False 09:18:34.332, reason '' |
| 3 kill -9 bridge | PASS | SIGKILL 09:18:36.741 → estop True, "hardware e-stop link lost" at 09:18:37.227 (**485 ms**) |
| 4 restart bridge, Y | PASS | rearmed 09:18:39.163. Y came 44 ms after hw RUN, not 1 s (harness used a stale RUN value); stayed armed |
| 5 open loop | PASS | hw True 09:19:27.406 → latched "hardware emergency stop" 09:19:27.409 (3 ms) |
| 6 close loop, Y | PASS | hw RUN 09:20:38.309; Y 09:20:57.650 → estop False 09:20:57.652, reason '' |

## Notes
- The supervisor logs "Manual throttle neutral interlock released" at 20 Hz after a rearm once /joy goes quiet. This is existing behaviour, not caused by the patch.
- "VESC telemetry stale" is expected with the battery unplugged. It did not block rearm.
- Current state: the patched supervisor is running under nohup (not laksa-car.service) with require_operator:=false. The bridge (pid 9838) is running as karsha.
  To restore the stock service: bash /tmp/estop_freshness/restore.sh (as samyak, needs sudo).

## Verdict
PASS 6/6. The freshness check closes the SIGKILL/OOM gap. Wheels-lift is still blocked on the receiver polarity flip and a B1–B7 re-run with run_is_high:=false.
