"""Generate a pinned local driver that normalizes PAT ID_SEL to Low after reset."""
import hashlib
from pathlib import Path
import sys

SHA = 'c7e7b316a4192265f1493e087d4db06df457b89a27d6d5ff3ee58cce71ecfa0b'


def patch(source):
    source = source.replace('\r\n', '\n')
    if hashlib.sha256(source.encode()).hexdigest() != SHA:
        raise ValueError('PAT driver changed; review address patch')
    source = source.replace('struct pat912x_hires_dial_data {',
                            'struct pat912x_hires_dial_data {\n    struct i2c_dt_spec runtime_i2c;')
    marker = 'static inline int32_t sign_extend_12'
    helper = '''static const struct i2c_dt_spec *pat_runtime_bus(const struct device *dev) {
    struct pat912x_hires_dial_data *data = dev->data;
    return &data->runtime_i2c;
}

int equinox_pat_selected_address(const struct device *dev) {
    return pat_runtime_bus(dev)->addr;
}

static int pat_select_address(const struct device *dev) {
    struct pat912x_hires_dial_data *data = dev->data;
    const uint8_t addresses[] = {0x73, 0x75, 0x79};
    for (int attempt = 0; attempt < 3; ++attempt) {
        int matches = 0;
        uint16_t selected = 0;
        for (size_t i = 0; i < ARRAY_SIZE(addresses); ++i) {
            uint8_t id[2] = {0};
            struct i2c_dt_spec probe = data->runtime_i2c;
            probe.addr = addresses[i];
            int rc = i2c_burst_read_dt(&probe, PAT912X_PRODUCT_ID1, id, sizeof(id));
            if (rc == 0 && sys_get_be16(id) == PRODUCT_ID_PAT9125EL) {
                selected = probe.addr;
                ++matches;
            }
        }
        if (matches > 1) {
            LOG_ERR("Multiple PAT sensors found; refusing ambiguous address");
            return -EINVAL;
        }
        if (matches == 1) {
            data->runtime_i2c.addr = selected;
            LOG_INF("PAT selected address=0x%02x", selected);
            return 0;
        }
        k_sleep(K_MSEC(10));
    }
    LOG_ERR("PAT product ID not found at supported addresses");
    return -ENODEV;
}

static int pat_normalize_address(const struct device *dev) {
    struct pat912x_hires_dial_data *data = dev->data;
    const struct device *port = DEVICE_DT_GET(DT_NODELABEL(gpio1));
    if (!device_is_ready(port)) { return -ENODEV; }
    int rc = pat_select_address(dev);
    if (rc < 0) { return rc; }
    const uint16_t initial_address = data->runtime_i2c.addr;
    rc = gpio_pin_configure(port, 11, GPIO_OUTPUT_LOW | GPIO_INPUT);
    if (rc < 0) { return rc; }
    k_sleep(K_MSEC(20));
    if (gpio_pin_get_raw(port, 11) != 0) { return -EIO; }
    /* GPIO changes alone do not reselect the slave address. Reset while Low.
     * The standard Zephyr PAT driver permits NACK on this reset write. */
    int reset_rc = i2c_reg_write_byte_dt(&data->runtime_i2c, PAT912X_CONFIGURATION, 0x97);
    data->runtime_i2c.addr = 0x75;
    k_sleep(K_MSEC(100));
    for (int attempt = 0; attempt < 10; ++attempt) {
        uint8_t id[2] = {0};
        rc = i2c_burst_read_dt(&data->runtime_i2c, PAT912X_PRODUCT_ID1, id, sizeof(id));
        if (rc == 0 && sys_get_be16(id) == PRODUCT_ID_PAT9125EL) {
            LOG_INF("PAT normalized 0x%02x -> 0x75; ID_SEL=Low reset_rc=%d", initial_address, reset_rc);
            return 0;
        }
        k_sleep(K_MSEC(20));
    }
    LOG_ERR("PAT Low-address verification failed; reset_rc=%d", reset_rc);
    return -ENODEV;
}

'''
    source = source.replace(marker, helper + marker)
    diagnostic = '''
#ifdef CONFIG_EQUINOX_PAT_IDSEL_TEST
static struct { const char *phase; int rc, level; uint8_t addr, id[2]; } pat_test_results[24];
static int pat_test_count;
void equinox_pat_report_idsel_test(void) {
    for (int i = 0; i < pat_test_count; ++i) {
        printk("PAT IDSEL phase=%s addr=0x%02x rc=%d id=%02x:%02x level=%d\\n",
               pat_test_results[i].phase, pat_test_results[i].addr,
               pat_test_results[i].rc, pat_test_results[i].id[0], pat_test_results[i].id[1], pat_test_results[i].level);
    }
}
static void pat_probe_phase(const struct device *dev, const char *phase) {
    const uint8_t addresses[] = {0x73, 0x75, 0x79};
    for (size_t i = 0; i < ARRAY_SIZE(addresses); ++i) {
        struct i2c_dt_spec bus = *pat_runtime_bus(dev);
        bus.addr = addresses[i];
        uint8_t id[2] = {0};
        int rc = i2c_burst_read_dt(&bus, PAT912X_PRODUCT_ID1, id, sizeof(id));
        int n = pat_test_count++;
        pat_test_results[n].phase = phase;
        pat_test_results[n].addr = bus.addr;
        pat_test_results[n].rc = rc;
        pat_test_results[n].level = gpio_pin_get_raw(DEVICE_DT_GET(DT_NODELABEL(gpio1)), 11);
        pat_test_results[n].id[0] = id[0];
        pat_test_results[n].id[1] = id[1];
        printk("PAT IDSEL phase=%s addr=0x%02x rc=%d id=%02x:%02x\\n",
               phase, bus.addr, rc, id[0], id[1]);
    }
}

static int pat_idsel_test(const struct device *dev) {
    const struct device *port = DEVICE_DT_GET(DT_NODELABEL(gpio1));
    if (!device_is_ready(port)) { return -ENODEV; }
    pat_probe_phase(dev, "input-before");
    int rc = gpio_pin_configure(port, 11, GPIO_OUTPUT_HIGH | GPIO_INPUT);
    if (rc < 0) { return rc; }
    k_sleep(K_MSEC(20));
    printk("PAT IDSEL high readback=%d\\n", gpio_pin_get_raw(port, 11));
    pat_probe_phase(dev, "output-high");
    rc = pat_select_address(dev);
    if (rc < 0) { gpio_pin_configure(port, 11, GPIO_INPUT); return rc; }
    /* Zephyr's PAT driver documents NACK on software reset. Verify by ID
     * scan afterwards instead of treating the reset return as success/failure. */
    int reset_rc = i2c_reg_write_byte_dt(pat_runtime_bus(dev), PAT912X_CONFIGURATION, 0x97);
    printk("PAT IDSEL high reset rc=%d\\n", reset_rc);
    k_sleep(K_MSEC(100));
    pat_probe_phase(dev, "high-after-reset");
    k_sleep(K_MSEC(100));
    pat_probe_phase(dev, "high-reset-retry");
    rc = gpio_pin_configure(port, 11, GPIO_OUTPUT_LOW | GPIO_INPUT);
    if (rc < 0) { return rc; }
    k_sleep(K_MSEC(20));
    printk("PAT IDSEL low readback=%d\\n", gpio_pin_get_raw(port, 11));
    pat_probe_phase(dev, "output-low");
    rc = pat_select_address(dev);
    if (rc < 0) { gpio_pin_configure(port, 11, GPIO_INPUT); return rc; }
    reset_rc = i2c_reg_write_byte_dt(pat_runtime_bus(dev), PAT912X_CONFIGURATION, 0x97);
    printk("PAT IDSEL low reset rc=%d\\n", reset_rc);
    k_sleep(K_MSEC(100));
    pat_probe_phase(dev, "low-after-reset");
    k_sleep(K_MSEC(100));
    pat_probe_phase(dev, "low-reset-retry");
    rc = gpio_pin_configure(port, 11, GPIO_INPUT);
    if (rc < 0) { return rc; }
    k_sleep(K_MSEC(20));
    pat_probe_phase(dev, "input-restored");
    return 0;
}
#endif

'''
    source = source.replace(marker, diagnostic + marker)
    source = source.replace('&cfg->i2c', 'pat_runtime_bus(dev)')
    source = source.replace('    LOG_INF("Initializing PAT912x hires dial',
                            '    data->runtime_i2c = cfg->i2c;\n\n    LOG_INF("Initializing PAT912x hires dial')
    source = source.replace('    err = pat912x_configure(dev);',
                            '#ifdef CONFIG_EQUINOX_PAT_IDSEL_TEST\n    err = pat_idsel_test(dev);\n    if (err < 0) { return err; }\n#endif\n    err = pat_normalize_address(dev);\n    if (err < 0) { return err; }\n\n    err = pat912x_configure(dev);')
    return source


if __name__ == '__main__':
    Path(sys.argv[2]).write_text(patch(Path(sys.argv[1]).read_text()))
