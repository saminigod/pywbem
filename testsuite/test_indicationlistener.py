#!/usr/bin/env python

"""Test WBEMListener against an indication generator. This test generates
   a number of indications and confirms that they are all received by the
   listener.

   This test validates the main paths of the listener and that the listener can
   receive large numbers of insdications without duplicates or dropping
   indications.

   It does not validate all of the possible xml options on indications.
"""

from __future__ import absolute_import

import unittest
import sys as _sys
import logging as _logging
from time import time
import datetime
from random import randint
import requests

from pywbem import WBEMListener

RCV_COUNT = 0
RCV_FAIL = False
VERBOSE = False
LISTENER = None

class ElapsedTimer(object):
    """
        Set up elapsed time timer. Calculates time between initiation
        and access.
    """
    def __init__(self):
        """ Initiate the object with current time"""
        self.start_time = datetime.datetime.now()

    def reset(self):
        """ Reset the start time for the timer"""
        self.start_time = datetime.datetime.now()

    def elapsed_ms(self):
        """ Get the elapsed time in milliseconds. returns floating
            point representation of elapsed time in seconds.
        """
        dt = datetime.datetime.now() - self.start_time
        return ((dt.days * 24 * 3600) + dt.seconds) * 1000  \
                + dt.microseconds / 1000.0

    def elapsed_sec(self):
        """ get the elapsed time in seconds. Returns floating
            point representation of time in seconds
        """
        return self.elapsed_ms() / 1000

def create_indication_data(msg_id, sequence_number, delta_time, protocol_ver):
    """Create a test indication from the template and input attributes"""

    data_template = """<?xml version="1.0" encoding="utf-8" ?>
    <CIM CIMVERSION="2.0" DTDVERSION="2.4">
      <MESSAGE ID="%(msg_id)s" PROTOCOLVERSION="%(protocol_ver)s">
        <SIMPLEEXPREQ>
          <EXPMETHODCALL NAME="ExportIndication">
            <EXPPARAMVALUE NAME="NewIndication">
              <INSTANCE CLASSNAME="CIM_AlertIndication">
                <PROPERTY NAME="Severity" TYPE="string">
                  <VALUE>high</VALUE>
                </PROPERTY>
                <PROPERTY NAME="SequenceNumber" TYPE="string">
                  <VALUE>%(sequence_number)s</VALUE>
                </PROPERTY>
                <PROPERTY NAME="DELTA_TIME" TYPE="string">
                  <VALUE>%(delta_time)s</VALUE>
                </PROPERTY>
              </INSTANCE>
            </EXPPARAMVALUE>
          </EXPMETHODCALL>
        </SIMPLEEXPREQ>
      </MESSAGE>
    </CIM>"""

    data = {'sequence_number': sequence_number, 'delta_time': delta_time,
            'protocol_ver': protocol_ver, 'msg_id': msg_id}
    return data_template%data

def send_indication(url, headers, payload, verbose):
    """Send a single indication using Python requests"""

    try:
        response = requests.post(url, headers=headers, data=payload, timeout=4)
    except Exception as ex:
        print('Exception %s' % ex)
        return False

    if verbose:
        print('\nResponse code=%s headers=%s data=%s' % (response.status_code,
                                                         response.headers,
                                                         response.text))

    return True if(response.status_code == 200) else False

def _process_indication(indication, host):
    """
    This function gets called when an indication is received.
    It receives each indication on a separate thread so the only communication
    with the rest of the program is RCV_COUNT which it increments for each
    received indication

    It tests the received indication sequence number against the RCV_COUNT
    which should catch and indication duplication or missing since the counters
    would no longer match.

    NOTE: Since this is a standalone function, it does not do an assert fail
    if there is a mismatch.
    """

    global RCV_COUNT
    global RCV_FAIL

    counter = indication.properties['SequenceNumber'].value
    if int(counter) != RCV_COUNT:
        RCV_FAIL = True
        print('ERROR in process indication counter=%s, COUNT=%s' % (counter,
                                                                    RCV_COUNT))
    #print('counter %s COUNT %s' % (counter, RCV_COUNT))
    RCV_COUNT += 1
    if VERBOSE:
        print("Received indication %s from %s:\n%s" % (RCV_COUNT, host,
                                                       indication.tomof()))

