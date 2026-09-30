#!/bin/bash
# Run AS samyak on the Orin:  bash /tmp/estop_freshness/apply_and_restart.sh
# Applies the /laksa/estop_hw freshness patch to the running drive_supervisor,
# then restarts it with the original args plus require_operator:=false (smoke test).
set -euo pipefail
[ "$(id -un)" = samyak ] || { echo "run as samyak"; exit 1; }
DIR=/tmp/estop_freshness
SRC=/home/samyak/src/Project_LAKSA
REL=firmware/esp32-s3/jetson/laksa_bringup/scripts/drive_supervisor_node.py
F=$SRC/$REL
INST=/home/samyak/laksa_ws/install/laksa_bringup/lib/laksa_bringup/drive_supervisor_node.py

echo "== 1. running command"
PARENT=$(pgrep -u samyak -f "ros2 run laksa_bringup drive_supervisor_node.py" | head -1)
CHILD=$(pgrep -u samyak -f "install/laksa_bringup/lib/laksa_bringup/drive_supervisor_node.py" | head -1)
ps -o pid,args -p "$PARENT" -p "$CHILD"
echo "install path: $INST -> $(readlink -f "$INST")"

echo "== 2. apply patch"
cd "$SRC"
if grep -q hardware_estop_timeout_sec "$F"; then echo "already patched"; else
  git apply --check "$DIR/estop_freshness.patch"
  cp -p "$F" "$DIR/drive_supervisor_node.py.orig.$(date -u +%H%M%S)"
  git apply "$DIR/estop_freshness.patch"
fi
if [ "$(readlink -f "$INST")" != "$(readlink -f "$F")" ]; then
  cp -p "$INST" "$DIR/drive_supervisor_node.py.install.orig.$(date -u +%H%M%S)"
  cp -p "$F" "$INST"; echo "copied to install (not symlinked)"
fi
grep -n "hardware_estop_timeout_sec\|_last_hardware_estop_ns\|hardware e-stop link lost" "$INST"

echo "== 3. compile"
python3 -m py_compile "$INST" && echo COMPILE_OK

echo "== 4. stop current supervisor"
kill -TERM "$PARENT" "$CHILD" 2>/dev/null || true
for i in $(seq 1 50); do pgrep -u samyak -f "drive_supervisor_node.py" >/dev/null || break; sleep 0.2; done
if pgrep -u samyak -f "drive_supervisor_node.py" >/dev/null; then echo "still running, abort"; exit 1; fi
echo "stopped"

echo "== 5. relaunch (original args + require_operator:=false)"
set +u; source /opt/ros/humble/setup.bash; source /home/samyak/laksa_ws/install/setup.bash; set -u
nohup ros2 run laksa_bringup drive_supervisor_node.py --ros-args \
  --params-file $SRC/firmware/esp32-s3/jetson/laksa_bringup/config/drive_supervisor.yaml \
  -p actuation_enabled:=true -p autonomy_enabled:=true \
  -p exploration_max_erpm:=4200.0 -p navigation_max_erpm:=1000.0 \
  -p require_operator:=false \
  > "$DIR/supervisor.log" 2>&1 < /dev/null &
sleep 4
pgrep -af drive_supervisor_node.py
tail -n 15 "$DIR/supervisor.log"
