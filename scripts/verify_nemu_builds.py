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
        assert conf['CONFIG_ZMK_CDC_ACM_BOOTLOADER_TRIGGER']=='y',name
        assert conf['CONFIG_UART_LINE_CTRL']=='y',name
        assert conf['CONFIG_RETENTION_BOOT_MODE']=='y',name
        assert conf['CONFIG_ZMK_BOOTMODE_MAGIC_VALUE_BOOTLOADER_TYPE_ADAFRUIT_NRF52']=='y',name
        assert node('nemu_bootloader_trigger').props['cdc-port'].val==node('equinox_nemu_boot_uart'),name
        cdc=[n for n in edt.nodes if n.status=='okay' and 'zephyr,cdc-acm-uart' in n.compats]
        assert len(cdc)==(2 if side=='dongle' else 1),(name,len(cdc))
        if side=='dongle':
            assert edt.chosen_node('zmk,studio-rpc-uart')!=node('equinox_nemu_boot_uart'),name
        assert conf.get('CONFIG_ZMK_BLE')!='y',name
        assert node('nemu_link_key_partition').regs[0].size==4096,name
        matrix=node('default_transform').props['map'].val
        assert len(matrix)==count and len(set(matrix))==count,name
        if reference is None: reference=matrix
        assert reference==matrix,name
        assert node('default_transform').props.get('col-offset').val == (8 if side=='right' else 0),name
        if side=='dongle':
            assert conf.get('CONFIG_EQUINOX_NEMU_STATUS_LED')!='y',name
            assert conf['CONFIG_ZMK_DYNAMIC_SETTINGS']=='y',name
            assert conf['CONFIG_ZMK_DYNAMIC_INPUT_PROCESSOR']=='y',name
            assert conf['CONFIG_ZMK_STUDIO']=='y',name
            for feature in ['COMBO', 'ENCODER_RUNTIME', 'MACRO', 'TAP_DANCE']:
                assert conf['CONFIG_ZMK_DYNAMIC_'+feature]=='y',(name,feature)
            assert conf['CONFIG_NEMU_LINK_FULL_SCAN']=='y',name
            assert conf.get('CONFIG_ZMK_DYNAMIC_BLE_PROFILE')!='y',name
            assert conf.get('CONFIG_ZMK_NEMU_LINK_STUDIO_ENDPOINT')!='y',name
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
            assert len(scan)==1 and len(scan[0]['settings'])==81,name
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
            assert 'sekigon,remote-hires-dial' in node('pat9125').compats,name
            assert 'device' not in node('right_tb_split').props,name
            processor=edt.get_node('/right_tb_listener').props['input-processors'].val
            assert processor[-1].controller==node('nemu_pointer'),name
            expected=2 if layout=='us' else 7
            assert next(iter(processor[0].data.values()))==expected,(name,processor[0].data)
            assert not node('nemu_pointer').props['aml-enabled'].val,name
            assert node('nemu_pointer').props['shift-point-0'].val==0,name
            assert len(edt.get_node('/sensors').props['sensors'].val)==1,name
        else:
            assert conf['CONFIG_ZMK_NEMU_LINK_PERIPHERAL_ID']==('0' if side=='left' else '1'),name
            assert conf.get('CONFIG_ZMK_SPLIT_ROLE_CENTRAL')!='y',name
            for feature in ['COMBO','ENCODER_RUNTIME','MACRO','TAP_DANCE','BLE_PROFILE']:
                assert conf.get('CONFIG_ZMK_DYNAMIC_'+feature)!='y',(name,feature)
            assert conf.get('CONFIG_NEMU_LINK_FULL_SCAN')!='y',name
            assert conf['CONFIG_ZMK_NEMU_LINK_KEY_PROVISION_USB']=='y',name
            assert conf['CONFIG_EQUINOX_NEMU_NIMH']=='y',name
            assert conf['CONFIG_EQUINOX_NEMU_STATUS_LED']=='y',name
            assert conf['CONFIG_WS2812_STRIP_SPI']=='y',name
            assert node('equinox_status_strip').props['chain-length'].val==4,name
            gate=node('status_power').props['gpios'].val[0]
            assert gate.controller==node('gpio1') and gate.data['pin']==13,name
            assert gate.data['flags'] & 1,name  # active-low power gate
            assert not any(n.name=='led_power_off' for n in edt.nodes),name
            assert node('code_partition').regs[0].addr==0x27000,name
            assert node('code_partition').regs[0].size==0xc4000,name
            assert node('nemu_link_key_partition').regs[0].addr==0xeb000,name
            levels=node('vbatt').props['mv-to-pct-thresholds'].val
            assert len(levels)==11 and all(a<b for a,b in zip(levels,levels[1:])),name
            if side=='left':
                assert node('right_tb_split').status=='disabled',name
                assert 'sekigon,hires-dial' in node('pat9125').compats,name
                assert edt.get_node('/sensors').props['sensors'].val==[node('pat9125')],name
            else:
                assert node('right_tb_split').props['device'].val==node('trackball'),name
                assert edt.get_node('/nemu_tb_listener').props['device'].val==node('trackball'),name
        print(name+': PASS')
