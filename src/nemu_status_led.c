/* Finite status animation; never run SPI writes in input/event work queues. */
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/led_strip.h>
#include <zephyr/sys/atomic.h>
#include <zmk/activity.h>
#include <zmk/event_manager.h>
#include <zmk/events/activity_state_changed.h>
#include <zmk/events/battery_state_changed.h>

static const struct device *strip = DEVICE_DT_GET(DT_NODELABEL(equinox_status_strip));
static const struct gpio_dt_spec power = GPIO_DT_SPEC_GET(DT_NODELABEL(status_power), gpios);
static struct k_work_q queue;
K_THREAD_STACK_DEFINE(stack, 1536);
static struct k_work_delayable work;
static atomic_t ready;
static atomic_t active;
static atomic_t restart;
static atomic_t battery = -1;
static bool powered;
static unsigned frame;
static struct led_rgb pixels[4];

static void off(void) {
    memset(pixels, 0, sizeof(pixels));
    if (powered) { (void)led_strip_update_rgb(strip, pixels, 4); }
    gpio_pin_set_dt(&power, 0);
    powered = false;
}

static void tick(struct k_work *unused) {
    ARG_UNUSED(unused);
    if (!atomic_get(&active)) { off(); return; }
    if (atomic_set(&restart, 0)) { frame = 0; }
    if (!powered) {
        if (gpio_pin_set_dt(&power, 1) < 0) { return; }
        powered = true;
        k_msleep(1);
    }
    /* 1.6 s softly pulsing rainbow, 1.6 s local battery, then power off. */
    if (frame >= 80) { off(); return; }
    static const struct led_rgb rainbow[4] = {
        {.r=24,.g=0,.b=6}, {.r=12,.g=18,.b=0},
        {.r=0,.g=20,.b=12}, {.r=6,.g=0,.b=24}
    };
    int soc = atomic_get(&battery);
    for (int i = 0; i < 4; i++) {
        if (frame < 40) {
            unsigned pulse = frame < 20 ? frame + 1 : 40 - frame;
            struct led_rgb c = rainbow[(i + frame / 10) % 4];
            pixels[i] = (struct led_rgb){.r=c.r*pulse/20, .g=c.g*pulse/20, .b=c.b*pulse/20};
        } else {
            pixels[i] = soc < 0 ? (struct led_rgb){.r=16,.g=8} :
                        soc < 25 ? (struct led_rgb){.r=24} :
                        soc < 65 ? (struct led_rgb){.g=20} :
                                   (struct led_rgb){.g=10,.b=28};
        }
    }
    if (!atomic_get(&active) || led_strip_update_rgb(strip, pixels, 4) < 0) {
        off(); return;
    }
    frame++;
    k_work_reschedule_for_queue(&queue, &work, K_MSEC(40));
}

static int event(const zmk_event_t *eh) {
    const struct zmk_battery_state_changed *b = as_zmk_battery_state_changed(eh);
    if (b) { atomic_set(&battery, b->state_of_charge); return ZMK_EV_EVENT_BUBBLE; }
    const struct zmk_activity_state_changed *a = as_zmk_activity_state_changed(eh);
    if (a && atomic_get(&ready)) {
        atomic_set(&active, a->state == ZMK_ACTIVITY_ACTIVE);
        if (a->state == ZMK_ACTIVITY_ACTIVE) { atomic_set(&restart, 1); }
        k_work_reschedule_for_queue(&queue, &work, K_NO_WAIT);
    }
    return ZMK_EV_EVENT_BUBBLE;
}
ZMK_LISTENER(equinox_nemu_led, event);
ZMK_SUBSCRIPTION(equinox_nemu_led, zmk_activity_state_changed);
ZMK_SUBSCRIPTION(equinox_nemu_led, zmk_battery_state_changed);

static int init(void) {
    if (!device_is_ready(strip) || !gpio_is_ready_dt(&power)) { return -ENODEV; }
    int err = gpio_pin_configure_dt(&power, GPIO_OUTPUT_INACTIVE);
    if (err) { return err; }
    k_work_init_delayable(&work, tick);
    k_work_queue_start(&queue, stack, K_THREAD_STACK_SIZEOF(stack), 10, NULL);
    atomic_set(&ready, 1);
    atomic_set(&active, zmk_activity_get_state() == ZMK_ACTIVITY_ACTIVE);
    atomic_set(&restart, 1);
    k_work_reschedule_for_queue(&queue, &work, K_MSEC(500));
    return 0;
}
SYS_INIT(init, APPLICATION, 99);
