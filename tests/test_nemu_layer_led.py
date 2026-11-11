"""Execute the relay/receiver C callbacks with a small host transport mock."""
import pathlib, re, subprocess, tempfile, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
PRELUDE = r"""
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <assert.h>
#define IS_ENABLED(x) (x)
#define ARG_UNUSED(x) (void)(x)
#define K_THREAD_STACK_DEFINE(n,s) char n[s]
#define K_THREAD_STACK_SIZEOF(n) sizeof(n)
#define BIT(n) (1u<<(n))
#define DT_NODELABEL(n) 0
#define DEVICE_DT_GET(n) NULL
#define ZMK_BEHAVIOR_OPAQUE 0
#define BEHAVIOR_LOCALITY_CENTRAL 0
#define BEHAVIOR_DT_INST_DEFINE(...)
#define SYS_INIT(...)
#define ZMK_LISTENER(...)
#define ZMK_SUBSCRIPTION(...)
#define ZMK_EV_EVENT_BUBBLE 0
#define CONFIG_ZMK_NEMU_LINK_PERIPHERAL_COUNT 2
struct k_work { void (*fn)(struct k_work*); };
struct k_work_q { int unused; };
#define K_WORK_DEFINE(n,f) struct k_work n = {f}
typedef int32_t atomic_t;
static int32_t atomic_get(atomic_t *a) {return *a;}
static void atomic_set(atomic_t *a,int32_t v) {*a=v;}
static struct k_work *pending;
static int k_work_submit_to_queue(struct k_work_q *q,struct k_work *w) {pending=w;return 0;}
static void k_work_queue_start(struct k_work_q *q,void*s,int n,int p,void*x) {}
static uint32_t now;
static uint32_t k_uptime_get_32(void) {return now;}
static uint64_t k_uptime_get(void) {return now;}
static bool owns=true, protected=false;
static bool zmk_nemu_link_owns_radio(void) {return owns;}
bool equinox_nemu_mode_led_active(void) {return protected;}
struct zmk_behavior_binding {const char *behavior_dev; uint32_t param1;};
struct zmk_behavior_binding_event {uint64_t timestamp;};
struct behavior_driver_api {int (*binding_pressed)(struct zmk_behavior_binding*,struct zmk_behavior_binding_event);int (*binding_released)(struct zmk_behavior_binding*,struct zmk_behavior_binding_event);int locality;};
static uint32_t shown;
static int plays;
static void zmk_animation_layer_status_set_status(uint32_t x) {shown=x;}
static int animation_control_play_now(void*a,void*b,bool c,int d) {assert(d==1500);plays++;return 0;}
struct zmk_position_state_changed {bool state;};
typedef struct {int kind;struct zmk_position_state_changed key;} zmk_event_t;
static void *as_zmk_layer_state_changed(const zmk_event_t *e) {return e->kind==1?(void*)e:NULL;}
static const struct zmk_position_state_changed *as_zmk_position_state_changed(const zmk_event_t *e) {return e->kind==2?&e->key:NULL;}
static uint32_t mask=1;
static uint32_t zmk_keymap_layer_state(void) {return mask;}
static int zmk_keymap_layer_default(void) {return 0;}
static int sends; static uint32_t sent[2];
static int zmk_split_central_invoke_behavior(uint8_t source,struct zmk_behavior_binding*b,struct zmk_behavior_binding_event e,bool press) {assert(source<2);assert(press);sends++;sent[source]=b->param1;return 0;}
static void flush(void) {struct k_work*w=pending;pending=NULL;if(w)w->fn(w);}
"""
class RelayTests(unittest.TestCase):
    def run_c(self, receiver, body):
        source=re.sub(r'^#include[^\n]*\n', '', (ROOT/'src/nemu_layer_led.c').read_text(), flags=re.M)
        with tempfile.TemporaryDirectory() as d:
            c=pathlib.Path(d)/'test.c'; exe=pathlib.Path(d)/'test'
            c.write_text(PRELUDE+source+'\nint main(void) {'+body+'}\n')
            subprocess.run(['cc','-std=c11',f'-DCONFIG_BOARD_NEMU_LINK_DONGLE={int(receiver)}',f'-DCONFIG_EQUINOX_NEMU_STATUS_LED={int(not receiver)}',str(c),'-o',str(exe)],check=True,capture_output=True)
            subprocess.run([str(exe)],check=True)
    def test_relay_coalesces_and_refreshes_only_on_input(self):
        self.run_c(True, r"""
        init(); zmk_event_t layer={.kind=1}, key={.kind=2,.key={true}}, other={0};
        mask=2; listener(&layer); mask=4; listener(&layer); assert(sends==0);
        flush(); assert(sends==2 && sent[0]==5 && sent[1]==5);
        now=1000; listener(&key); assert(!pending);
        now=3000; listener(&other); assert(!pending);
        listener(&key); flush(); assert(sends==4);
        """)
    def test_halves_ignore_ble_and_protect_mode_indication(self):
        self.run_c(False, r"""
        init(); struct zmk_behavior_binding b={.param1=9};struct zmk_behavior_binding_event e={0};
        owns=false; receive(&b,e); assert(!pending);
        owns=true; protected=true; receive(&b,e); flush(); assert(plays==0);
        protected=false; receive(&b,e); b.param1=3; receive(&b,e);flush();
        assert(plays==1 && shown==3);
        """)
