#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/init.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/printk.h>

LOG_MODULE_REGISTER(equinox_pat_diag, LOG_LEVEL_INF);

#define PAT DT_NODELABEL(pat9125)
static const struct device *const pat = DEVICE_DT_GET(PAT);
static const struct i2c_dt_spec pat_bus = I2C_DT_SPEC_GET(PAT);
static const struct gpio_dt_spec motion = GPIO_DT_SPEC_GET(PAT, motion_gpios);

static void report(void) {
    uint8_t id[2] = {0};
    const uint8_t product_reg = 0;
    const bool bus_ready = device_is_ready(pat_bus.bus);
    printk("PAT probe: ready=%d init_res=%u bus_ready=%d addr=0x%02x\n",
           device_is_ready(pat), pat->state->init_res, bus_ready, pat_bus.addr);
    int result = bus_ready ? i2c_write_read(pat_bus.bus, pat_bus.addr,
                                          &product_reg, 1, id, sizeof(id)) : -ENODEV;
    int motion_raw = gpio_is_ready_dt(&motion) ? gpio_pin_get_raw(motion.port, motion.pin) : -ENODEV;
    printk("PAT ready=%d bus_ready=%d addr=0x%02x id_rc=%d id=%02x:%02x motion_raw=%d\n",
            device_is_ready(pat), bus_ready, pat_bus.addr, result, id[0], id[1], motion_raw);
    printk("PAT uptime_ms=%lld id_sel_raw=%d\n", k_uptime_get(),
           gpio_pin_get_raw(DEVICE_DT_GET(DT_NODELABEL(gpio1)), 11));
    if (bus_ready && result < 0) {
        /* Only the PAT9125's documented alternate ID_SEL addresses; no writes
         * to configuration registers or general-purpose bus scan. */
        const uint8_t alternatives[] = {0x73, 0x75};
        for (size_t i = 0; i < ARRAY_SIZE(alternatives); ++i) {
            uint8_t alt_id[2] = {0};
            int rc = i2c_write_read(pat_bus.bus, alternatives[i], &product_reg, 1,
                                    alt_id, sizeof(alt_id));
            printk("PAT alternate addr=0x%02x rc=%d id=%02x:%02x\n",
                   alternatives[i], rc, alt_id[0], alt_id[1]);
        }
    }
}

static void diagnostic_thread(void *a, void *b, void *c) {
    ARG_UNUSED(a);
    ARG_UNUSED(b);
    ARG_UNUSED(c);
    while (true) {
        report();
        k_sleep(K_SECONDS(5));
    }
}

K_THREAD_DEFINE(pat_diag_thread, 2048, diagnostic_thread, NULL, NULL, NULL, 10, 0, 10000);
