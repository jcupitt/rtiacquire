#!/usr/bin/python

"""Load and query the led-map.txt file.

Ledmap -- a loaded LED map file
Author: J.Cupitt
GNU LESSER GENERAL PUBLIC LICENSE
"""

import re
import logging

class Ledmap:

    """A loaded LED map file.

    get_names -- return a list of the names of the maps
    get_bytes -- get bytes to send to set a light pattern
    """

    def __init__(self, filename):

        """Load up the LED map file.

        filename -- file to load, usually 'led-map.txt'

        The file contains one or more sections. A section starts with a line
        of the form "** section-name **", where section-name may be any
        string. Section names may not be repeated in the file.

        Subsequent lines list byte hex triples to send to the light controller
        to light a set of LEDs. They have the form "0x12, 0xfe, 0xff". The
        "0x" is optional. The numbers may be separated by comma, space or tab.

        Blank lines are ignored.

        Errors are reported to logging.

        """

        logging.debug('Ledmap: loading %s ...', filename)

        # a hash from a map name to a list of byte triples
        self.maps = {}

        # a list of map names, in the order they appear in the led map file
        self.names = []

        current_name = None
        lineno = 0
        for line in open(filename):
            lineno += 1

            match = re.match(r"\s*\*\*\s*(.+?)\s*\*\*\s*", line)
            if match != None:
                current_name = match.group(1)
                if current_name in self.maps:
                    logging.error('%s:%d: repeated name', filename, lineno)
                    continue
                self.maps[current_name] = []
                self.names += [current_name]
                continue

            byte = r"(0x)?[A-Fa-f0-9]{2}"
            patt = "\s*(%s)[ ,\t]+(%s)[ ,\t]+(%s)\s*" %(byte, byte, byte)
            match = re.match(patt, line)
            if match != None:
                if current_name == None:
                    logging.error('%s:%d: triple with no name', 
                                    filename, lineno)
                    continue
                A = int(match.group(1), 16)
                B = int(match.group(3), 16)
                C = int(match.group(5), 16)
                self.maps[current_name] += [[A, B, C]]
                continue

            if re.match(r"\s*", line):
                continue

            logging.error('%s:%d: parse error', filename, lineno)

    def get_names(self):
        """Return a list of section names."""
        return self.names

    def get_bytes(self, name):
        """Return an array of light patterns. 
        
        Each array element is itself a 3-element list of numbers to send 
        to the controller.
        """
        return self.maps[name]
