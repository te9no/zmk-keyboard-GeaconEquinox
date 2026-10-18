# Equinox PMW motion / battery validation

## 2026-10-15: idle/activity recovery fix, initial hardware confirmation

Right CDC COM56 (USB serial `3D61E124761EF67C`) captured activity wake at
17:26:29, PERFORMANCE changing `0x01` to `0xf1`, followed by repeated raw
Y deltas around -519/-520 at roughly 8 ms intervals. This localizes the
observed output to the PMW read/decode path, not solely host HID persistence.
It does not yet distinguish sensor state from SPI sampling corruption.

The reference efog commit above writes normal-run PERFORMANCE `0x00` by
default, unlike the pinned cormoran activity handler's forced-run upper bits.
The keyboard-local patch now uses `0x00` for this path as a controlled
comparison; Studio frame capture's separate forced-run procedure is unchanged.
MOT/all-ones guards, direction, keymap, CPI and shared dependencies are unchanged.

22 host tests passed. Right US built with `just.sh --profile geacon-equinox
build geacon_equinox_right_us` and was flashed via the verified right-hand
1200-baud trigger and matching XIAO bootloader serial. CDC confirmed ready=1,
init_error=0 and split_connected=1; idle PERFORMANCE reads back as `0x00`.
Follow-up CDC captured typing at uptime 103–106 seconds without the earlier
continuous PMW deltas; sensor initialization and split connectivity remained
healthy through 120 seconds. Asked to check idle-to-typing recurrence and normal
ball operation, the user replied "大丈夫そう". This is initial practical
confirmation, not a guarantee against long-duration recurrence. The precise
sensor-internal mechanism remains unproven; the evidence supports avoiding the
forced-run transition as the effective change on this hardware.
Right JIS also builds successfully; JIS hardware is not separately tested.
No upstream changes, push or release has been performed.

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
