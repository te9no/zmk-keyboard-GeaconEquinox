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
                self.assertEqual(len(bindings), 5)
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


if __name__ == '__main__':
    unittest.main()
