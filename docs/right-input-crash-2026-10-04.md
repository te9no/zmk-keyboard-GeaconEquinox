# Right input crash investigation (2026-10-04)

Status: user reports stable operation with enlarged stacks on diagnostic US firmware.
The precise root cause remains unresolved; production firmware acceptance is pending.

- Original right US firmware repeatedly rebooted during input. Stored incident type 1,
  reason 2 means fatal stack-check failure (not a freeze timeout).
- Diagnostic build enabled thread names and printed existing watchdog records without
  deleting settings. Incidents 12–16 identify thread `input`, PC `0x31564`.
  That diagnostic ELF resolves the PC to `zmk_split_bt_send_relay_event`, service.c:521.
  Addresses must be interpreted with the matching ELF, not subsequent builds.
- Increased right `CONFIG_INPUT_THREAD_STACK_SIZE` from 1024 to 4096. Build and 16
  configuration tests passed; owner still reports occasional failures. Do not mark fixed.
- A later capture reached uptime 157640 ms with split connected and no observed reboot
  during that capture. This does not disprove the intermittent report.
- Incident storage had reached its 16-record limit. Diagnostic-only capacity increased
  to 32; existing records 1–16 preserved. Right US flashed via COM56 / I:.
- Latest diagnostic target: `geacon_equinox_right_us_diagnostics`, built with
  `./just.sh --profile geacon-equinox build geacon_equinox_right_us_diagnostics`.
  Generated config confirms input stack 4096 and incident capacity 32.
- Left firmware and pairing settings were not changed in this diagnostic update.

Next: reproduce while pressing right keys / moving the ball; inspect new records
17 onwards. Relay queue-full retry is recursive in the pinned ZMK source, but this
has not been established as the cause of the remaining intermittent failure.

## Studio connection / Central investigation

After the owner identified Studio connection as a trigger, a separate left US
diagnostic target was built and flashed (COM61 / H:), preserving settings.
It reads watchdog records without clearing them. Six pre-existing fatal records
report reason=2, thread=sysworkq (uptimes 300, 14, 6, 11, 17, 19 seconds).
PC=0x68d1fbfd and LR=0x173a0ac0 are not usable code addresses, so the precise
call site is unconfirmed. This is separate from the right input-thread fault.
At initial diagnosis the left system workqueue stack was 2048 bytes.
Evidence: local equinox-left-crash-diagnostics.log (2026-10-04).

The next trial increases CONFIG_SYSTEM_WORKQUEUE_STACK_SIZE to 4096 on the left.
The left US diagnostic build passed, generated config verified, 17 configuration
tests passed, and the artifact was flashed via COM61 / H:. Existing incidents
1–8 are the pre-trial baseline (all sysworkq stack-check failures). Settings
were not erased. Studio connection and repeated input acceptance remain pending;
do not treat the stack increase as a confirmed complete fix.

## Stable diagnostic trial and production cleanup

Owner reported stable operation after Studio connection. The measured Central
sysworkq high-water usage increased from 640 to 1640 bytes; no new crash beyond
the eight-record baseline, at uptime approximately 18 minutes. This measurement
does not prove which earlier call path exhausted/corrupted the original stack.

Normal build.yaml contains only left/right US/JIS. The optional crash snippet
is disabled by default: no fatal-handler wrapper, extra crash thread, or 32-slot
override is linked into normal builds. Existing CDC logging and watchdog remain.
Normal builds retain left sysworkq=4096 and right input=4096. Devices remain on
diagnostic firmware until a separately verified production flash.

The owner subsequently confirmed that the DYA Studio runtime combo works.
The additional combo-readout diagnostic was built but not flashed. No combo
behavior/settings fix was applied. Cold-boot persistence is not separately
confirmed by this report.
