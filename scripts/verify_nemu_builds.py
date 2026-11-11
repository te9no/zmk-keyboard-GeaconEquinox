#!/usr/bin/env python3
"""Validate the compiled DTS/config of every receiver and keyboard variant."""
import argparse
import json
import pickle
from pathlib import Path
import sys

parser=argparse.ArgumentParser()
parser.add_argument('workspace',type=Path)
parser.add_argument('--target', default='all')
args=parser.parse_args()
w=args.workspace.resolve()
sys.path.insert(0,str(w/'zephyr/scripts/dts/python-devicetree/src'))

def cfg(path):
    return dict(line.split('=',1) for line in path.read_text().splitlines() if line.startswith('CONFIG_'))

for layout,count in [('us',63),('jis',64)]:
    reference=None
    for side in ['left','right','dongle']:
        name=f'equinox_nemu_{side}_{layout}'
        if args.target not in ('all', name):
            continue
        build=w/'build'/name/'zephyr'
        conf=cfg(build/'.config')
        with (build/'edt.pickle').open('rb') as f: edt=pickle.load(f)
        def node(label): return edt.label2node[label]
        assert conf['CONFIG_ZMK_NEMU_LINK']=='y',name
        if side=='right':
            assert int(conf['CONFIG_INPUT_THREAD_STACK_SIZE']) >= 2048,name
        assert conf['CONFIG_ZMK_CDC_ACM_BOOTLOADER_TRIGGER']=='y',name
        assert conf['CONFIG_UART_LINE_CTRL']=='y',name
        assert conf['CONFIG_RETENTION_BOOT_MODE']=='y',name
        assert conf['CONFIG_ZMK_BOOTMODE_MAGIC_VALUE_BOOTLOADER_TYPE_ADAFRUIT_NRF52']=='y',name
        assert node('nemu_bootloader_trigger').props['cdc-port'].val==node('equinox_nemu_boot_uart'),name
        cdc=[n for n in edt.nodes if n.status=='okay' and 'zephyr,cdc-acm-uart' in n.compats]
        assert len(cdc)==(1 if side=='right' else 2),(name,len(cdc))
        if side!='right':
            assert edt.chosen_node('zmk,studio-rpc-uart')!=node('equinox_nemu_boot_uart'),name
        assert (conf.get('CONFIG_ZMK_BLE')=='y')==(side!='dongle'),name
        assert conf['CONFIG_ZMK_NEMU_LINK_MODE_CHORD']=='y',name
        assert node('eq_layer').status == 'okay', name
        assert 'te9no,behavior-nemu-layer-led' in node('eq_layer').compats, name
        assert conf.get('CONFIG_ZMK_NEMU_LINK_STUDIO_SOURCE')=='0',name
        mode=edt.get_node('/nemu_mode_keys')
        assert mode.props['source-0-switch-positions'].val==[1,2,3],name
        assert mode.props['source-1-switch-positions'].val==[6,7,8],name
        if side!='dongle':
            assert conf['CONFIG_ZMK_NEMU_LINK_MODE_SWITCH']=='y',name
            assert conf['CONFIG_ZMK_NEMU_LINK_BOOT_ESB']=='y',name
            assert conf['CONFIG_BT_LL_SW_SPLIT']=='y',name
            assert conf['CONFIG_ZMK_SPLIT_BLE']=='y',name
            assert conf.get('CONFIG_ZMK_NEMU_LINK_FIXED_ESB')!='y',name
        assert node('nemu_link_key_partition').regs[0].size==4096,name
        matrix=node('default_transform').props['map'].val
        assert len(matrix)==count and len(set(matrix))==count,name
        assert all((matrix[i] & 0xff)<8 for i in [1,2,3]),name
        assert all((matrix[i] & 0xff)>=8 for i in [6,7,8]),name
        if reference is None: reference=matrix
        assert reference==matrix,name
        assert node('default_transform').props.get('col-offset').val == (8 if side=='right' else 0),name
        if side!='right':
            if side=='dongle':
                assert conf.get('CONFIG_EQUINOX_NEMU_STATUS_LED')!='y',name
            assert conf['CONFIG_ZMK_DYNAMIC_SETTINGS']=='y',name
            assert conf['CONFIG_ZMK_DYNAMIC_INPUT_PROCESSOR']=='y',name
            assert conf['CONFIG_ZMK_STUDIO']=='y',name
            for feature in ['COMBO', 'ENCODER_RUNTIME', 'MACRO', 'TAP_DANCE']:
                assert conf['CONFIG_ZMK_DYNAMIC_'+feature]=='y',(name,feature)
            assert (conf.get('CONFIG_NEMU_LINK_FULL_SCAN')=='y')==(side=='dongle'),name
            assert (conf.get('CONFIG_ZMK_DYNAMIC_BLE_PROFILE')=='y')==(side=='left'),name
            assert conf.get('CONFIG_ZMK_NEMU_LINK_STUDIO_ENDPOINT')=='y',name
            assert conf.get('CONFIG_ZMK_NEMU_LINK_STUDIO_SYNC')=='y',name
            assert conf.get('CONFIG_ZMK_NEMU_LINK_STUDIO_SHARED_SETTINGS')=='y',name
            schema_path=build.parent/'modules/zmk-feature-dynamic-settings/generated/settings-schema.json'
            groups=json.loads(schema_path.read_text())['groups']
            for module in ['combo', 'macro', 'tap-dance']:
                slots=[g for g in groups if g['module']==module and g['name']=='slot']
                assert len(slots)==4,(name,module,len(slots))
                assert all(not g['proxy'] and g['target_role']=='owner' for g in slots),name
            assignments=[g for g in groups if g['module']=='encoder' and g['name']=='assignment']
            assert len(assignments)==len(edt.get_node('/keymap').children),name
            assert all(not g['proxy'] for g in assignments),name
            scan=[g for g in groups if g['module']=='nemu-link-scan']
            if side=='dongle':
                assert len(scan)==1 and len(scan[0]['settings'])==81,name
            else:
                assert not scan,name
                assert any(g['module']=='ble' for g in groups),name
            source=node('equinox_encoder_source')
            assert source.props['sensor'].val==node('pat9125'),name
            assert source.props['input-mode'].val=='angle',name
            assert source.props['sensor-index'].val==0,name
            # Empty runtime records must leave existing dial defaults available.
            for layer,behavior,params in [
                ('default_layer','hires_dial_scroll',[10,1]),
                ('function_layer','hires_dial_radial_controller',[1,1]),
                ('dial_layer','hires_dial_radial_controller',[1,1])]:
                binding=edt.get_node('/keymap/'+layer).props['sensor-bindings'].val[0]
                assert binding.controller==node(behavior),name
                assert list(binding.data.values())==params,name
            assert conf['CONFIG_ZMK_SPLIT_ROLE_CENTRAL']=='y',name
            if side=='dongle':
                assert 'sekigon,remote-hires-dial' in node('pat9125').compats,name
            assert 'device' not in node('right_tb_split').props,name
            processor=edt.get_node('/right_tb_listener').props['input-processors'].val
            assert processor[-1].controller==node('nemu_pointer'),name
            expected=2 if layout=='us' else 7
            assert next(iter(processor[0].data.values()))==expected,(name,processor[0].data)
            assert not node('nemu_pointer').props['aml-enabled'].val,name
            assert node('nemu_pointer').props['shift-point-0'].val==0,name
            assert len(edt.get_node('/sensors').props['sensors'].val)==1,name
        if side!='dongle':
            assert conf['CONFIG_ZMK_NEMU_LINK_PERIPHERAL_ID']==('0' if side=='left' else '1'),name
            assert (conf.get('CONFIG_ZMK_SPLIT_ROLE_CENTRAL')=='y')==(side=='left'),name
            if side=='right':
                for feature in ['COMBO','ENCODER_RUNTIME','MACRO','TAP_DANCE','BLE_PROFILE']:
                    assert conf.get('CONFIG_ZMK_DYNAMIC_'+feature)!='y',(name,feature)
            assert conf.get('CONFIG_NEMU_LINK_FULL_SCAN')!='y',name
            if side=='right':
                assert conf['CONFIG_ZMK_NEMU_LINK_KEY_PROVISION_USB']=='y',name
            else:
                assert conf['CONFIG_ZMK_USB']=='y',name  # provisioning shares keyboard HID
            assert conf['CONFIG_EQUINOX_NEMU_NIMH']=='y',name
            assert conf['CONFIG_EQUINOX_NEMU_STATUS_LED']=='y',name
            assert conf['CONFIG_ZMK_ANIMATION']=='y',name
            assert conf['CONFIG_RGBLED_WIDGET']=='y',name
            assert conf['CONFIG_ZMK_DRIVER_EXT_POWER_TRANSIENT']=='y',name
            assert conf['CONFIG_WS2812_STRIP_SPI']=='y',name
            assert node('led_strip').props['chain-length'].val==4,name
            gate=node('led_power').props['control-gpios'].val[0]
            assert gate.controller==node('gpio1') and gate.data['pin']==13,name
            assert gate.data['flags'] & 1,name  # active-low power gate
            assert not any(n.name=='led_power_off' for n in edt.nodes),name
            assert node('code_partition').regs[0].addr==0x27000,name
            assert node('code_partition').regs[0].size==0xc4000,name
            assert node('nemu_link_key_partition').regs[0].addr==0xeb000,name
            levels=node('vbatt').props['mv-to-pct-thresholds'].val
            assert len(levels)==11 and all(a<b for a,b in zip(levels,levels[1:])),name
            if side=='left':
                assert node('right_tb_split').status=='okay',name
                assert 'sekigon,hires-dial' in node('pat9125').compats,name
                assert edt.get_node('/sensors').props['sensors'].val==[node('pat9125')],name
            else:
                assert node('right_tb_split').props['device'].val==node('trackball'),name
                assert edt.get_node('/nemu_tb_listener').props['device'].val==node('trackball'),name
        print(name+': PASS')
