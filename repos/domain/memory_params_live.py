#!/usr/bin/env python
# Test set domain memory parameters with flag
# VIR_DOMAIN_AFFECT_LIVE

import os
import math
import commands
from xml.dom import minidom

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('guestname', 'hard_limit', 'soft_limit', 'swap_hard_limit', )
optional_params = {}

UNLIMITED = 9007199254740991
CGROUP_PATH = "/cgroup/"

def get_cgroup_setting(guestname):
    """get domain memory parameters in cgroup
    """
    if os.path.exists(CGROUP_PATH):
        cgroup_path = CGROUP_PATH
    else:
        cgroup_path = "/sys/fs%s" % CGROUP_PATH

    cmd = "lscgroup | grep %s | grep memory:" % guestname
    ret, out = commands.getstatusoutput(cmd)
    if ret:
        logger.error(out)
        return 1
    else:
        mem_cgroup_path = "%s%s" % (cgroup_path, out.replace(':', ''))

    f = open("%s/memory.limit_in_bytes" % mem_cgroup_path)
    hard = int(f.read())
    logger.info("memory.limit_in_bytes value is %s" % hard)
    f.close()

    f = open("%s/memory.soft_limit_in_bytes" % mem_cgroup_path)
    soft = int(f.read())
    logger.info("memory.soft_limit_in_bytes value is %s" % soft)
    f.close()

    f = open("%s/memory.memsw.limit_in_bytes" % mem_cgroup_path)
    swap = int(f.read())
    logger.info("memory.memsw.limit_in_bytes value is %s" % swap)
    f.close()

    new_dict = {'hard_limit': hard/1024,
                'soft_limit': soft/1024,
                'swap_hard_limit': swap/1024
               }
    logger.debug("memory parameters dict get from cgroup is %s" % new_dict)

    return new_dict

def memory_params_live(params):
    """set domain memory parameters with live flag and check
    """
    global logger
    logger = params['logger']
    guestname = params['guestname']
    hard_limit = int(params['hard_limit'])
    soft_limit = int(params['soft_limit'])
    swap_hard_limit = int(params['swap_hard_limit'])

    logger.info("the name of virtual machine is %s" % guestname)
    param_dict = {'hard_limit': hard_limit,
                  'soft_limit': soft_limit,
                  'swap_hard_limit': swap_hard_limit
                 }

    for i in param_dict.keys():
        if param_dict[i] == -1:
            param_dict[i] = UNLIMITED

    logger.info("the param dict for setting is %s" % param_dict)

    conn = sharedmod.libvirtobj['conn']

    try:
        domobj = conn.lookupByName(guestname)
        flags = libvirt.VIR_DOMAIN_AFFECT_LIVE
        logger.info("get %s memory parameters with flag: %s" %
                    (guestname, flags))
        ret_pre = domobj.memoryParameters(flags)
        logger.info("%s memory parameters is %s" % (guestname, ret_pre))

        logger.info("set %s memory parameters with flag: %s" %
                    (guestname, flags))
        domobj.setMemoryParameters(param_dict, flags)
        logger.info("set memory parameters done")

        logger.info("get %s memory parameters with flag: %s" %
                    (guestname, flags))
        ret_pos = domobj.memoryParameters(flags)
        logger.info("%s memory parameters is %s" % (guestname, ret_pos))

        if ret_pos == param_dict:
            logger.info("memory parameters is as expected")
        else:
            logger.error("memory parameters is not as expected")
            return 1

        logger.info("check memory parameters in cgroup")
        ret = get_cgroup_setting(guestname)
        if ret == 1:
            logger.error("fail to get domain memory cgroup setting")
            return 1

        for i in param_dict.keys():
            if math.fabs(param_dict[i] - ret[i]) > 1:
                logger.error("%s value not match with cgroup setting" % i)
                return 1

        logger.info("memory parameters is as expected in cgroup setting")

    except libvirtError, e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    return 0

def memory_params_live_check(params):
    """check lscgroup packages
    """
    logger = params['logger']
    cmd = 'lscgroup'
    ret, out = commands.getstatusoutput(cmd)
    if ret and 'command not found' in out:
        logger.error(out)
        logger.error("package libcgroup or libcgroup-tools is not installed")
        return 1
