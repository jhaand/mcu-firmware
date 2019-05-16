/*
 * Copyright (C) 2018 COGIP Robotics association <cogip35@gmail.com>
 *
 * This file is subject to the terms and conditions of the GNU Lesser
 * General Public License v2.1. See the file LICENSE in the top level
 * directory for more details.
 */

/**
 * @defgroup    planner Trajectory planification module
 * @ingroup     robotics
 * @brief       Trajectory planification module
 *
 * The planner, asociated to a controller, generate the robot course according
 * to a given path. It also handles avoidance behavior.
 *
 *
 * @{
 * @file
 * @brief       Common planner API and datas
 *
 * @author      Gilles DOFFE <g.doffe@gmail.com>
 * @author      Yannick GICQUEL <yannick.gicquel@gmail.com>
 * @author      Stephen CLYMANS <sclymans@gmail.com>
 */
#ifndef PLANNER_H_
#define PLANNER_H_

/* Project includes */
#include "ctrl.h"
#include "odometry.h"
#include "path.h"
#include "utils.h"


extern path_t *path;

/**
 * @brief Start a the planification for associated motion controller
 *
 * @param[in] arg               Controller object
 *
 * @return
 */
void planner_start(ctrl_t*);

/**
 * @brief Periodic task function to process a planner
 *
 * @param[in] arg               Should be NULL
 *
 * @return
 */
void *task_planner(void *arg);

#endif /* PLANNER_H_ */