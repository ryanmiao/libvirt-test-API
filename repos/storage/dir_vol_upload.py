#!/usr/bin/env python
# dir storage volume upload testing, only raw format volume is
# supported, other format might fail. offset and length can
# only be chosen in 0 and 1048576.

import os
import string
from xml.dom import minidom

import libvirt
from libvirt import libvirtError

from src import sharedmod
from utils import utils

required_params = ('poolname', 'volname', 'volformat', 'capacity',
                   'offset', 'length',)
optional_params = {'xml' : 'xmls/dir_volume.xml',
                  }

def get_pool_path(poolobj):
    """ get pool xml description
    """
    poolxml = poolobj.XMLDesc(0)

    logger.debug("the xml description of pool is %s" % poolxml)

    doc = minidom.parseString(poolxml)
    path_element = doc.getElementsByTagName('path')[0]
    textnode = path_element.childNodes[0]
    path_value = textnode.data

    return path_value

def write_file(path):
    """write 1M test data to file
    """
    logger.info("write data into file %s" % path)
    f = open(path, 'w')
    datastr = ''.join(string.lowercase + string.uppercase
                      + string.digits + '.' + '\n')
    data = ''.join(16384 * datastr)
    f.write(data)
    f.close()

def handler(stream, data, file_):
    return file_.read(data)

def dir_vol_upload(params):
    """test volume download and check"""

    global logger
    logger = params['logger']
    poolname = params['poolname']
    volname = params['volname']
    volformat = params['volformat']
    offset = int(params['offset'])
    length = int(params['length'])
    capacity = params['capacity']
    xmlstr = params['xml']

    logger.info("the poolname is %s, volname is %s, volformat is %s" %
                (poolname, volname, volformat))
    logger.info("upload offset is: %s" % offset)
    logger.info("the data length to upload is: %s" % length)

    conn = sharedmod.libvirtobj['conn']
    try:
        poolobj = conn.storagePoolLookupByName(poolname)
        path_value = get_pool_path(poolobj)
        volume_path = path_value + "/" + volname

        xmlstr = xmlstr.replace('VOLPATH', volume_path)
        xmlstr = xmlstr.replace('SUFFIX', capacity[-1])
        xmlstr = xmlstr.replace('CAP', capacity[:-1])
        logger.debug("volume xml:\n%s" % xmlstr)

        logger.info("create %s %s volume" % (volname, volformat))
        vol = poolobj.createXML(xmlstr, 0)

        test_path = path_value + "/" + "vol_test"
        write_file(test_path)
        olddigest = utils.digest(test_path, 0, 0)
        logger.debug("the old file digest is: %s" % olddigest)

        if offset:
            origdigestpre = utils.digest(volume_path, 0, offset)
        else:
            origdigestpre = ''
        logger.debug("the original pre region digest is: %s" % origdigestpre)

        origdigestpost = utils.digest(volume_path, offset + 1024 * 1024, 0)
        logger.debug("the original post region digest is: %s" % origdigestpost)

        st = conn.newStream(0)

        f = open(test_path, 'r')
        logger.info("start upload")
        vol.upload(st, offset, length, 0)
        logger.info("sent all data")
        st.sendAll(handler, f)
        logger.info("finished stream")
        st.finish()
        f.close()

        newdigest = utils.digest(volume_path, offset, 1024 * 1024)
        logger.debug("the new file digest is: %s" % olddigest)

        if offset:
            newdigestpre = utils.digest(volume_path, 0, offset)
        else:
            newdigestpre = ''
        logger.debug("the new pre region digest is: %s" % origdigestpre)

        newdigestpost = utils.digest(volume_path, offset + 1024 * 1024, 0)
        logger.debug("the new post region digest is: %s" % origdigestpost)

        if newdigestpre == origdigestpre:
            logger.info("file pre region digests match")
        else:
            logger.error("file pre region digests not match")
            return 1

        if olddigest == newdigest:
            logger.info("file digests match")
        else:
            logger.error("file digests not match")
            return 1

        if newdigestpost == origdigestpost:
            logger.info("file post region digests match")
        else:
            logger.error("file post region digests not match")
            return 1

    except libvirtError, e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    return 0

def dir_vol_upload_clean(params):
    """clean testing environment"""
    poolname = params['poolname']
    volname = params['volname']

    conn = sharedmod.libvirtobj['conn']
    poolobj = conn.storagePoolLookupByName(poolname)
    path_value = get_pool_path(poolobj)
    test_path = path_value + "/" + "vol_test"

    vol = poolobj.storageVolLookupByName(volname)
    vol.delete(0)

    if os.path.exists(test_path):
        os.unlink(test_path)

    return 0
