#!/usr/bin/env python
# test libvirt cpu map

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ()
optional_params = {'conn': '', }

CPUSTATE = "cat /sys/devices/system/cpu/cpu%s/online"


def get_cpu_num(logger):
    """ get cpu number
    """
    cmd = "lscpu | grep 'CPU(s):' | head -1 | cut -d : -f 2 | tr -d ' '"
    status, out = utils.exec_cmd(cmd, shell=True)
    if status != 0:
        logger.error("Exec %s fails" % cmd)
        return -1
    logger.debug("Exec outputs %s" % out[0])

    return int(out[0])


def get_cpu_list(state_type, logger):
    """ get all cpu in the same type state
    """
    ret = list()

    if state_type == "online":
        match = '1'
        ret.append(0)
    elif state_type == "offline":
        match = '0'
    else:
        logger.error("Unidentified cpu state type %s" % state_type)
        return ret

    cpu_num = get_cpu_num(logger)
    if cpu_num < 0:
        return ret

    for i in range(1, cpu_num):
        cmd = CPUSTATE % i
        status, out = utils.exec_cmd(cmd, shell=True)
        if status != 0:
            logger.error("Exec %s fails" % cmd)
            return ret
        logger.debug("Exec outputs %s" % out[0])

        if out[0] == match:
            ret.append(i)

    return ret


def check_cpu_map(cpu_map, logger):
    """ check cpu map
    """
    cpu_num = get_cpu_num(logger)
    if not cpu_map[0] == cpu_num:
        logger.error("The number of CPUs is not correct")
        logger.error("getCPUMap returns %d, should be %d" %
                     (cpu_map[0], cpu_num))
        return False
    logger.info("check the number of CPUs success")

    online_cpus = get_cpu_list('online', logger)
    offline_cpus = get_cpu_list('offline', logger)

    if not cpu_map[2] == len(online_cpus):
        logger.error("The number of online CPUs is not correct")
        logger.error("getCPUMap returns %d, should be %d" %
                     (cpu_map[2], len(online_cpus)))
        return False
    logger.info("check the number of online CPUs success")

    for i in online_cpus:
        if not cpu_map[1][i] == True:
            logger.error("The cpu%s should be online" % i)
            return False

    for i in offline_cpus:
        if not cpu_map[1][i] == False:
            logger.error("The cpu%s should be offline" % i)
            return False
    logger.info("check the cpu states success")

    return True


def cpu_map(params):
    """ test libvirt cpu map
        getCPUMap returns a turple: (A, [B], C)
            A is number of CPUs
            B is a list of state indicates if CPU is online
            C is number of online CPUs
    """
    logger = params['logger']

    try:
        # get connection firstly.
        # If conn is not specified, use conn from sharedmod
        if 'conn' in params:
            conn = libvirt.open(params['conn'])
        else:
            conn = sharedmod.libvirtobj['conn']

        res = conn.getCPUMap()
        if check_cpu_map(res, logger):
            logger.info("check cpu map success")
        else:
            logger.error("check cpu map fails")
            return 1

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s" %
                     e.message)
        return 1

    return 0
