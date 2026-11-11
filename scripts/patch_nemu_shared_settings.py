"""Preserve independent keymaps while allowing synced shared settings at mode return."""
from pathlib import Path
import hashlib,sys
HASHES = {'studio_zmk.c': '7853652bd7693e5ee0cd7072ffdfbf8357908da272a0c6c679debc1654e9853b', 'link_esb.c': 'a5ba01e2330da64985b03c44caeeace6acf5d8dc1919954bc470528e2c5f38e2'}
source, dest = map(Path, sys.argv[1:])
s=source.read_text()
if hashlib.sha256(source.read_bytes()).hexdigest()!=HASHES[source.name]:
    raise SystemExit('Review nemu shared-settings adapter for changed upstream source')
if source.name=='studio_zmk.c':
    # Equinox keeps receiver and BLE keymaps local; only shared groups synchronize.
    gate = '    if (ready && !dirty && !rx.started && !tx_active() && now >= next_offer) {'
    assert s.count(gate) == 1
    s = s.replace(gate, """    next_offer = UINT64_MAX;
    tx.phase = NEMU_LINK_STUDIO_TX_FAILED;
""" + gate)
    call = """                response_pending =
                    nemu_link_studio_stream_receive(&rx, &p, &live, nemu_link_studio_schema(), now,
                                                    apply_record, commit_received, NULL, &response);"""
    assert s.count(call) == 1
    s = s.replace(call, """                response = (struct nemu_link_studio_packet){
                    .kind = NEMU_LINK_STUDIO_ERROR, .transaction = p.transaction,
                    .length = 2, .data = {NEMU_LINK_STUDIO_STALE, p.kind},
                };
                response_pending = true;""")
    gate = 'dynamic_settings_shared_group_count() && atomic_get(&synchronized) &&'
    assert s.count(gate) == 1
    s = s.replace(gate, """dynamic_settings_shared_group_count() &&
        peer_shared_contract_known && peer_shared_contract_matches &&""")
    s += """
/* Different keymap contracts remain incompatible; this only gates mode return. */
bool equinox_shared_settings_ready_for_ble(void) {
#if IS_ENABLED(CONFIG_ZMK_NEMU_LINK_STUDIO_SHARED_SETTINGS)
    return peer_shared_contract_known && peer_shared_contract_matches &&
           shared_ready && shared_synchronized &&
           !atomic_get(&shared_save_pending) && !shared_tx_active() && !shared_rx_active();
#else
    return false;
#endif
}
"""
else:
    marker='if (!nemu_link_studio_synced() || nemu_link_studio_radio_busy()) {'
    assert s.count(marker)==1
    s=s.replace(marker,'if ((!nemu_link_studio_synced() && !equinox_shared_settings_ready_for_ble()) || nemu_link_studio_radio_busy()) {')
    # bool is available after the normal includes; declare inside the guarded function.
    s=s.replace('    if ((!nemu_link_studio_synced()', '    extern bool equinox_shared_settings_ready_for_ble(void);\n    if ((!nemu_link_studio_synced()')
dest.write_text(s)
