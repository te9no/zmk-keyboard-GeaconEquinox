"""Scoped bootloader handoff fix for the pinned Zephyr clock driver."""
import hashlib
import pathlib
import sys

source = pathlib.Path(sys.argv[1]).read_bytes()
if hashlib.sha256(source).hexdigest() != "c85ade09a43bd70a0b3b8b9714a1f6f9985dbb78e08d5b670b9f7495e5caa6ca":
    raise SystemExit("Unreviewed nRF clock driver; review boot clock patch before building")
needle = b"\tnrfx_err = nrfx_clock_init(clock_event_handler);"
assert source.count(needle) == 1
replacement = b"""	/* Discard the bootloader's HF event before nrfx enables its anomaly-201
	 * duplicate-event latch. Keep the clock running and preserve ownership. */
	nrf_clock_event_clear(NRF_CLOCK, NRF_CLOCK_EVENT_HFCLKSTARTED);
""" + needle
pathlib.Path(sys.argv[2]).write_bytes(source.replace(needle, replacement))
