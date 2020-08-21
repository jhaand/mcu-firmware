/*
 * Copyright (C) 2020 COGIP Robotics association <cogip35@gmail.com>
 *
 * This file is subject to the terms and conditions of the GNU Lesser
 * General Public License v2.1. See the file LICENSE in the top level
 * directory for more details.
 */

/*
 * @{
 *
 * @file
 * @brief       vl53l0x-api RIOT interface emulation
 *
 * @author      Gilles DOFFE <g.doffe@gmail.com>
 */

/* Standard include */
#include <stdio.h>

/* Project includes */
#include "vl53l0x.h"
#include "board.h"

//static VL53L0X_Dev_t devices[VL53L0X_NUMOF];

int vl53l0x_init_dev(vl53l0x_t dev)
{
    (void) dev;
    return 0;
}

int vl53l0x_reset_dev(vl53l0x_t dev) {
    (void) dev;
    return 0;
}

void vl53l0x_reset(void)
{
    for (vl53l0x_t dev = 0; dev < VL53L0X_NUMOF; dev++) {
        assert(vl53l0x_reset_dev(dev) == 0);
    }
}

void vl53l0x_init(void)
{
    for (vl53l0x_t dev = 0; dev < VL53L0X_NUMOF; dev++) {
        assert(vl53l0x_init_dev(dev) == 0);
    }
}

uint16_t vl53l0x_continuous_ranging_get_measure(vl53l0x_t dev)
{
    (void) dev;

    return UINT16_MAX;
}
/** @} */
