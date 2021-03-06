#!/usr/bin/env python

import os
import sys
import re
import time
import commands

import libvirt
from libvirt import libvirtError

from src import sharedmod

required_params = ('poolname',)
optional_params = {}

VIRSH_POOLUUID = "virsh pool-uuid"

def check_pool_uuid(poolname, UUIDString, logger):
    """ check UUID String of a pool """
    status, ret = commands.getstatusoutput(VIRSH_POOLUUID + ' %s' % poolname)
    if status:
        logger.error("executing "+ "\"" +  VIRSH_POOLUUID + ' %s' % poolname + "\"" + " failed")
        logger.error(ret)
        return False
    else:
        UUIDString_virsh = ret[:-1]
        logger.debug("UUIDString from API is %s" % UUIDString)
        logger.debug("UUIDString from " + "\"" + VIRSH_POOLUUID + "\"" " is %s" % UUIDString_virsh)
        if UUIDString_virsh == UUIDString:
            return True
        else:
            return False

def pool_uuid(params):
    """ call appropriate API to generate the UUIDStirng
        of a pool , then compared to the output of command
        virsh pool-uuid
    """
    logger = params['logger']
    poolname = params['poolname']
    conn = sharedmod.libvirtobj['conn']

    pool_names = conn.listDefinedStoragePools()
    pool_names += conn.listStoragePools()

    if poolname in pool_names:
        poolobj = conn.storagePoolLookupByName(poolname)
    else:
        logger.error("%s not found\n" % poolname);
        return 1

    try:
        UUIDString = poolobj.UUIDString()
        logger.info("the UUID string of pool %s is %s" % (poolname, UUIDString))
        if check_pool_uuid(poolname, UUIDString, logger):
            logger.info(VIRSH_POOLUUID + " test succeeded.")
            return 0
        else:
            logger.error(VIRSH_POOLUUID + " test failed.")
            return 1
    except libvirtError, e:
        logger.error("API error message: %s, error code is %s" \
                     % (e.message, e.get_error_code()))
        return 1

    return 0
