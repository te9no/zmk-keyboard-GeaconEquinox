"""Do not forward BLE central events into an inactive ESB peripheral transport."""
import hashlib
import pathlib
import sys
source = pathlib.Path(sys.argv[1]).read_bytes()
if hashlib.sha256(source).hexdigest() != "f1a9e10f72674862f355c2a890e6b2418fd90a15158a2d97a1513cecbfca4db7":
    raise SystemExit("Unreviewed split peripheral source; review mode guard")
needle = b"int split_peripheral_listener(const zmk_event_t *eh) {"
assert source.count(needle) == 1
replacement = b"""#include <zmk/nemu_link/control.h>

int split_peripheral_listener(const zmk_event_t *eh) {
    /* This listener is also linked into a switchable BLE central. Its local
     * keymap owns events in BLE mode; ESB forwarding belongs to ESB mode only. */
    if (!zmk_nemu_link_owns_radio()) {
        return ZMK_EV_EVENT_BUBBLE;
    }
"""
pathlib.Path(sys.argv[2]).write_bytes(source.replace(needle, replacement))
