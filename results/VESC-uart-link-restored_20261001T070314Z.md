# VESC UART link restored — TX/RX swap found by operator

Run at: 20261001T070314Z (07:02 UTC). Battery in. ESP32: USB to the Orin plus UART to the VESC only (IMU, servo etc. unplugged by the operator).

## Isolation steps (05:00–05:40 UTC)
- State 2 (battery in, UART unplugged, VESC USB → Orin, notes/estop/vesc_probe.py read-only FW_VERSION/GET_VALUES):
  FW 6.06 hw '60', v_in 15.7 V, t_fet 23.7 C, fault 0. VESC healthy. (t_motor -75 C = no motor NTC.)
- State 3 (UART reconnected): VESC still answers over USB; the ESP32 still had telemetry_sequence 0 → fault is in the UART link.
- Operator: VESC UART baud 115200 (matches esp32_config.h VESC_UART_BAUD_RATE). Operator found TX/RX swapped and fixed it.

## Now (/laksa/state)
07:02:50 telemetry_fresh=true seq=8104 age=5 ms  v_in=15.6 V t_fet=33.8 C fault=0 erpm=-1
07:02:53 seq=8120 (+16 in 3 s ≈ 5 Hz = VESC_TELEMETRY_INTERVAL_MS 200)
07:02:56 seq=8135  age=5 ms
imu_available=false (IMU unplugged; expected). 0 ESP32 USB disconnects in 5 min.

## Verdict
The VESC↔ESP32 UART link is UP. Root cause of "car won't move": ESP32↔VESC TX/RX swapped. No VESC config or ESP32 firmware writes were made by the agent.
