#!/usr/bin/python

"""This module wraps up jpeg decompression in a nice interface.

This module makes use of a small C library built from dejpeg.c. See comments
in there for build instructions.

bufjpeg2pixbuf -- decompress a jpeg from a memory area to a gtk.gdk.Pixbuf
Author: J.Cupitt
Created as part of the AHRC RTI project in 2011
GNU LESSER GENERAL PUBLIC LICENSE
"""

import logging
import ctypes
import os

import pygtk
pygtk.require('2.0')
import gtk

import finalize

# get the directory this source is in
source_dir = os.path.dirname(__file__)

# Load library
decompress = ctypes.CDLL(os.path.join(source_dir, 'dejpeg.so'))

class Image(ctypes.Structure):
    _fields_ = [('width', ctypes.c_int),
                ('height', ctypes.c_int),
                ('pixels', ctypes.c_void_p)]

def finalize_image(image):
    logging.debug('finalizing image %s', repr(image))
    decompress.image_free(ctypes.byref(image))

def bufjpeg2pixbuf(data, length):

    """Decompress to a Pixbuf.

    Decompress the jpeg held in the memory area indicated by(data, length),
    construct a gtk.gdk.Pixbuf, and return it.

    """

    logging.debug('decompress: starting ...')
    image = Image()
    retval = decompress.decompress(data, length, ctypes.byref(image))
    if retval != 0:
        logging.error('decompress failed')
        finalize_image(image)
        return 
    logging.debug('decompress: done')

    logging.debug('decompress: read %d x %d pixel image', 
                    image.width, image.height)
    string = ctypes.string_at(image.pixels, image.width * image.height * 3)

    pixbuf = gtk.gdk.pixbuf_new_from_data(string, 
                gtk.gdk.COLORSPACE_RGB, False, 8, 
                image.width, image.height, image.width * 3)

    finalize.track(pixbuf, image, finalize_image)

    return pixbuf

