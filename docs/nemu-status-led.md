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

Layer animation definitions are restored, but receiver-side layer changes are not
relayed to the halves in nemu-link mode. Local BLE layer indicators retain the
original behavior. No receiver-layer indication is claimed by this restoration.

Validation: all six US/JIS production targets and their compiled configuration checks
passed. All 26 unit tests passed.
Both JIS halves were flashed after checking their hardware serial numbers and
returned as CDC devices. Visible LED behavior and input coexistence have not yet
been verified on this restored-LED build.
