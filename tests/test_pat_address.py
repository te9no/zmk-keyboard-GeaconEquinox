import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pat_patch', ROOT / 'scripts/patch_pat_address.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PatAddress(unittest.TestCase):
    def test_source_guard(self):
        with self.assertRaises(ValueError):
            mod.patch('unexpected driver')

    def test_selection(self):
        source = ROOT.parents[1] / '.zmk-workspace/profiles/geacon-equinox/west/modules/zmk-driver-hires-dial/src/hires_dial.c'
        if not source.exists():
            self.skipTest('pinned west source required')
        patched = mod.patch(source.read_text())
        self.assertNotIn('&cfg->i2c', patched)
        function = 'static int pat_select_address' + patched.split('static int pat_select_address', 1)[1].split('#ifdef CONFIG_EQUINOX_PAT_IDSEL_TEST', 1)[0]
        harness = '''
#include <stdint.h>
#include <stddef.h>
#include <errno.h>
#include <assert.h>
#include <stdarg.h>
#define ARRAY_SIZE(a) (sizeof(a)/sizeof(a[0]))
#define PAT912X_PRODUCT_ID1 0
#define PRODUCT_ID_PAT9125EL 0x3191
static void test_log(const char *format, ...) { (void)format; }
#define LOG_ERR(...) test_log(__VA_ARGS__)
#define LOG_INF(...) test_log(__VA_ARGS__)
#define K_MSEC(x) (x)
#define PAT912X_CONFIGURATION 6
#define GPIO_OUTPUT_LOW 2
#define GPIO_INPUT 1
#define DT_NODELABEL(x) 0
#define DEVICE_DT_GET(x) (&test_port)
static int reads, sleeps, mode, reset_bad, gpio_bad, reset_nack, transient, writes;
struct i2c_dt_spec { int addr; };
struct pat912x_hires_dial_data { struct i2c_dt_spec runtime_i2c; };
struct device { void *data; };
static struct device test_port;
static int device_is_ready(const struct device *p) { (void)p;return 1; }
static int gpio_pin_configure(const struct device *p,int pin,int flags) {
 (void)p;assert(pin==11 && flags==3);return gpio_bad ? -EIO : 0;
}
static int gpio_pin_get_raw(const struct device *p,int pin) { (void)p;(void)pin;return 0; }
static int i2c_reg_write_byte_dt(struct i2c_dt_spec *bus,int reg,int val) {
 assert(bus->addr==mode && reg==6 && val==0x97);writes++;
 mode=reset_bad ? 0 : 0x75;transient=1;return reset_nack ? -EIO : 0;
}
static void k_sleep(int n) { (void)n; sleeps++; }
static int sys_get_be16(uint8_t *id) {return (id[0]<<8)|id[1];}
static int i2c_burst_read_dt(struct i2c_dt_spec *bus,int reg,uint8_t *id,size_t len) {
 (void)reg;(void)len;reads++;
 if(transient){transient--;return -EIO;}
 if(mode==bus->addr || mode==1) {id[0]=0x31;id[1]=0x91;return 0;}
 if(mode==2) {id[0]=0x31;id[1]=0x90;return 0;}
 return -EIO;
}
''' + function + '''
int main(void) {
 struct pat912x_hires_dial_data data={{0x79}}; struct device dev={&data};
 int addresses[]={0x73,0x75,0x79};
 for(int i=0;i<3;i++){mode=addresses[i];reads=0;assert(pat_select_address(&dev)==0);assert(data.runtime_i2c.addr==mode);assert(reads==3);}
 mode=1;assert(pat_select_address(&dev)==-EINVAL);
 mode=2;reads=0;sleeps=0;assert(pat_select_address(&dev)==-ENODEV);assert(reads==9 && sleeps==3);
 mode=0;assert(pat_select_address(&dev)==-ENODEV);
 for(int i=0;i<3;i++) {
  mode=addresses[i];reset_nack=i%2;writes=0;
  assert(pat_normalize_address(&dev)==0);
  assert(data.runtime_i2c.addr==0x75 && writes==1);
 }
 mode=0x73;gpio_bad=1;writes=0;
 assert(pat_normalize_address(&dev)==-EIO && writes==0);gpio_bad=0;
 mode=0x79;reset_bad=1;reads=0;
 assert(pat_normalize_address(&dev)==-ENODEV && reads==13);
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'pat.c'; exe=Path(tmp)/'pat'
            src.write_text(harness)
            subprocess.run(['cc','-Wall','-Werror',str(src),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True)
