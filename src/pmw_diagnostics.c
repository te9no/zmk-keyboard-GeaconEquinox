#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include <cormoran/pmw3610/pmw3610_api.h>
#include <zmk/split/bluetooth/peripheral.h>

static void report_thread(void *a, void *b, void *c) {
    ARG_UNUSED(a);
    ARG_UNUSED(b);
    ARG_UNUSED(c);
    const struct device *dev = DEVICE_DT_GET(DT_NODELABEL(trackball));
    const struct gpio_dt_spec irq = GPIO_DT_SPEC_GET(DT_NODELABEL(trackball), irq_gpios);
    while (true) {
        printk("PMW ready=%d device_ready=%d init_error=%d irq_raw=%d split_connected=%d uptime_ms=%lld\n",
               pmw3610_is_ready(dev), device_is_ready(dev), pmw3610_get_init_error(dev),
               gpio_is_ready_dt(&irq) ? gpio_pin_get_raw(irq.port, irq.pin) : -1,
               zmk_split_bt_peripheral_is_connected(), k_uptime_get());
        k_sleep(K_SECONDS(5));
    }
}

K_THREAD_DEFINE(pmw_diag_thread, 2048, report_thread, NULL, NULL, NULL, 10, 0, 10000);
