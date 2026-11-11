/* Radio callbacks publish state; animation control runs off the input queue. */
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/sys/atomic.h>
#include <zmk/nemu_link/control.h>
#include <zmk_driver_animation/drivers/animation_control.h>

static struct k_work_q queue;
K_THREAD_STACK_DEFINE(stack, 2048);
static struct k_work work;
static atomic_t state;
static atomic_t protected_until;
bool equinox_nemu_mode_led_active(void) {
    return (int32_t)((uint32_t)atomic_get(&protected_until) - k_uptime_get_32()) > 0;
}
static atomic_t boot_transition = IS_ENABLED(CONFIG_ZMK_NEMU_LINK_BOOT_ESB);
static const struct device *const animations[] = {
    DEVICE_DT_GET(DT_NODELABEL(nemu_switching_animation)),
    DEVICE_DT_GET(DT_NODELABEL(nemu_ble_animation)),
    DEVICE_DT_GET(DT_NODELABEL(nemu_esb_animation)),
    DEVICE_DT_GET(DT_NODELABEL(nemu_error_animation)),
};
static void display(struct k_work *unused) {
    ARG_UNUSED(unused);
    unsigned s = atomic_get(&state);
    animation_control_play_now(DEVICE_DT_GET(DT_NODELABEL(animation_control)),
                               animations[s], true, s == 0 ? 8000 : 2400);
}
static void notify(unsigned s) {
    atomic_set(&protected_until, k_uptime_get_32() + (s == 0 ? 8000 : 2400));
    atomic_set(&state, s);
    k_work_submit_to_queue(&queue, &work);
}
static void requested(bool esb) {
    ARG_UNUSED(esb);
    if (!atomic_get(&boot_transition)) {
        notify(0);
    }
}
static void changed(bool esb, int error) {
    /* Preserve the original battery/endpoint sequence on a successful boot. */
    if (atomic_cas(&boot_transition, 1, 0) && !error) {
        return;
    }
    notify(error ? 3 : esb ? 2 : 1);
}
static const struct zmk_nemu_link_observer observer = {
    .mode_requested = requested, .mode_changed = changed,
};
static int init(void) {
    k_work_init(&work, display);
    k_work_queue_start(&queue, stack, K_THREAD_STACK_SIZEOF(stack), 10, NULL);
    return zmk_nemu_link_register_observer(&observer);
}
SYS_INIT(init, APPLICATION, 98);
