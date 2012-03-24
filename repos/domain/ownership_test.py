#!/usr/bin/env python
"""Setting the dynamic_ownership in /etc/libvirt/qemu.conf,
   check the ownership of saved domain file. Test could be on
   local or root_squash nfs. The default owner of the saved
   domain file is qemu:qemu in this case.
   domain:ownership_test
       guestname
           #GUESTNAME#
       dynamic_ownership
           enable|disable
       use_nfs
           enable|disable
"""

__author__ = 'Wayne Sun: gsun@redhat.com'
__date__ = 'Mon Jul 25, 2011'
__version__ = '0.1.0'
__credits__ = 'Copyright (C) 2011 Red Hat, Inc.'
__all__ = ['ownership_test']

import os
import re
import sys

QEMU_CONF = "/etc/libvirt/qemu.conf"
SAVE_FILE = "/mnt/test.save"
TEMP_FILE = "/tmp/test.save"

def append_path(path):
    """Append root path of package"""
    if path not in sys.path:
        sys.path.append(path)

from lib import connectAPI
from lib import domainAPI
from utils.Python import utils
from exception import LibvirtAPI

pwd = os.getcwd()
result = re.search('(.*)libvirt-test-API', pwd)
append_path(result.group(0))

def return_close(conn, logger, ret):
    """close hypervisor connection and return the given value"""
    conn.close()
    logger.info("closed hypervisor connection")
    return ret

def check_params(params):
    """Verify inputing parameter dictionary"""
    logger = params['logger']
    keys = ['guestname', 'dynamic_ownership', 'use_nfs']
    for key in keys:
        if key not in params:
            logger.error("%s is required" %key)
            return 1
    return 0

def check_domain_running(domobj, guestname, logger):
    """ check if the domain exists, may or may not be active """
    guest_names = domobj.get_list()

    if guestname not in guest_names:
        logger.error("%s doesn't exist or not running" % guestname)
        return 1
    else:
        return 0

def nfs_setup(util, logger):
    """setup nfs on localhost
    """
    logger.info("set nfs service")
    cmd = "echo /tmp *\(rw,root_squash\) >> /etc/exports"
    ret, out = util.exec_cmd(cmd, shell=True)
    if ret:
        logger.error("failed to config nfs export")
        return 1

    logger.info("restart nfs service")
    cmd = "service nfs restart"
    ret, out = util.exec_cmd(cmd, shell=True)
    if ret:
        logger.error("failed to restart nfs service")
        return 1
    else:
        for i in range(len(out)):
            logger.info(out[i])

    return 0

def chown_file(util, filepath, logger):
    """touch a file and setting the chown
    """
    if os.path.exists(filepath):
        os.remove(filepath)

    touch_cmd = "touch %s" % filepath
    logger.info(touch_cmd)
    ret, out = util.exec_cmd(touch_cmd, shell=True)
    if ret:
        logger.error("failed to touch a new file")
        logger.error(out[0])
        return 1

    logger.info("set chown of %s as 107:107" % filepath)
    chown_cmd = "chown 107:107 %s" % filepath
    ret, out = util.exec_cmd(chown_cmd, shell=True)
    if ret:
        logger.error("failed to set the ownership of %s" % filepath)
        return 1

    logger.info("set %s mode as 664" % filepath)
    cmd = "chmod 664 %s" % filepath
    ret, out = util.exec_cmd(cmd, shell=True)
    if ret:
        logger.error("failed to set the mode of %s" % filepath)
        return 1

    return 0

def prepare_env(util, dynamic_ownership, use_nfs, logger):
    """configure dynamic_ownership in /etc/libvirt/qemu.conf,
       set chown of the file to save
    """
    if dynamic_ownership == 'enable':
        d_ownership = 1
    elif dynamic_ownership == 'disable':
        d_ownership = 0
    else:
        logger.error("wrong dynamic_ownership value")
        return 1

    logger.info("set the dynamic ownership in %s as %s" % \
                (QEMU_CONF, d_ownership))
    set_cmd = "echo dynamic_ownership = %s >> %s" % \
               (d_ownership, QEMU_CONF)
    ret, out = util.exec_cmd(set_cmd, shell=True)
    if ret:
        logger.error("failed to set dynamic ownership")
        return 1

    logger.info("restart libvirtd")
    restart_cmd = "service libvirtd restart"
    ret, out = util.exec_cmd(restart_cmd, shell=True)
    if ret:
        logger.error("failed to restart libvirtd")
        return 1
    else:
        for i in range(len(out)):
            logger.info(out[i])

    if use_nfs == 'enable':
        filepath = TEMP_FILE
    elif use_nfs == 'disable':
        filepath = SAVE_FILE
    else:
        logger.error("wrong use_nfs value")
        return 1

    ret = chown_file(util, filepath, logger)
    if ret:
        return 1

    if use_nfs == 'enable':
        ret = nfs_setup(util, logger)
        if ret:
            return 1

        cmd = "setsebool virt_use_nfs 1"
        logger.info(cmd)
        ret, out = util.exec_cmd(cmd, shell=True)
        if ret:
            logger.error("Failed to setsebool virt_use_nfs")
            return 1

        logger.info("mount the nfs path to /mnt")
        mount_cmd = "mount -o vers=3 127.0.0.1:/tmp /mnt"
        ret, out = util.exec_cmd(mount_cmd, shell=True)
        if ret:
            logger.error("Failed to mount the nfs path")
            for i in range(len(out)):
                logger.info(out[i])
            return 1

    return 0

