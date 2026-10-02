from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EquinoxConfigTest(unittest.TestCase):
    def test_layouts_have_unique_matrix_positions_and_matching_keymaps(self):
        for layout, count in [('US', 63), ('JIS', 64)]:
            with self.subTest(layout=layout):
                overlay = (ROOT / f'snippets/equinox-{layout.lower()}/equinox-{layout.lower()}.overlay').read_text()
                positions = re.findall(r'RC\((\d+),\s*(\d+)\)', overlay)
                self.assertEqual(len(positions), count)
                self.assertEqual(len(set(positions)), count)
                self.assertEqual(sum(int(c) < 8 for _, c in positions), 29)
                for row, col in positions:
                    self.assertNotEqual(int(row), int(col) % 8)
                self.assertEqual(overlay.count('&key_physical_attrs'), count)
                keymap = (ROOT / f'config/GeaconEquinox_{layout}.keymap').read_text()
                bindings = re.findall(r'bindings\s*=\s*<([^>]+)>', keymap)
                self.assertEqual(len(bindings), 6)
                self.assertTrue(all(b.count('&') == count for b in bindings))

    def test_jis_adds_one_position(self):
        def positions(layout):
            text = (ROOT / f'snippets/equinox-{layout}/equinox-{layout}.overlay').read_text()
            return set(re.findall(r'RC\((\d+),\s*(\d+)\)', text))
        self.assertEqual(positions('jis') - positions('us'), {('2', '13')})
        self.assertFalse(positions('us') - positions('jis'))

    def test_layout_shift_is_available_in_both_layouts(self):
        for layout in ('US', 'JIS'):
            text = (ROOT / f'config/GeaconEquinox_{layout}.keymap').read_text()
            self.assertIn('#include "layout_shift.dtsi"', text)
            self.assertIn('compatible = "zmk,behavior-layout-shift-key-press"', text)
            self.assertEqual(text.count('&tog_ls'), 1)

    def test_schematic_scan_pins(self):
        text = (ROOT / 'boards/shields/GeaconEquinox/GeaconEquinox.dtsi').read_text()
        pins = re.findall(r'<&gpio(\d) (\d+) GPIO_ACTIVE_LOW>', text)
        self.assertEqual(pins, [('0', '28'), ('0', '15'), ('0', '19'),
                               ('1', '1'), ('0', '9'), ('0', '10'),
                               ('1', '3'), ('1', '5')])

    def test_led_wiring_and_exclusive_power_owner(self):
        shield = ROOT / 'boards/shields/GeaconEquinox'
        led = (shield / 'GeaconEquinox_led.dtsi').read_text()
        common = (shield / 'GeaconEquinox.dtsi').read_text()
        self.assertIn('#include "GeaconEquinox_led.dtsi"', common)
        self.assertNotIn('led_power_off', common)
        self.assertIn('control-gpios = <&gpio1 13 GPIO_ACTIVE_LOW>', led)
        self.assertEqual(led.count('NRF_PSEL(SPIM_MOSI, 0, 29)'), 2)
        self.assertIn('chain-length = <4>', led)
        self.assertIn('battery-animations = <&empty_animation>', led)
        for side in ('left', 'right'):
            conf = (shield / f'geacon_equinox_{side}.conf').read_text()
            self.assertIn('CONFIG_ZMK_ANIMATION=y', conf)
            self.assertIn('CONFIG_RGBLED_WIDGET=y', conf)

    def test_cdc_debug_configuration(self):
        conf = (ROOT / 'snippets/equinox-cdc/equinox-cdc.conf').read_text()
        for setting in ('CONFIG_ZMK_USB_LOGGING=y', 'CONFIG_ZMK_LOG_LEVEL_DBG=y',
                        'CONFIG_LOG_MODE_DEFERRED=y', 'CONFIG_LOG_BUFFER_SIZE=8192',
                        'CONFIG_USB_CDC_ACM_LOG_LEVEL_OFF=y', 'CONFIG_USB_DRIVER_LOG_LEVEL_OFF=y'):
            self.assertIn(setting, conf)
        right = (ROOT / 'boards/shields/GeaconEquinox/geacon_equinox_right.conf').read_text()
        self.assertIn('CONFIG_PMW3610_LOG_LEVEL_DBG=y', right)
        self.assertIn('CONFIG_SPI_THREE_WIRE_GPIO_LOG_LEVEL_DBG=y', right)

    def test_pat_reference_driver_and_read_only_diagnostics(self):
        shield = ROOT / 'boards/shields/GeaconEquinox'
        conf = (shield / 'geacon_equinox_left.conf').read_text()
        overlay = (shield / 'geacon_equinox_left.overlay').read_text()
        self.assertIn('CONFIG_ZMK_HIRES_DIAL=y', conf)
        self.assertNotIn('CONFIG_PAT9125=y', conf)
        self.assertNotIn('CONFIG_INPUT_PAT912X=y', conf)
        self.assertIn('compatible = "sekigon,hires-dial"', overlay)
        self.assertIn('pat9125: pat9125@79', overlay)
        self.assertIn('reg = <0x79>', overlay)
        address_hog = re.search(r'pat_address\s*\{([^}]+)', overlay).group(1)
        self.assertIn('input;', address_hog)
        self.assertNotIn('output-low;', address_hog)
        self.assertNotIn('zephyr,deferred-init', overlay)
        diag = (ROOT / 'src/pat_diagnostics.c').read_text()
        self.assertNotIn('device_init(pat)', diag)
        self.assertNotIn('i2c_reg_write', diag)

    def test_fn_enter_dial_button_preserves_base_enter(self):
        for layout in ('US', 'JIS'):
            text = (ROOT / f'config/GeaconEquinox_{layout}.keymap').read_text()
            base = re.search(r'default_layer\s*\{.*?bindings\s*=\s*<([^>]+)>', text, re.S).group(1)
            fn = re.search(r'function_layer\s*\{.*?bindings\s*=\s*<([^>]+)>', text, re.S).group(1)
            base_bindings = [b.strip() for b in re.findall(r'&\w+[^&]*', base)]
            fn_bindings = [b.strip() for b in re.findall(r'&\w+[^&]*', fn)]
            enter_binding = '&kp ENTER' if layout == 'US' else '&lt 4 ENTER'
            enter_position = base_bindings.index(enter_binding)
            self.assertEqual(fn_bindings[enter_position], '&dial_open')
            self.assertEqual(text.count('&dial_open'), 1)

    def test_dial_layer_routing_and_tb_isolation(self):
        shield = ROOT / 'boards/shields/GeaconEquinox'
        dial = (ROOT / 'config/equinox_dial.dtsi').read_text()
        self.assertIn('#if defined(EQUINOX_HAS_DIAL)', dial)
        self.assertIn('device = <&hires_dial_scroll>', dial)
        self.assertIn('&{/keymap/function_layer} { sensor-bindings = <&hires_dial_radial_controller 1 1>; };', dial)
        for layer in ('default', 'mouse', 'scroll', 'bt'):
            self.assertIn(f'&{{/keymap/{layer}_layer}} {{ sensor-bindings = <&hires_dial_scroll 10 1>; }};', dial)
        for layout in ('US', 'JIS'):
            keymap = (ROOT / f'config/GeaconEquinox_{layout}.keymap').read_text()
            self.assertTrue(keymap.rstrip().endswith('#include "equinox_dial.dtsi"'))
        overlay = (shield / 'geacon_equinox_left.overlay').read_text()
        self.assertNotIn('pat_listener', overlay)
        self.assertIn('device = <&right_tb_split>', overlay)
        self.assertEqual(overlay.count('INPUT_TRANSFORM_X_INVERT'), 2)
        self.assertNotIn('INPUT_TRANSFORM_Y_INVERT', overlay)
        self.assertIn('&board_cdc_acm_uart { status = "disabled"; };', overlay)
        self.assertNotIn('&snippet_studio_rpc_usb_uart { status = "disabled";', overlay)
        conf = (shield / 'geacon_equinox_left.conf').read_text()
        self.assertIn('CONFIG_ZMK_HIRES_DIAL_RADIAL_CONTROLLER=y', conf)
        self.assertIn('CONFIG_ZMK_HIRES_DIAL_SCROLL=y', conf)

    def test_first_fn_thumb_enter_tap_hold(self):
        dial = (ROOT / 'config/equinox_dial.dtsi').read_text()
        self.assertIn('flavor = "tap-preferred";', dial)
        self.assertIn('tapping-term-ms = <200>;', dial)
        self.assertIn('bindings = <&dial_open>, <&kp>;', dial)
        self.assertNotIn('hold-while-undecided', dial)
        for layout in ('US', 'JIS'):
            text = (ROOT / f'config/GeaconEquinox_{layout}.keymap').read_text()
            base = re.search(r'default_layer\s*\{.*?bindings\s*=\s*<([^>]+)>', text, re.S).group(1)
            fn = re.search(r'function_layer\s*\{.*?bindings\s*=\s*<([^>]+)>', text, re.S).group(1)
            base_bindings = [b.strip() for b in re.findall(r'&\w+[^&]*', base)]
            fn_bindings = [b.strip() for b in re.findall(r'&\w+[^&]*', fn)]
            thumb_space = base_bindings.index('&kp SPACE')
            self.assertEqual(fn_bindings[thumb_space], '&dial_enter 0 ENTER')
            self.assertEqual(fn_bindings[thumb_space + 1:thumb_space + 3], ['&kp ENTER', '&kp ENTER'])
            self.assertEqual(text.count('&dial_enter'), 1)

    def test_dial_mode_survives_fn_release_and_has_exit(self):
        dial = (ROOT / 'config/equinox_dial.dtsi').read_text()
        self.assertIn('#define EQUINOX_DIAL_LAYER 5', dial)
        self.assertIn('&{/keymap/dial_layer} { sensor-bindings = <&hires_dial_radial_controller 1 1>; };', dial)
        opening = re.search(r'dial_open: dial_open\s*\{([^}]+)', dial).group(1)
        self.assertIn('&macro_press &mo EQUINOX_DIAL_LAYER', opening)
        self.assertIn('&macro_pause_for_release', opening)
        self.assertNotIn('&macro_release &mo', opening)
        cancel = re.search(r'dial_cancel: dial_cancel\s*\{([^}]+)', dial).group(1)
        self.assertIn('&macro_release &hires_dial_radial_controller_button', cancel)
        self.assertIn('&macro_release &mo EQUINOX_DIAL_LAYER', cancel)
        for layout in ('US', 'JIS'):
            text = (ROOT / f'config/GeaconEquinox_{layout}.keymap').read_text()
            self.assertEqual(re.findall(r'^\s*(\w+_layer)\s*\{', text, re.M)[5], 'dial_layer')
            self.assertEqual(text.count('&dial_select 0 0'), 2)
            self.assertEqual(text.count('&dial_cancel'), 1)


if __name__ == '__main__':
    unittest.main()
