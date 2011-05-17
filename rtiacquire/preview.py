#!/usr/bin/python

"""A widget for displaying a live preview image.

Preview -- a gtk.Image displaying a live camera preview
Author: J.Cupitt
Created as part of the AHRC RTI project in 2011
GNU LESSER GENERAL PUBLIC LICENSE
"""

import logging

import pygtk
pygtk.require('2.0')
import gtk
import glib

import decompress 

# inter-frame delay, in milliseconds
# 50 gives around 20 fps and doesn't overload the machine too badly
frame_timeout = 50

class Preview (gtk.Image):

    """A widget displaying a live preview.

    get_live -- return True if the preview is currently live
    set_live -- turn the live preview on and off
    """

    def __init__ (self, camera):
        """
        Startup.

        camera -- the camera to display, see camera.py

        The preview starts at 640x426 pixels, this may change if the camera
        turns out to have a different size for its preview image.
        """

        gtk.Image.__init__ (self)

        # start with a blank 640x426 image, we overwrite this with jpg from
        # the camera during live preview
        self.pixbuf = gtk.gdk.Pixbuf (gtk.gdk.COLORSPACE_RGB, 
                        False, 8, 640, 426)
        self.set_from_pixbuf (self.pixbuf)

        self.preview_timeout = 0

        self.camera = camera

        self.frame = 0

    def grab_frame (self):
        logging.debug ('grabbing frame ..')
        frame = self.camera.preview ()
        if frame == None:
            return
        (data, length) = frame
        if length.value == 0:
            return

        pixbuf = decompress.bufjpeg2pixbuf (data, length)
        if pixbuf != None:
            self.pixbuf = pixbuf
            self.set_from_pixbuf (pixbuf)
            self.frame += 1

    def get_live (self):
        """Return True if the display is currently live."""
        return self.preview_timeout != 0

    def live_cb (self):
        self.grab_frame ()
        return True

    def fps_cb (self):
        logging.debug ('fps = %d', self.frame)
        self.frame = 0
        return True

    def set_live (self, live):
        """Turn the live preview on and off.

        live -- True means start the live preview display
        """
        if live and self.preview_timeout == 0:
            logging.debug ('starting timeout ..')
            self.preview_timeout = glib.timeout_add (frame_timeout, 
                            self.live_cb)
            self.fps_timeout = glib.timeout_add (1000, self.fps_cb)
        elif not live and self.preview_timeout != 0:
            glib.source_remove (self.preview_timeout)
            self.preview_timeout = 0
            glib.source_remove (self.fps_timeout)
            self.fps_timeout = 0

        if live:
            # grab a frame immediately so we can get an exception, if there
            # are any
            self.grab_frame ()

