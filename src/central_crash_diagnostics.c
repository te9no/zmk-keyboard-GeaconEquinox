#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include <cormoran/zmk/watchdog.h>
#include <cormoran/runtime_combo/runtime_combo.h>

/* Preserve evidence before reboot without writing flash or logging in fault context.
 * Candidate return addresses are raw stack words, not an unwound backtrace. */
static struct {
    uint32_t magic;
    uint32_t count;
    uint32_t words[CONFIG_SYSTEM_WORKQUEUE_STACK_SIZE / sizeof(uint32_t)];
} __noinit crash_stack;

void __real_zmk_watchdog_pending_set(const struct zmk_watchdog_incident_record *rec);
void __wrap_zmk_watchdog_pending_set(const struct zmk_watchdog_incident_record *rec) {
    if (rec->type == ZMK_WATCHDOG_INCIDENT_FATAL &&
        k_current_get() == &k_sys_work_q.thread) {
        crash_stack.magic = 0;
        const volatile uint32_t *src =
            (const volatile uint32_t *)k_sys_work_q.thread.stack_info.start;
        uint32_t count = MIN(ARRAY_SIZE(crash_stack.words),
                             k_sys_work_q.thread.stack_info.size / sizeof(uint32_t));
        for (uint32_t i = 0; i < count; i++) {
            crash_stack.words[i] = src[i];
        }
        crash_stack.count = count;
        crash_stack.magic = 0x45514353;
    }
    __real_zmk_watchdog_pending_set(rec);
}

static void report_thread(void *a, void *b, void *c) {
    ARG_UNUSED(a);
    ARG_UNUSED(b);
    ARG_UNUSED(c);
    while (true) {
        struct zmk_runtime_combo_global_settings global;
        int combo_rc = zmk_runtime_combo_read_global_settings(&global);
        printk("COMBO global rc=%d count=%u timeout=%u idle=%u\n", combo_rc,
               zmk_runtime_combo_count(), combo_rc ? 0 : global.timeout_ms,
               combo_rc ? 0 : global.require_prior_idle_ms);
        for (uint32_t i = 0; i < zmk_runtime_combo_max_count(); i++) {
            struct zmk_runtime_combo_config combo;
            int rc = zmk_runtime_combo_read(i, &combo);
            if (rc) {
                printk("COMBO slot=%u rc=%d\n", i, rc);
                continue;
            }
            printk("COMBO slot=%u enabled=%u len=%u layers=%08x behavior=%s p1=%u p2=%u timeout=%u\n",
                   i, combo.enabled, combo.key_position_len, combo.layer_mask,
                   combo.behavior.behavior_dev ? combo.behavior.behavior_dev : "NULL",
                   combo.behavior.param1, combo.behavior.param2, combo.timeout_ms);
            for (uint8_t p = 0; p < combo.key_position_len; p++) {
                printk("COMBO slot=%u pos[%u]=%d\n", i, p, combo.key_positions[p]);
            }
        }
        size_t unused = 0;
        int stack_rc = k_thread_stack_space_get(&k_sys_work_q.thread, &unused);
        printk("CENTRAL STACK rc=%d unused=%u total=%u\n", stack_rc,
               (unsigned)unused, (unsigned)k_sys_work_q.thread.stack_info.size);
        if (crash_stack.magic == 0x45514353 &&
            crash_stack.count <= ARRAY_SIZE(crash_stack.words)) {
            for (uint32_t i = 0; i < crash_stack.count; i++) {
                uint32_t word = crash_stack.words[i];
                if ((word & 1) && word >= 0x27000 && word < 0x100000) {
                    printk("CENTRAL STACK_CANDIDATE offset=%u addr=%08x\n", i * 4, word);
                }
            }
            crash_stack.magic = 0;
        }
        printk("CENTRAL WATCHDOG uptime_ms=%lld count=%u capacity=%u dropped=%u\n",
               k_uptime_get(), zmk_watchdog_store_count(), zmk_watchdog_store_capacity(),
               zmk_watchdog_store_dropped_since_boot());
        for (uint16_t i = 0; i < zmk_watchdog_store_count(); i++) {
            struct zmk_watchdog_incident_record rec;
            if (zmk_watchdog_store_get(i, &rec) != 0) {
                continue;
            }
            if (rec.type == ZMK_WATCHDOG_INCIDENT_FATAL) {
                printk("CENTRAL CRASH ordinal=%u uptime_s=%u reason=%u pc=%08x lr=%08x thread=%.16s\n",
                       rec.boot_ordinal, rec.uptime_s, rec.detail.fatal.reason,
                       rec.detail.fatal.pc, rec.detail.fatal.lr, rec.detail.fatal.thread_name);
            } else if (rec.type == ZMK_WATCHDOG_INCIDENT_FREEZE) {
                printk("CENTRAL FREEZE ordinal=%u uptime_s=%u channel=%u queue=%.16s\n",
                       rec.boot_ordinal, rec.uptime_s, rec.detail.freeze.channel_id,
                       rec.detail.freeze.queue_name);
            } else {
                printk("CENTRAL RESET ordinal=%u uptime_s=%u type=%u cause=%08x\n",
                       rec.boot_ordinal, rec.uptime_s, rec.type, rec.detail.reset.cause_bits);
            }
        }
        k_sleep(K_SECONDS(5));
    }
}

K_THREAD_DEFINE(central_crash_diag, 2048, report_thread, NULL, NULL, NULL, 10, 0, 2000);
