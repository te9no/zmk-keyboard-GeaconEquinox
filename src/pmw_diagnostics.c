#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include <cormoran/pmw3610/pmw3610_api.h>
#include <zmk/split/bluetooth/peripheral.h>
#if IS_ENABLED(CONFIG_EQUINOX_CRASH_DIAGNOSTICS)
#include <cormoran/zmk/watchdog.h>
#endif

static void report_thread(void *a, void *b, void *c) {
    ARG_UNUSED(a);
    ARG_UNUSED(b);
    ARG_UNUSED(c);
    const struct device *dev = DEVICE_DT_GET(DT_NODELABEL(trackball));
    const struct gpio_dt_spec irq = GPIO_DT_SPEC_GET(DT_NODELABEL(trackball), irq_gpios);
    while (true) {
#if IS_ENABLED(CONFIG_EQUINOX_CRASH_DIAGNOSTICS)
        printk("WATCHDOG count=%u capacity=%u dropped=%u\n", zmk_watchdog_store_count(),
               zmk_watchdog_store_capacity(), zmk_watchdog_store_dropped_since_boot());
        for (uint16_t i = 0; i < zmk_watchdog_store_count(); i++) {
            struct zmk_watchdog_incident_record rec;
            if (zmk_watchdog_store_get(i, &rec) != 0) {
                continue;
            }
            if (rec.type == ZMK_WATCHDOG_INCIDENT_FATAL) {
                printk("CRASH ordinal=%u uptime_s=%u reason=%u pc=%08x lr=%08x thread=%.16s\n",
                       rec.boot_ordinal, rec.uptime_s, rec.detail.fatal.reason,
                       rec.detail.fatal.pc, rec.detail.fatal.lr, rec.detail.fatal.thread_name);
            } else if (rec.type == ZMK_WATCHDOG_INCIDENT_FREEZE) {
                printk("FREEZE ordinal=%u uptime_s=%u channel=%u queue=%.16s\n",
                       rec.boot_ordinal, rec.uptime_s, rec.detail.freeze.channel_id,
                       rec.detail.freeze.queue_name);
            } else {
                printk("RESET ordinal=%u uptime_s=%u type=%u cause=%08x\n",
                       rec.boot_ordinal, rec.uptime_s, rec.type, rec.detail.reset.cause_bits);
            }
        }
#endif
        printk("PMW ready=%d device_ready=%d init_error=%d irq_raw=%d split_connected=%d uptime_ms=%lld\n",
               pmw3610_is_ready(dev), device_is_ready(dev), pmw3610_get_init_error(dev),
               gpio_is_ready_dt(&irq) ? gpio_pin_get_raw(irq.port, irq.pin) : -1,
               zmk_split_bt_peripheral_is_connected(), k_uptime_get());
        k_sleep(K_SECONDS(5));
    }
}

K_THREAD_DEFINE(pmw_diag_thread, 2048, report_thread, NULL, NULL, NULL, 10, 0,
                IS_ENABLED(CONFIG_EQUINOX_CRASH_DIAGNOSTICS) ? 2000 : 10000);
