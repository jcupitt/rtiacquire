#!/usr/bin/python

"""This module wraps up communication with the light controller.

Lights -- a connection to the light controller
Error -- the exception we can raise

Author: J.Cupitt
Created as part of the AHRC RTI project in 2011
GNU LESSER GENERAL PUBLIC LICENSE
"""

import os
import serial
import time
import logging

class Error(Exception):

    """An error from the lights.

    message -- a high-level description of the error
    detail -- a string with some detailed diagnostics
    """

    def __init__(self, message, detail):
        self.message = message
        self.detail = detail

        logging.debug('lights: %s', repr(self))

    def __str__(self):
        return '%s - %s' %(self.message, self.detail)

# where we look for the light controller, in order
#   /dev/ttyUSB0    
#       when you plug the light controller in on Ubuntu, this dev
#       appears ... normally it's USB0 but I guess if the machine has other
#       generic USB devices, it could appear as higher numbers

light_ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2']

class Lights:
    def __init__(self):
        """Startup.

        The connection to the light controller is made automatically on the
        first call to the set_triple() method.
        """
        self.port = None

    def try_port(self, portname):
        logging.debug('** trying port %s', portname) 

        try:
            port = serial.Serial(portname, 38400, timeout = 0.1)
        except serial.SerialException as e:
            raise Error('Unable to connect to lights', str(e))

        time.sleep(1)
        port.write('?')
        resp = port.readline()
        if resp != 'USB I/O 24R1\r\n':
            port.close()
            raise Error('Unable to connect to lights', 
                'Bad response received - %s' % resp)

        # init ports
        port.write("!")
        port.write("A")
        port.write(chr(0))
        port.write("!")
        port.write("B")
        port.write(chr(0))
        port.write("!")
        port.write("C")
        port.write(chr(0))

        logging.debug('** successful connection to lights on port %s', 
                        portname) 

        return port

    # open the connection
    def connect(self):
        if self.port == None:
            logging.debug('** lights init')
            for portname in light_ports:
                try:
                    port = self.try_port(portname)
                except Exception as e:
                    logging.debug('** error on %s, %s', portname, str(e)) 
                else:
                    logging.debug('** lights found on %s', portname)
                    break
            else:
                raise Error('No lights found', 
                    'No light controller found on any port')

            self.port = port

    def release(self):
        if self.port != None:
            logging.debug('** lights shutdown')
            self.set_triple([0, 0, 0])
            self.port.close()
            self.port = None

    def set_triple(self, triple):
        """Send a triple to the light contoller.

        triple -- three bytes as [a, b, c] to send to the three channels

        This method can raise Error if no controller can be found or a
        connection error occurs.
        """

        A, B, C = triple

        self.connect()

        logging.debug('** lights A = %s, B = %s, C = %s', 
                        hex(A), hex(B), hex(C))

        self.port.write("A")
        self.port.write(chr(A))
        self.port.write("B")
        self.port.write(chr(B))
        self.port.write("C")
        self.port.write(chr(C))

