"""Exercise the actual C voltage conversion across the full ADC range."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class NemuBatteryTest(unittest.TestCase):
    def test_nimh_curve(self):
        source = '''
#include <assert.h>
#include "equinox_nimh.h"
int main(void) {
    uint16_t v[] = {1100,1150,1200,1220,1240,1260,1280,1300,1320,1350,1400};
    unsigned prev = 0;
    for (unsigned mv=0; mv<=65535; mv++) {
        unsigned pct=equinox_nimh_percent(mv,v);
        assert(pct>=prev && pct<=100);
        prev=pct;
    }
    for (unsigned i=0;i<11;i++) assert(equinox_nimh_percent(v[i],v)==i*10);
    assert(equinox_nimh_percent(1125,v)==5);
    assert(equinox_nimh_percent(1375,v)==95);
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as d:
            c=Path(d)/'test.c'; c.write_text(source)
            exe=Path(d)/'test'
            subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-I',str(ROOT/'include'),str(c),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True)
