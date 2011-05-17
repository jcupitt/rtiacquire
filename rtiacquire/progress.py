#!/usr/bin/python

"""A widget for displaying progress feedback.

Progress -- display progress feedback
Author: J.Cupitt
Created as part of the AHRC RTI project in 2011
GNU LESSER GENERAL PUBLIC LICENSE
"""

import pygtk
pygtk.require('2.0')
import gtk
import glib

class Progress (gtk.InfoBar):
    def cancel_cb (self, widget, response_id, client):
        self.cancel = True

    def __init__ (self):
        gtk.InfoBar.__init__ (self)

        self.cancel = False
    
        content = self.get_content_area ()

        self.progressbar = gtk.ProgressBar ()
        content.pack_start (self.progressbar, True, True)
        self.progressbar.show ()

        self.add_button ('Cancel', 0)
        self.connect ('response', self.cancel_cb, None)

    def start (self, message):
        """Start an operation that needs progress feedback.

        message -- the message to display during the operation
        """
        self.progressbar.set_text (message)
        self.progressbar.set_fraction (0)
        self.show ()

    def progress (self, fraction):
        """Feedback during the operation.

        fraction -- a value in the range [0, 1] indicating progress

        Return True if the user has requested cancellation.

        This method must be called every few tens of milliseconds to avoid
        locking the UI.
        """
        self.progressbar.set_fraction (fraction)
        while gtk.events_pending ():
            gtk.main_iteration ()

        return self.cancel

    def stop (self):
        """End of operation.

        The progress bar is hidden again.
        """
        self.hide ()
        self.cancel = False


