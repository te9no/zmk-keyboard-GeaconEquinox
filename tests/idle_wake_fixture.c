#include <assert.h>
#include <errno.h>
#include <stdint.h>
enum { NEMU_LINK_IDLE_OFF, NEMU_LINK_IDLE_WAKING, NEMU_LINK_IDLE_AWAKE };
enum { UP, NEMU_LINK_LINK_PERIPHERAL_LOST };
static struct { int phase; } idle, peripheral;
static uint64_t now, retry_wake_ms, idle_off_ms, idle_off_since;
static uint32_t idle_wakes, idle_errors, wake_max_ms;
static int calls, results[2];
#define CONFIG_ZMK_NEMU_LINK_IDLE_RETRY_MS 100
#define k_uptime_get() now
#define MAX(a,b) ((a) > (b) ? (a) : (b))
#define LOG_WRN(...)
static int nemu_link_radio_wake(void) { assert(calls < 2); return results[calls++]; }
/* WAKE */
int main(void) {
    results[0] = -EAGAIN;
    assert(idle_wake() == 0 && calls == 2 && peripheral.phase == UP && idle_wakes == 1);
    idle.phase = NEMU_LINK_IDLE_OFF;
    calls = 0;
    results[1] = -EAGAIN;
    assert(idle_wake() == -EAGAIN && calls == 2 && peripheral.phase == NEMU_LINK_LINK_PERIPHERAL_LOST);
    assert(idle_wake() == -EAGAIN && calls == 2 && idle_errors == 1);
    now += 100;
    calls = 0;
    results[0] = -EIO;
    assert(idle_wake() == -EIO && calls == 1);
    return 0;
}
