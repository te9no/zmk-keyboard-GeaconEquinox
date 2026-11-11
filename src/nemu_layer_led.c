/* Receive layer state through the authenticated split behavior transport. */
#define DT_DRV_COMPAT te9no_behavior_nemu_layer_led
#include <zephyr/kernel.h>
#include <zephyr/sys/atomic.h>
#include <drivers/behavior.h>
#include <zmk/behavior.h>
#include <zmk/nemu_link/control.h>
static struct k_work_q layer_queue;
K_THREAD_STACK_DEFINE(layer_stack, 2048);
static atomic_t layer_mask = 1;
#if IS_ENABLED(CONFIG_EQUINOX_NEMU_STATUS_LED)
#include <zmk_driver_animation/drivers/animation_control.h>
#include <zmk_driver_animation/drivers/animation_layer_status.h>
extern bool equinox_nemu_mode_led_active(void);
static void show_layer(struct k_work *work) {
    ARG_UNUSED(work);
    if (!zmk_nemu_link_owns_radio() || equinox_nemu_mode_led_active()) { return; }
    zmk_animation_layer_status_set_status((uint32_t)atomic_get(&layer_mask));
    animation_control_play_now(DEVICE_DT_GET(DT_NODELABEL(animation_control)),
        DEVICE_DT_GET(DT_NODELABEL(animation_layer_status)), true, 1500);
}
K_WORK_DEFINE(show_work, show_layer);
#endif
static int receive(struct zmk_behavior_binding *binding, struct zmk_behavior_binding_event event) {
    ARG_UNUSED(event);
#if IS_ENABLED(CONFIG_EQUINOX_NEMU_STATUS_LED)
    if (zmk_nemu_link_owns_radio()) {
        atomic_set(&layer_mask, binding->param1);
        k_work_submit_to_queue(&layer_queue, &show_work);
    }
#endif
    return ZMK_BEHAVIOR_OPAQUE;
}
static int release(struct zmk_behavior_binding *binding, struct zmk_behavior_binding_event event) {
    ARG_UNUSED(binding); ARG_UNUSED(event); return ZMK_BEHAVIOR_OPAQUE;
}
static const struct behavior_driver_api api = {
    .binding_pressed = receive, .binding_released = release,
    .locality = BEHAVIOR_LOCALITY_CENTRAL,
};
BEHAVIOR_DT_INST_DEFINE(0, NULL, NULL, NULL, NULL, POST_KERNEL,
                       CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &api);
#if IS_ENABLED(CONFIG_BOARD_NEMU_LINK_DONGLE)
#include <zmk/keymap.h>
#include <zmk/event_manager.h>
#include <zmk/events/layer_state_changed.h>
#include <zmk/events/position_state_changed.h>
#include <zmk/split/central.h>
static atomic_t last_refresh;
static void send_layer(struct k_work *work) {
    ARG_UNUSED(work);
    struct zmk_behavior_binding binding = {
        .behavior_dev = "eq_layer", .param1 = (uint32_t)atomic_get(&layer_mask),
    };
    struct zmk_behavior_binding_event event = {.timestamp = k_uptime_get()};
    for (uint8_t source = 0; source < CONFIG_ZMK_NEMU_LINK_PERIPHERAL_COUNT; source++) {
        zmk_split_central_invoke_behavior(source, &binding, event, true);
    }
}
K_WORK_DEFINE(send_work, send_layer);
static int listener(const zmk_event_t *event) {
    bool changed = as_zmk_layer_state_changed(event) != NULL;
    const struct zmk_position_state_changed *key = as_zmk_position_state_changed(event);
    uint32_t now = k_uptime_get_32();
    /* Refresh on resumed typing, never with idle polling or pointer traffic. */
    if (changed || (key && key->state &&
        (uint32_t)(now - (uint32_t)atomic_get(&last_refresh)) >= 2000)) {
        atomic_set(&last_refresh, now);
        atomic_set(&layer_mask, zmk_keymap_layer_state() | BIT(zmk_keymap_layer_default()));
        k_work_submit_to_queue(&layer_queue, &send_work);
    }
    return ZMK_EV_EVENT_BUBBLE;
}
ZMK_LISTENER(equinox_layer_relay, listener);
ZMK_SUBSCRIPTION(equinox_layer_relay, zmk_layer_state_changed);
ZMK_SUBSCRIPTION(equinox_layer_relay, zmk_position_state_changed);
#endif
static int init(void) {
    k_work_queue_start(&layer_queue, layer_stack, K_THREAD_STACK_SIZEOF(layer_stack), 10, NULL);
    return 0;
}
SYS_INIT(init, APPLICATION, 97);
