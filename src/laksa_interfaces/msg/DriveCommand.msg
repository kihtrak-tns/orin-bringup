# Provenance: matches firmware/esp32-s3/extra_ros_packages/laksa_interfaces/msg/DriveCommand.msg
# on branch autonomy-handoff-2026-09-02 @ 4787d05, which is what the flashed build
# (cba74e7-dirty) actually compiled in. Confirmed against strings + live traffic 26 Sep 2026.
# DO NOT hand-edit without re-checking against firmware evidence.
#
# SI-unit drive command. Positive steering is left, following REP-103.
float32 speed_mps
float32 steering_angle_rad
# Request active VESC regenerative/current braking instead of zero-RPM coast.
bool brake