class TestIndications(unittest.TestCase):
    """
    Create a WBEMListener and starts the listener. Note that it resets the
    received indication counter (RCV_COUNT) so that there is an accurate
    count of indications actually received.
    """

    @staticmethod
    def createlistener(host, http_port=None, https_port=None,
                       certfile=None, keyfile=None):

        global RCV_COUNT
        global LISTENER
        global RCV_FAIL
        RCV_FAIL = False

        _logging.basicConfig(stream=_sys.stderr, level=_logging.WARNING,
                             format='%(levelname)s: %(message)s')

        RCV_COUNT = 0
        LISTENER = WBEMListener(host=host,
                                http_port=http_port,
                                https_port=https_port,
                                certfile=certfile,
                                keyfile=keyfile)
        LISTENER.add_callback(_process_indication)
        LISTENER.start()

    def send_indications(self, send_count, http_port, https_port):
        """
        Send the number of indications defined by the send_count attribute
        Creates the listener, starts the listener, creates the
        indication XML and adds sequence number and time to the
        indication instance and sends that instance using requests.
        The indication instance is modified for each indication count so
        that each carries its own sequence number
        """

        #pylint: disable=global-variable-not-assigned
        global VERBOSE
        global RCV_FAIL
        RCV_FAIL = False
        host = 'localhost'

        self.createlistener(host, http_port)

        start_time = time()

        full_url = 'http://%s:%s' % (host, http_port)

        if VERBOSE:
            print('full_url=%s' % full_url)

        cim_protocol_version = '1.4'

        headers = {'content-type': 'application/xml; charset=utf-8',
                   'CIMExport': 'MethodRequest',
                   'CIMExportMethod': 'ExportIndication',
                   'Accept-Encoding': 'Identity',
                   'CIMProtocolVersion': cim_protocol_version}
        # includes accept-encoding because of requests issue.
        #He supplies it if don't TODO try None

        delta_time = time() - start_time
        rand_base = randint(1, 10000)
        timer = ElapsedTimer()
        for i in range(send_count):

            msg_id = '%s' % (i + rand_base)
            payload = create_indication_data(msg_id, i, delta_time,
                                             cim_protocol_version)

            if VERBOSE:
                print('headers=%s\n\npayload=%s' % (headers, payload))

            success = send_indication(full_url, headers, payload, VERBOSE)

            if success:
                if VERBOSE:
                    print('sent # %s' % i)
            else:
                self.fail('Error return from send. Terminating.')

        endtime = timer.elapsed_sec()
        print('Sent %s in %s sec or %.2f ind/sec' % (send_count, endtime,
                                                     (send_count/endtime)))

        self.assertEqual(send_count, RCV_COUNT,
                         'Mismatch between sent and rcvd')
        self.assertFalse(RCV_FAIL, 'Sequence numbers do not match')
        RCV_FAIL = False
        LISTENER.stop()

#TODO issue 452. Reuse of the indication listener fails at least in python 3
# Therefore we use different port for each test
    def test_send_10(self):
        """Test with sending 10 indications"""
        self.send_indications(10, 5000, None)

    def test_send_100(self):
        """Test sending 100 indications"""
        self.send_indications(100, 5001, None)

    # Disabled the following test, because in some environments it takes 30min.
    #def test_send_1000(self):
    #    """Test sending 1000 indications"""
    #    self.send_indications(1000, 5002, None)

#    This test takes about 60 seconds and so is disabled for now
#    def test_send_10000(self):
#        self.send_indications(10000)

if __name__ == '__main__':
    VERBOSE = False
    unittest.main()
