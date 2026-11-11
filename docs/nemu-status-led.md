# nemu-link LED restoration

The keyboard halves reuse `GeaconEquinox_led.dtsi`, including the original
four-pixel strip, active-low P1.13 power gate, animation controller and XIAO RGB LED.
The receiver does not enable these hardware drivers.

- Boot: battery for 1 second, black for 0.2 seconds, endpoint for 1 second.
- Return from idle: local battery indication for 1 second.
- Battery colors: green/high, yellow/middle, red/low (original animation settings).
- USB-powered operation: original endpoint and rainbow animations.
- Battery-powered operation: original empty background animation.
- Original animation controls and XIAO battery/connection indicators are restored.
- Idle and inactive animation power management use the original transient power driver.

Explicit mode switches retain yellow transition, blue BLE, green nemu-link and
red failure indications. Completion colors indicate mode selection, not confirmed
peer connectivity. Successful boot selection does not interrupt the boot sequence.
The original endpoint animation and internal RGB connection indication read the
nemu-link peripheral phase when that transport owns the radio. The status is sampled
when each indication runs; it is not a continuously refreshed connection monitor.

Rendering runs on a dedicated priority-10 queue with a 4096-byte stack. Mode
callbacks only enqueue their notifications. The right input stack remains 2048
bytes. Pinned upstream LED sources are left unchanged; SHA-checked generated
adapters provide the queue and endpoint changes during the build.

Receiver layer changes are relayed to both halves through the authenticated split
behavior channel. Each half displays the highest active layer on all four LEDs for 1.5 seconds:
Def blue, Fnc cyan, Mouse red, Scr white, BT orange, Dial purple, Mac green,
MacDial magenta. BLE retains its original per-pixel layer map.
Mode-switch indications have priority over layer indications.

The receiver coalesces updates to the latest layer mask on a priority-10 queue.
Typing also refreshes state at most once every two seconds, allowing reconnection
to recover the display without idle polling. There is no per-pointer-packet traffic.
BLE mode ignores receiver layer commands and keeps the original local behavior.
The receiver and both halves must run this version; receiver-only or half-only
updates do not provide this feature. Delivery is best effort through the existing
transport; a quiet reconnection is reflected on the next layer change or typing.

Validation: all six US/JIS production targets and their compiled configuration checks
passed. All 28 unit tests passed, including host execution of the C relay callbacks.
The generated renderer also passed an eight-layer color, BLE mapping and frame
countdown test.
The JIS receiver and both halves were flashed after checking their device
identities and returned as CDC devices. Visible LED behavior and input coexistence have not yet
been verified on this restored-LED build.

Receiver-layer display is pending hardware verification.
