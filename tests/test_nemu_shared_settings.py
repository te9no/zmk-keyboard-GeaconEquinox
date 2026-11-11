import ast
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
class SharedSettingsTests(unittest.TestCase):
    def test_mode_return_requires_complete_shared_sync(self):
        tree = ast.parse((ROOT/'scripts/patch_nemu_shared_settings.py').read_text())
        fragment = next(n.value.value for n in ast.walk(tree)
                        if isinstance(n, ast.AugAssign) and isinstance(n.value, ast.Constant)
                        and isinstance(n.value.value, str)
                        and 'bool equinox_shared_settings_ready_for_ble' in n.value.value)
        pre = """#include <stdbool.h>
#include <assert.h>
#define IS_ENABLED(x) 1
#define NEMU_LINK_STUDIO_INCOMPATIBLE 4
static int last_keymap_offer_decision;
static bool shared_ready,shared_synchronized,shared_save_pending,tx,rx;
static bool atomic_get(bool*p){return *p;}
static bool shared_tx_active(void){return tx;}
static bool shared_rx_active(void){return rx;}
"""
        main = """int main(void){for(int bits=0;bits<64;bits++){
last_keymap_offer_decision=(bits&1)?5:0;
shared_ready=!!(bits&2);shared_synchronized=!!(bits&4);
shared_save_pending=!!(bits&8);tx=!!(bits&16);rx=!!(bits&32);
assert(equinox_shared_settings_ready_for_ble()==(bits==7));}}
"""
        with tempfile.TemporaryDirectory() as folder:
            c=pathlib.Path(folder)/'test.c';exe=pathlib.Path(folder)/'test'
            c.write_text(pre+fragment+main)
            subprocess.run(['cc',str(c),'-o',str(exe)],check=True,capture_output=True)
            subprocess.run([str(exe)],check=True)
