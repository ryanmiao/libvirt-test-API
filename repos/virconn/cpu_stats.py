#!/usr/bin/env python
# test libvirt cpu stats

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('cpuNum',)
optional_params = {'conn': '', }

STATFILE = "/proc/stat"
GETCPUSTAT = "cat /proc/stat | grep cpu%s"
USR_POS = 1
NI_POS = 2
SYS_POS = 3
IDLE_POS = 4
IOWAIT_POS = 5
IRQ_POS = 6
SOFTIRQ_POS = 7


def compare_result(dest, src, delta, logger):
    """ compare two integer results with delta bias
    """
    if dest >= src - delta and dest <= src + delta:
        return True
    return False


def check_stat(cpu, stat, stat_type, logger):
    """ check cpu stat for cpu[cpunum]
    """
    delta = 0
    if cpu == "-1":
        cmd = GETCPUSTAT % " | head -1"
        cpu = ""
    else:
        cmd = GETCPUSTAT % cpu

    status, out = utils.exec_cmd(cmd, shell=True)
    if status != 0:
        logger.error("Exec %s fails" % cmd)
        return False

    logger.debug("get cpu%s stats: %s" % (cpu, out))
    stats = out[0].split()
    logger.debug("cpu stats: %s" % stats)

    if stat_type == "kernel":
        target_stat = int(stats[SYS_POS]) + int(stats[IRQ_POS]) + \
                      int(stats[SOFTIRQ_POS])
        delta = 1
    elif stat_type == "idle":
        target_stat = int(stats[IDLE_POS])
        delta = 10
    elif stat_type == "user":
        target_stat = int(stats[USR_POS]) + int(stats[NI_POS])
        delta = 2
    elif stat_type == "iowait":
        target_stat = int(stats[IOWAIT_POS])
        delta = 10
    else:
        logger.error("Unidentified type %s" % stat_type)
        return False

    if compare_result(stat, target_stat, delta, logger):
        logger.info("%s stat check success" % stat_type)
    else:
        logger.error("%s stat check failed" % stat_type)
        logger.error("%s stat is %d, should be %d" %
                     (stat_type, stat, target_stat))
        return False

    return True


def cpu_stats(params):
    """ test libvirt cpu stats
    """
    logger = params['logger']
    cpunum = int(params['cpuNum'])
    stat_types = ['kernel', 'idle', 'user', 'iowait']

    try:
        # get connection firstly.
        # If conn is not specified, use conn from sharedmod
        if 'conn' in params:
            conn = libvirt.open(params['conn'])
        else:
            conn = sharedmod.libvirtobj['conn']

        res = conn.getCPUStats(cpunum, 0)

        for s in stat_types:
            if not s in res:
                logger.error("%s is not the key" % s)
                return 1
            if not check_stat(str(cpunum), res[s] / 10000000, s, logger):
                return 1

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s" %
                     e.message)
        return 1

    return 0
