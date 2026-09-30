#!/bin/bash
# Start the bridge in the background with run_debounce_reads:=5; print its PID.
source /opt/ros/humble/setup.bash
nohup python3 -u ~/estop_bridge/external_estop_bridge.py --ros-args -p run_debounce_reads:=5 >> ~/estop_bridge/bridge_run.log 2>&1 < /dev/null &
echo $! > ~/estop_bridge/bridge.pid
echo "started pid $(cat ~/estop_bridge/bridge.pid) at $(date -u +%T.%N | cut -c1-12)"
