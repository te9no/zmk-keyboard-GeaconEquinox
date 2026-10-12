# Equinox PMW motion / battery validation

## 2026-10-12: candidate, hardware verification pending

User reports continuous cursor movement after vibration, even after releasing
the ball. This is not yet reproduced in a captured CDC trace.

Reference inspected: efogdev/zmk-pmw3610-driver, zephyr-4.1,
`38105b4f09d6d5b94ef5a3073428719e3c356af1`.
Its startup/rest sample suppression and inactivity anti-warp filter address
transient jumps. Equinox forces awake and the reported symptom is continuous;
blindly adding that threshold could hide the fault and discard legitimate input.
The reference's anti-warp threshold is also positive-only (x > limit || y > limit).
No code was copied from that driver.

The pinned cormoran driver decoded deltas without checking the Motion MOT bit.
The Equinox build now rejects MOT-clear frames and all-0xff bus responses and
clears unreported deltas. A rate-limited CDC trace records motion flags, SQUAL
and signed raw deltas, including rejected frames. Valid continuous sensor
motion is deliberately not suppressed; surface, wiring, power, or split/HID
issues may require a different fix after tracing.

`scripts/patch_pmw_guard.py` generates a build-local variant of the pinned driver
and fails on source hash mismatch. It does not edit the shared west checkout or
remove Studio RPC. Re-review it when upgrading the upstream dependency.

The previous generated DTS used XIAO's onboard AIN7 LiPo divider and power GPIO.
The user confirmed Equinox instead uses Polaris's D0 / P0.02 / AIN0 external Bat
input. Both halves now use 1M/470k division (battery mV = ADC mV * 1470 / 470),
no switched measurement GPIO, and the same single-cell NiMH percentage table.
Example: 425 mV at D0 represents approximately 1329 mV at the battery.

Hardware checks before merge:

- CDC on the right: capture resting, normal movement, vibration, and subsequent
  hands-off intervals. Distinguish repeated raw motion from a host-only repeat.
- Check ordinary slow/fast movement and both signs; no unintended axis changes.
- Measure D0 and battery voltage, compare reported voltage/percentage on both
  halves (allow the battery reporting interval to elapse).
- Check Studio diagnostics and split connectivity remain functional.

No flash, merge, or upstream PR has been performed for this candidate.

Local validation: 21 host tests passed, including compilation/execution of the
injected motion gate with positive/negative valid samples, stale motion and
all-ones input. `just.sh --profile geacon-equinox build geacon_equinox` succeeded
for left/right US/JIS. All four generated DTS files contain AIN0, 470000/1470000,
the NiMH table, and no battery power GPIO. Right builds compile the generated
guarded source rather than the original compilation unit. CDC debug remains
enabled (`CONFIG_ZMK_LOG_LEVEL=4`). Hardware results are still pending.
