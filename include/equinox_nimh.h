/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdint.h>
static inline uint8_t equinox_nimh_percent(uint16_t mv, const uint16_t levels[11]) {
    if (mv <= levels[0]) return 0;
    for (unsigned i = 1; i < 11; i++) {
        if (mv < levels[i]) {
            return (i - 1) * 10 + (mv - levels[i - 1]) * 10 / (levels[i] - levels[i - 1]);
        }
    }
    return 100;
}
