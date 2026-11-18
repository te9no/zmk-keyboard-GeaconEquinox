/* Fault injection for the pinned mode worker and its request gate. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <errno.h>
#include <stddef.h>
#define IS_ENABLED(x) x
#define CONFIG_ZMK_BLE 1
#define CONFIG_ZMK_SPLIT_ROLE_CENTRAL 1
#define CONFIG_ZMK_NEMU_LINK_STUDIO_SYNC 0
#define ARG_UNUSED(x) (void)(x)
#define LOG_INF(...)
#define LOG_ERR(...)
#define K_FOREVER 0
#define K_MSEC(x) (x)
#define K_WORK_DELAYABLE_DEFINE(name, handler) static int name
struct k_work { int unused; };
static bool esb_active, ble_suspended, mode_pending, target_esb, mode_valid = true;
static int mode_lock, mode_work_q, enable_error, split_error, host_error, result, submissions;
#define k_mutex_lock(...) ((void)0)
#define k_mutex_unlock(...) ((void)0)
#define zmk_endpoint_clear_reports() ((void)0)
#define bt_enable(x) enable_error
#define bt_disable() 0
#define settings_load_subtree(x) 0
#define zmk_nemu_link_ble_split_resume() split_error
#define zmk_nemu_link_ble_host_resume() host_error
#define zmk_split_peripheral_select_first_available_transport() 0
#define zmk_split_peripheral_select_transport(x) 0
#define nemu_link_notify_mode_requested(x) ((void)0)
#define nemu_link_notify_mode_changed(mode, err) (result = (err))
#define k_work_reschedule_for_queue(...) (++submissions)
/* MODE_IMPLEMENTATION */
static void transition(bool esb) {
    int before = submissions;
    assert(request_mode(esb, 0) == 0);
    assert(submissions == before + 1);
    mode_work_handler(NULL);
}
int main(void) {
    transition(true);
    enable_error = -EIO;
    transition(false);
    assert(result == -EIO && !esb_active);
    transition(true);
    assert(result == 0 && esb_active);
    enable_error = 0;
    split_error = -ENOMEM;
    transition(false);
    assert(result == -ENOMEM);
    split_error = 0;
    enable_error = -EALREADY;
    host_error = -EIO;
    transition(false);
    assert(result == -EIO);
    host_error = 0;
    transition(false);
    assert(result == 0 && mode_valid);
    int before = submissions;
    assert(request_mode(false, 0) == 0 && before == submissions);
    return 0;
}