def ownership_get(logger):
    """check the ownership of file"""

    statinfo = os.stat(SAVE_FILE)
    uid = statinfo.st_uid
    gid = statinfo.st_gid

    logger.info("the uid and gid of %s is %s:%s" %(SAVE_FILE, uid, gid))

    return 0, uid, gid

def ownership_test(params):
    """Save a domain to a file, check the ownership of
       the file after save and restore
    """
    # Initiate and check parameters
    params_check_result = check_params(params)
    if params_check_result:
        return 1

    logger = params['logger']
    guestname = params['guestname']
    dynamic_ownership = params['dynamic_ownership']
    use_nfs = params['use_nfs']

    util = utils.Utils()

    # set env
    logger.info("prepare the environment")
    ret = prepare_env(util, dynamic_ownership, use_nfs, logger)
    if ret:
        logger.error("failed to prepare the environment")
        return 1

    # Connect to local hypervisor connection URI
    uri = params['uri']
    conn = connectAPI.ConnectAPI()
    virconn = conn.open(uri)

    # save domain to the file
    logger.info("save domain %s to the file %s" % (guestname, SAVE_FILE))
    domobj = domainAPI.DomainAPI(virconn)

    logger.info("check the domain state")
    ret = check_domain_running(domobj, guestname, logger)
    if ret:
        return return_close(conn, logger, 1)

    try:
        domobj.save(guestname, SAVE_FILE)
        logger.info("Success save domain %s to %s" % (guestname, SAVE_FILE))
    except LibvirtAPI, e:
        logger.error("API error message: %s, error code is %s" % \
                      (e.response()['message'], e.response()['code']))
        logger.error("Error: fail to save domain %s to %s" % \
                      (guestname, SAVE_FILE))
        return return_close(conn, logger, 1)

    logger.info("check the ownership of %s after save" % SAVE_FILE)
    ret, uid, gid = ownership_get(logger)
    if use_nfs == 'enable':
        if uid == 107 and gid == 107:
            logger.info("As expected, the chown not change.")
        else:
            logger.error("The chown of %s is %s:%s, it's not as expected" % \
                             (SAVE_FILE, uid, gid))
            return return_close(conn, logger, 1)
    elif use_nfs == 'disable':
        if dynamic_ownership == 'enable':
            if uid == 0 and gid == 0:
                logger.info("As expected, the chown changed to root:root")
            else:
                logger.error("The chown of %s is %s:%s, it's not as expected" % \
                             (SAVE_FILE, uid, gid))
                return return_close(conn, logger, 1)
        elif dynamic_ownership == 'disable':
            if uid == 107 and gid == 107:
                logger.info("As expected, the chown not change.")
            else:
                logger.error("The chown of %s is %s:%s, it's not as expected" % \
                             (SAVE_FILE, uid, gid))
                return return_close(conn, logger, 1)

    # restore domain from file
    logger.info("restore the domain from the file")
    try:
        domobj.restore(guestname, SAVE_FILE)
        logger.info("Success restore domain %s from %s" % \
                     (guestname, SAVE_FILE))
    except LibvirtAPI, e:
        logger.error("API error message: %s, error code is %s" % \
                      (e.response()['message'], e.response()['code']))
        logger.error("Error: fail to restore domain %s from %s" % \
                      (guestname, SAVE_FILE))
        return return_close(conn, logger, 1)

    logger.info("check the ownership of %s after restore" % SAVE_FILE)
    ret, uid, gid = ownership_get(logger)
    if uid == 107 and gid == 107:
        logger.info("As expected, the chown not change.")
    else:
        logger.error("The chown of %s is %s:%s, not change back as expected" % \
                     (SAVE_FILE, uid, gid))
        return return_close(conn, logger, 1)

    return return_close(conn, logger, 0)

def ownership_test_clean(params):
    """clean testing environment"""
    logger = params['logger']
    use_nfs = params['use_nfs']

    util = utils.Utils()

    if use_nfs == 'enable':
        if os.path.ismount("/mnt"):
            umount_cmd = "umount /mnt"
            ret, out = util.exec_cmd(umount_cmd, shell=True)
            if ret:
                logger.error("Failed to unmount the nfs path")
                for i in range(len(out)):
                    logger.error(out[i])

        clean_nfs_conf = "sed -i '$d' /etc/exports"
        util.exec_cmd(clean_nfs_conf, shell=True)

        filepath = TEMP_FILE
    elif use_nfs == 'disable':
        filepath = SAVE_FILE

    if os.path.exists(filepath):
        os.remove(filepath)

    clean_qemu_conf = "sed -i '$d' %s" % QEMU_CONF
    util.exec_cmd(clean_qemu_conf, shell=True)

    cmd = "service libvirtd restart"
    util.exec_cmd(cmd, shell=True)

    return 0
