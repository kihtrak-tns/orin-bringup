# ESTOP-bench Part 1 — remaining bridge-only tests (run_is_high=True, run_debounce_reads=5)

Run at: 20260930T091248Z (09:08–09:13 UTC). Battery unplugged. Bridge started by agent via ~/estop_bridge/start_bridge.sh.
Logger: ~/estop_bridge/estop_logger.py → bench_log2.txt

## Output
```
09:08:22.288 data=False (msg #1)
09:08:24.535 data=True (msg #46)
09:08:25 SILENT (last msg 1.2s ago, last data=True)
09:08:36.605 GAP 12.069s
09:08:36.805 data=False (msg #51)
09:08:38.854 data=True (msg #92)
09:08:40 SILENT (last msg 1.4s ago, last data=True)
09:08:48.737 GAP 9.883s
09:08:48.937 data=False (msg #97)
09:10:31.538 data=True (msg #2149)
09:10:51.537 data=False (msg #2549)
09:12:05.237 data=True (msg #4023)
09:12:22.837 data=False (msg #4375)
```
Signal times: kill -TERM 4435 at 09:08:24.515; kill -INT 8205 at 09:08:38.817.

## Results
| Step | Result | Evidence |
|---|---|---|
| B3 retest (debounce 5) | PASS | 09:10:31.538 RUN→STOP directly, held 20.0 s with no blip, RUN at 09:10:51.537 |
| B5 long (3V3 out ~15 s per operator) | PASS | STOP held continuously 09:12:05.237 → 09:12:22.837 (17.6 s), no RUN flicker |
| B6 reconnect | PASS | RUN at 09:12:22.837 |
| B7 SIGTERM (pin RUN) | PASS | final true +20 ms, then silent, exit 0 |
| B7 SIGINT | PASS | final true +37 ms, then silent, exit 0 |
| Debounce 5 STOP→RUN | info | 200 ms (09:08:36.605 → 36.805) |

## Verdict
Part 1 PASS. B4 is still open: it waits on the receiver polarity flip, after which all of B1–B7 get re-run with run_is_high:=false.
