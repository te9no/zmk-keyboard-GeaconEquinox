# nemu-link status LEDs

Both keyboard halves drive their own four WS2812 LEDs on SPI3/P0.29.
P1.13 is the active-low supply gate. The former always-off GPIO hog is removed.
The receiver has no such strip and does not enable this driver.

At boot and when activity returns from idle, a 1.6-second dim rainbow animation
is followed by 1.6 seconds of local battery indication on all four LEDs:
blue at 65% or above, green at 25–64%, red below 25%. Amber means that no battery
report has arrived yet. These are local readings, not the other half's battery.
The strip then goes black and its supply is disabled. Idle also requests immediate
shutdown; there is no permanent animation or periodic idle polling.

SPI transfers and the one-millisecond power stabilization delay run on a dedicated
priority-10 work queue, never in the input/event callback. No extra LED modules
are imported and the existing radio, keymap and pointing settings are preserved.
This first version does not display receiver layers or claim radio connectivity.
Physical brightness/color and input coexistence still require hardware validation.

Dynamic module inventory is maintained in [nemu-link.md](nemu-link.md).

Validation: all six US/JIS keyboard/receiver production builds passed, including
compiled-DTS checks for strip length, SPI driver, active-low gate and removal of
the competing GPIO hog. The existing 26 unit tests passed. Both JIS halves were
flashed after matching their hardware serial numbers and reappeared as CDC and
vendor HID devices. Visible illumination and motion remain user-confirmation items.
