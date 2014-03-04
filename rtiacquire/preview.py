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
import rect 

# inter-frame delay, in milliseconds
# 50 gives around 20 fps and doesn't overload the machine too badly
frame_timeout = 50

# width of selection box border
select_width = 3

# size of corner resize boxes
select_corner = 15

# we have a small state machine for manipulating the select box
def enum(**enums):
    return type('Enum', (), enums)
SelectState = enum(WAIT = 1, DRAG = 2, RESIZE = 3)

# For each edge direction, the corresponding cursor we select
resize_cursor_shape = {
    rect.Edge.NW:   gtk.gdk.Cursor(gtk.gdk.TOP_LEFT_CORNER),
    rect.Edge.NE:   gtk.gdk.Cursor(gtk.gdk.TOP_RIGHT_CORNER),
    rect.Edge.SW:   gtk.gdk.Cursor(gtk.gdk.BOTTOM_LEFT_CORNER),
    rect.Edge.SE:   gtk.gdk.Cursor(gtk.gdk.BOTTOM_RIGHT_CORNER),
    rect.Edge.N:    gtk.gdk.Cursor(gtk.gdk.TOP_SIDE),
    rect.Edge.S:    gtk.gdk.Cursor(gtk.gdk.BOTTOM_SIDE),
    rect.Edge.E:    gtk.gdk.Cursor(gtk.gdk.RIGHT_SIDE),
    rect.Edge.W:    gtk.gdk.Cursor(gtk.gdk.LEFT_SIDE)
}

# another cursor for grag
drag_cursor_shape = gtk.gdk.Cursor(gtk.gdk.FLEUR)

