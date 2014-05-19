#!/usr/bin/env python
# test libvirt cpu baseline

import libvirt
from libvirt import libvirtError

from src import sharedmod
from xml.dom import minidom

required_params = ('arch', 'model', 'vendor', 'feature', 'required_feature',)
optional_params = {'conn': '', 'disabled_feature': '',
                   'xml': 'xmls/cpu.xml', }


def parse_arguments(args):
    """ parse the arguments
    """
    return [s.strip() for s in args.split('|')]


def append_features(xmlstr, feature):
    """ append all features to xml
    """
    doc = minidom.parseString(xmlstr)
    cpu = doc.getElementsByTagName('cpu')[0]
    for e in feature:
        cpu_feature = doc.createElement('feature')
        cpu_feature.setAttribute('name', e)
        cpu.appendChild(cpu_feature)

    return doc.toxml()


def get_features_from(feature_type, xmlstr, logger):
    """ get features from xmlstr
    """
    doc = minidom.parseString(xmlstr)
    cpus = doc.getElementsByTagName('cpu')
    outputs = cpus[0].getElementsByTagName('feature')
    ret = []
    for i in outputs:
        if not i.hasAttribute('policy'):
            logger.error("baselineCPU returns xml without policy attribute")
            return ret
        if not i.hasAttribute('name'):
            logger.error("baselineCPU returns xml without name attribute")
            return ret
        if i.getAttributeNode('policy').nodeValue == feature_type:
            ret.append(i.getAttributeNode('name').nodeValue)
    return ret


def check_features(src, target, logger):
    """ check returned required features
    """
    if not len(src) == len(target):
        logger.error("the numbers of features are inconsistent")
        return False
    for s in src:
        if s in target:
            logger.debug("the feature %s is found" % s)
        else:
            logger.error("the feature %s is not found" % s)
            return False
    return True


def cpu_baseline(params):
    """ test libvirt cpu baseline
        'feature' is a parament indicates which feature is on
        'required_feature' indicates which feature is required based on input
        'disabled_feature' indicates which feature is disabled based on input
    """
    logger = params['logger']

    feature = parse_arguments(params['feature'])
    required_feature = parse_arguments(params['required_feature'])
    disabled_feature = parse_arguments(params.get('disabled_feature', ''))
    xmlstr = params['xml']

    try:
        # get connection firstly.
        # If conn is not specified, use conn from sharedmod
        if 'conn' in params:
            conn = libvirt.open(params['conn'])
        else:
            conn = sharedmod.libvirtobj['conn']

        logger.info("feature: %s" % feature)
        logger.info("required_feature: %s" % required_feature)
        logger.info("disabled_feature: %s" % disabled_feature)

        xmlstr = append_features(xmlstr, feature)
        logger.info("append features to xml:\n%s" % xmlstr)

        retxml = conn.baselineCPU([xmlstr], 0)
        logger.info("baselineCPU returns:\n%s" % retxml)

        ret_required = get_features_from('require', retxml, logger)
        logger.info("returned required features are: %s" % ret_required)

        if check_features(required_feature, ret_required, logger):
            logger.info("check returned required feature pass")
        else:
            logger.error("check returned required feature fails")
            return 1

        ret_disabled = get_features_from('disable', retxml, logger)
        logger.info("returned disabled features are: %s" % ret_disabled)

        if check_features(disabled_feature, ret_disabled, logger):
            logger.info("check returned disabled feature pass")
        else:
            logger.error("check returned disabled feature fails")
            return 1

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s" %
                     e.message)
        return 1

    return 0
