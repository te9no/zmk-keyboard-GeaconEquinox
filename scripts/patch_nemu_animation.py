"""Adapt pinned original LED modules without editing the shared checkout."""
import hashlib
from pathlib import Path
import sys
HASHES = {'animation.c': '8bbf0e54c4837acf8b5bcb3eaead0cd35997a841826eeea03f98dc1a1754cc77', 'animation_endpoint.c': '8d1bdc3e77755b5103ee6275dbad190dfc80c2e5de534e998af81ca1f15f5c54', 'widget.c': '975d3fb16866397b9144dd1da4458aa0475fcecdfa9b399daee345ad745931f8'}
HASHES['animation_layer_status.c'] = 'e4ae591bc848523fee22f61b63e3bf7a3746c335779a7b53f10f64bb7f5bdae3'
source, output = map(Path, sys.argv[1:])
s = source.read_text()
if hashlib.sha256(source.read_bytes()).hexdigest() != HASHES[source.name]:
    raise SystemExit("LED module changed; review the adaptation")
if source.name == 'animation.c':
    s = s.replace('K_WORK_DEFINE(animation_work, zmk_animation_tick);', 'static struct k_work_q equinox_animation_queue;\nK_THREAD_STACK_DEFINE(equinox_animation_stack, 4096);\nK_WORK_DEFINE(animation_work, zmk_animation_tick);')
    s = s.replace('k_work_submit(&animation_work);', 'k_work_submit_to_queue(&equinox_animation_queue, &animation_work);')
    s = s.replace('static int zmk_animation_init(void) {', 'static int zmk_animation_init(void) {\n    k_work_queue_start(&equinox_animation_queue, equinox_animation_stack,\n                      K_THREAD_STACK_SIZEOF(equinox_animation_stack), 10, NULL);')
elif source.name == 'animation_endpoint.c':
    s = '#include <zmk/nemu_link/control.h>\n' + s
    marker = "#if IS_CENTRAL\n    update_pixels_central(dev, pixels, num_pixels);\n#elif IS_SPLIT_PERIPHERAL\n    update_pixels_peripheral(dev, pixels, num_pixels);\n#endif"
    prefix = '    if (zmk_nemu_link_owns_radio()) {\n        const struct animation_endpoint_config *config = dev->config;\n        bool up = ((zmk_nemu_link_debug_state() >> 5) & 3) == 2;\n        struct zmk_color_hsl color = up ? *config->color_usb : *config->color_disconnected;\n        struct zmk_color_rgb rgb;\n        zmk_hsl_to_rgb(&color, &rgb);\n        for (size_t i = 0; i < config->pixel_map_size; i++) {\n            pixels[config->pixel_map[i]].value = rgb;\n        }\n    } else {\n'
    if marker not in s: raise SystemExit('endpoint render changed')
    s = s.replace(marker, prefix + marker + '\n    }')
elif source.name == 'animation_layer_status.c':
    s = '#include <zmk/nemu_link/control.h>\n' + s
    s = s.replace('#if IS_SPLIT_PERIPHERAL', '#if IS_SPLIT_PERIPHERAL || IS_ENABLED(CONFIG_ZMK_NEMU_LINK)')
    s = s.replace('        uint8_t idx = i + config->layer_offset;',
        '        uint8_t idx = i + config->layer_offset;\n'
        '        if (zmk_nemu_link_owns_radio() && data->layer_status) {\n'
        '            idx = 31U - __builtin_clz(data->layer_status);\n'
        '        }')
    s = s.replace('(1 << idx)', '(UINT32_C(1) << idx)')
    s = s.replace('    data->layer_status = 0;', '    if (!zmk_nemu_link_owns_radio()) { data->layer_status = 0; }')
    for fn in ('refresh_layer_status_central', 'sync_layer_status_to_peripheral'):
        marker = 'static void ' + fn + '(const struct device *dev) {'
        s = s.replace(marker, marker + '\n    if (zmk_nemu_link_owns_radio()) { return; }')
elif source.name == 'widget.c':
    s = '#include <zmk/nemu_link/control.h>\n' + s
    marker = '    struct blink_item blink = {.duration_ms = CONFIG_RGBLED_WIDGET_CONN_BLINK_MS};'
    s = s.replace(marker, marker + '\n    if (zmk_nemu_link_owns_radio()) {\n        bool up = ((zmk_nemu_link_debug_state() >> 5) & 3) == 2;\n        blink.color = up ? CONFIG_RGBLED_WIDGET_CONN_COLOR_CONNECTED\n                         : CONFIG_RGBLED_WIDGET_CONN_COLOR_DISCONNECTED;\n        k_msgq_put(&led_msgq, &blink, K_NO_WAIT);\n        return;\n    }')
output.write_text(s)
