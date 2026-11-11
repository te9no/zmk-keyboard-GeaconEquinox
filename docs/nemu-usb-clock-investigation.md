# nemu-link USB / clock investigation (2026-11-11)

## Observed failure

On the JIS right XIAO nRF52840, USB device selection was intermittent. A
separate reproducible startup failure was captured with CDC diagnostics:
`NRF_CCM self-test failed: -116` every approximately 105 ms, with no right
traffic at the receiver. Instrumentation located the timeout in the HF clock
request, before encryption. The oscillator was already running, but the
onoff manager remained in TO_ON with zero references.

At boot an HFCLKSTARTED event was delivered while Zephyr's HF state was OFF.
The nrfx anomaly-201 duplicate-event latch records this event. A later real
HF start then lacks its completion callback. In the failed run, counters
recorded one HF request, one earlier HF event, and zero ready callbacks.

## Scoped change

Clear the inherited HFCLKSTARTED event immediately before nrfx_clock_init in
the pinned Zephyr driver. Keep the oscillator running and retain normal
onoff ownership and all encryption checks. Apply only to nRF52840 nemu-link
images. The nRF52833 receiver and ordinary ZMK builds are excluded.

The script verifies the exact input driver SHA-256 and substitutes a generated
build-tree source; the shared dependency checkout is not modified.

## Evidence and limits

- Before the change: repeated HF request timeouts and no right radio traffic.
- After the driver-initialization change: authenticated peer link, accepted
  data, radio transmissions completing, and no HF timeout in captured logs.
- Final scoped patch plus diagnostic logging: 30 consecutive HID feature GETs
  succeeded; maximum observed round-trip approximately 4 ms.
- An alternative PRE_KERNEL_1 priority-0 standalone cleanup was tried and
  removed after a device-descriptor failure. It is not the delivered fix.
- USB port ownership by Studio can prevent CDC bootloader access; disconnect
  Studio before flashing. This is distinct from a missing USB device.
- Short tests do not prove that all intermittent Studio disappearance is
  resolved. Cold power cycles, repeated Studio selection, and extended use
  remain hardware acceptance tests.

Private diagnostic logs reside in work/equinox-nemu-diagnostics. No keys or
settings were erased. Published release assets have not been replaced.

## Left dial / unwanted peer keymap synchronization

The left PAT9125 responds at 0x75 with product ID 31:91, device ready and
initialization result zero. This does not by itself verify rotation/scroll.

The receiver configuration incorrectly enabled NEMU_LINK_STUDIO_ENDPOINT
with STUDIO_SOURCE=0, while both keyboards are split peripherals without peer
Studio endpoints. Left-side logs showed repeated application ACK timeouts,
re-authentication, and rejected 0x80 Studio frames. Disabling the CCM/RADIO
overlap optimization did not resolve this and was reverted.

Following https://nemu-link-studio.pages.dev/docs, the receiver now uses local
Studio/RPC and Dynamic Settings without peer keymap synchronization. The
endpoint is disabled and the source override removed. After flashing this
receiver configuration, approximately 25 seconds of concurrent left/receiver
logs showed an established link, zero data rejections, and no repeated ACK
timeouts. Initial authentication retries are distinct from sustained failure.

Rotation and right trackball movement remain unverified pending user input.
Both keyboards and the receiver currently have temporary diagnostic logging;
restore normal images after the movement tests. Diagnostic PMW readiness now
builds without BLE split dependencies and reports unavailable connection
status as -1 rather than claiming a connected peer.
