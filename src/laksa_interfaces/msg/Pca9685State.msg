# Provenance: production-branch layout (production/laksa-mainline @ 1f0db4f),
# the only branch that defines this message. `initialized` value to be confirmed
# at runtime by laksa_readonly_check.py (see A1a in orin_bringup_plan.md).
builtin_interfaces/Time stamp
bool initialized
bool responsive
bool configuration_matches
uint8 i2c_address
uint16 configured_pwm_frequency_hz
uint8 mode1
uint8 prescale
float32 last_successful_write_age_sec
float32 last_successful_read_age_sec
uint32 consecutive_i2c_errors
uint32 total_i2c_errors
int32 last_i2c_error_code
uint32 reinitialization_count
bool automatic_recovery_enabled
uint8 steering_pwm_channel
uint8 steering_command_deg
uint16 steering_pulse_us
uint16 steering_off_tick
