#!/usr/bin/python

"""A widget for displaying infomation.

Info -- display messages and errors
Author: J.Cupitt
Created as part of the AHRC RTI project in 2011
GNU LESSER GENERAL PUBLIC LICENSE
"""

import logging

import pygtk
pygtk.require('2.0')
import gtk
import glib

# how long to keep the bar visible, in milliseconds
info_timeout = 5000

class Info(gtk.InfoBar):

    """Display messages and errors.

    The widget hides itself after a short delay and is less obtrusive than a
    popup dialog box. 
    
    Messages come in two parts: a high-level summary, and a detailed
    description.
    """

    def hide_cb(self, widget, response_id, client):
        self.hide()

    def __init__(self):
        gtk.InfoBar.__init__(self)

        self.hide_timeout = 0
    
        content = self.get_content_area()

        self.label = gtk.Label()
        content.pack_start(self.label, False, False)
        self.label.show()

        self.add_button('Close', 0)
        self.connect('response', self.hide_cb, None)

    def timeout_cb(self):
        self.hide_timeout = 0
        self.hide()
        return False

    def pop(self):
        self.show()
        if self.hide_timeout:
            glib.source_remove(self.hide_timeout)
            self.hide_timeout = 0
        self.hide_timeout = glib.timeout_add(info_timeout, self.timeout_cb)

    def set_msg(self, main, sub):
        self.label.set_markup('<b>%s</b>\n%s' % (main, sub))

    def msg(self, main, sub):
        """Display an informational message.

        main -- a summary of the message
        sub -- message details
        """
        self.set_msg(main, sub)
        logging.debug('info: %s, %s', main, sub)
        self.set_message_type(gtk.MESSAGE_INFO)
        self.pop()

    def err(self, main, sub):
        """Display an error message.

        main -- a summary of the error
        sub -- error details
        """
        self.set_msg(main, sub)
        logging.error('error: %s, %s', main, sub)
        self.set_message_type(gtk.MESSAGE_ERROR)
        self.pop()