class Preview(gtk.EventBox):

    """A widget displaying a live preview.

    get_live -- return True if the preview is currently live
    set_live -- turn the live preview on and off
    """

    # expose on our gtk.Image
    def expose_event(self, widget, event):
        window = self.image.get_window()

        if not self.gc:
            self.gc = gtk.gdk.Drawable.new_gc(window,
                                               gtk.gdk.Color("white"),
                                               gtk.gdk.Color("black"),
                                               None,            # font
                                               gtk.gdk.COPY,
                                               gtk.gdk.SOLID,
                                               None,            # tile
                                               None,            # stipple
                                               None,            # clip
                                               gtk.gdk.INCLUDE_INFERIORS,
                                               0, 0,
                                               0, 0,
                                               False,
                                               0,               # 1 pixel width
                                               gtk.gdk.LINE_SOLID,
                                               gtk.gdk.CAP_NOT_LAST,
                                               gtk.gdk.JOIN_MITER) 

        if self.visible:
            window.draw_rectangle(self.gc, True,
                                   self.area.left - select_width, 
                                   self.area.top - select_width, 
                                   self.area.width + select_width * 2, 
                                   select_width)
            window.draw_rectangle(self.gc, True,
                                   self.area.right(), 
                                   self.area.top, 
                                   select_width,
                                   self.area.height) 
            window.draw_rectangle(self.gc, True,
                                   self.area.left - select_width, 
                                   self.area.bottom(), 
                                   self.area.width + select_width * 2, 
                                   select_width)
            window.draw_rectangle(self.gc, True,
                                   self.area.left - select_width, 
                                   self.area.top, 
                                   select_width,
                                   self.area.height)

        return False

    def button_press_event(self, widget, event):
        x = int(event.x)
        y = int(event.y)
        outer = self.area.clone()
        outer.margin_adjust(select_width * 2)

        if self.select_state == SelectState.WAIT and \
            self.visible and \
            self.area.includes_point(x, y):
            self.select_state = SelectState.DRAG
            self.drag_x = x - self.area.left
            self.drag_y = y - self.area.top
            self.queue_draw()
        elif self.select_state == SelectState.WAIT and \
            self.visible and \
            not self.area.includes_point(x, y) and \
            outer.includes_point(x, y):
            self.select_state = SelectState.RESIZE
            self.resize_direction = self.area.which_corner(select_corner, x, y)
            corner = self.area.corner(self.resize_direction)
            (cx, cy) = corner.centre()
            self.drag_x = x - cx
            self.drag_y = y - cy
            self.queue_draw()
        elif self.select_state == SelectState.WAIT and \
            self.visible:
            self.visible = False
            self.queue_draw()
        elif self.select_state == SelectState.WAIT and \
            not self.visible:
            self.visible = True
            self.area.left = x
            self.area.top = y
            self.area.width = 1
            self.area.height = 1
            self.select_state = SelectState.RESIZE
            self.resize_direction = rect.Edge.SE
            self.drag_x = 1
            self.drag_y = 1
            self.queue_draw()

    def motion_notify_event(self, widget, event):
        x = int(event.x)
        y = int(event.y)

        if self.select_state == SelectState.DRAG:
            self.area.left = x - self.drag_x
            self.area.top = y - self.drag_y
            self.queue_draw()
        elif self.select_state == SelectState.RESIZE:
            corner = self.area.corner(self.resize_direction)
            (cx, cy) = corner.centre()

            if self.resize_direction in [rect.Edge.SE, rect.Edge.E,
                                         rect.Edge.NE]:
                right = x - self.drag_x
                self.area.width = right - self.area.left

            if self.resize_direction in [rect.Edge.SW, rect.Edge.S,
                                         rect.Edge.SE]:
                bottom = y - self.drag_y
                self.area.height = bottom - self.area.top

            if self.resize_direction in [rect.Edge.SW, rect.Edge.W,
                                         rect.Edge.NW]:
                left = x - self.drag_x
                self.area.width = self.area.right() - left
                self.area.left = left

            if self.resize_direction in [rect.Edge.NW, rect.Edge.N,
                                         rect.Edge.NE]:
                top = y - self.drag_y
                self.area.height = self.area.bottom() - top
                self.area.top = top

            self.area.normalise()
            self.queue_draw()
        else:
            window = self.image.get_window()
            outer = self.area.clone()
            outer.margin_adjust(select_width * 2)
            if self.visible and \
                self.area.includes_point(x, y):
                window.set_cursor(drag_cursor_shape)
            elif self.visible and \
                not self.area.includes_point(x, y) and \
                outer.includes_point(x, y):
                edge = self.area.which_corner(select_corner, x, y)
                window.set_cursor(resize_cursor_shape[edge])
            else:
                window.set_cursor(None)

    def button_release_event(self, widget, event):
        if self.select_state == SelectState.DRAG:
            self.select_state = SelectState.WAIT
        elif self.select_state == SelectState.RESIZE:
            self.select_state = SelectState.WAIT

    def __init__(self, camera):
        """
        Startup.

        camera -- the camera to display, see camera.py

        The preview starts at 640x426 pixels, this may change if the camera
        turns out to have a different size for its preview image.
        """

        gtk.EventBox.__init__(self)

        self.image = gtk.Image()
        self.add(self.image)
        self.image.show()

        # start with a blank 640x426 image, we overwrite this with jpg from
        # the camera during live preview
        self.pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, 
                                     False, 8, 640, 426)
        self.image.set_from_pixbuf(self.pixbuf)

        self.preview_timeout = 0

        self.camera = camera

        self.frame = 0

        self.image.set_app_paintable(True)

        self.gc = None

        self.visible = True
        self.area = rect.Rect(10, 10, 100, 100)
        self.select_state = SelectState.WAIT
        self.resize_direction = rect.Edge.N

        self.image.connect_after('expose-event', self.expose_event)

        self.add_events(gtk.gdk.POINTER_MOTION_MASK)
        self.connect('button-press-event', self.button_press_event)
        self.connect('motion-notify-event', self.motion_notify_event)
        self.connect('button-release-event', self.button_release_event)

    def grab_frame(self):
        logging.debug('grabbing frame ..')
        frame = self.camera.preview()
        if frame == None:
            return
        (data, length) = frame
        if length.value == 0:
            return

        pixbuf = decompress.bufjpeg2pixbuf(data, length)
        if pixbuf != None:
            self.pixbuf = pixbuf
            self.image.set_from_pixbuf(pixbuf)
            self.frame += 1

    def get_live(self):
        """Return True if the display is currently live."""
        return self.preview_timeout != 0

    def live_cb(self):
        self.grab_frame()
        return True

    def fps_cb(self):
        logging.debug('fps = %d', self.frame)
        self.frame = 0
        return True

    def set_live(self, live):
        """Turn the live preview on and off.

        live -- True means start the live preview display
        """
        if live and self.preview_timeout == 0:
            logging.debug('starting timeout ..')
            self.preview_timeout = glib.timeout_add(frame_timeout, 
                            self.live_cb)
            self.fps_timeout = glib.timeout_add(1000, self.fps_cb)
        elif not live and self.preview_timeout != 0:
            glib.source_remove(self.preview_timeout)
            self.preview_timeout = 0
            glib.source_remove(self.fps_timeout)
            self.fps_timeout = 0

        if live:
            # grab a frame immediately so we can get an exception, if there
            # are any
            self.grab_frame()

