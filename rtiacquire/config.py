#!/usr/bin/python

"""Display camera config.

Config -- display and edit camera config
Author: J.Cupitt
Created as part of the AHRC RTI project in 2011
GNU LESSER GENERAL PUBLIC LICENSE
"""

import logging
import pickle
import os

import pygtk
pygtk.require('2.0')
import gtk
import glib

import camera

# how long to keep the bar visible, in milliseconds
info_timeout = 5000

class Config(gtk.Window):
    """Display and edit the camera config."""

    def destroy_cb(self, widget, data = None):
        if self.refresh_timeout:
            glib.source_remove(self.refresh_timeout)
            self.refresh_timeout = 0
        self.presets_save(os.path.join(self.options.tempdir, 'settings'))
        self.destroy() 

    def align_label(self, sg, label):
        hb = gtk.HBox(False, 5)
        hb.show()

        l = gtk.Label(label)
        l.set_alignment(1, 0.5)
        sg.add_widget(l)
        hb.pack_start(l, False)
        l.show()

        return hb

    def widget_set(self, widget, item, value):
        if isinstance(widget, gtk.Scale):
            widget.set_value(value)
        elif isinstance(widget, gtk.Entry):
            widget.set_text(value)
        elif isinstance(widget, gtk.ComboBox):
            choices = item.get_choices()
            if value in choices:
                widget.set_active(choices.index(value))
        elif isinstance(widget, gtk.CheckButton):
            widget.set_active(value)
        else:
            logging.error('unknown widget type')

    def widget_get(self, widget, item):
        if isinstance(widget, gtk.Scale):
            return widget.get_value()
        elif isinstance(widget, gtk.Entry):
            return widget.get_text()
        elif isinstance(widget, gtk.ComboBox):
            return item.get_choices()[widget.get_active()]
        elif isinstance(widget, gtk.CheckButton):
            return widget.get_active()
        else:
            logging.error('unknown widget type')
            return None

    def get_settings(self, item):
        """Get the settings from a tree of items as a hash."""
        settings = {}
        settings[item.get_name()] = item.get_value()
        for child in item.get_children():
            settings.update(self.get_settings(child))
        return settings

    def set_settings(self, settings):
        """Apply a set of settings."""
        root_widget = self.config.get_root_widget()
        for name in settings:
            item = root_widget.get_child_by_name(name)
            # we can't set readonly items
            if not item.get_readonly():
                item.set_value(settings[name])
        try:
            self.config.set_config()
        except camera.Error as e:
            logging.error('unable to set settings, %s', repr(e))
        self.refresh()

    def refresh_item(self, item):
        name = item.get_name()
        # not all camera settings will have GUI widgets
        if name in self.widget_table:
            widget = self.widget_table[name]
            self.widget_set(widget, item, item.get_value())
            widget.set_sensitive(not item.get_readonly())
        for child in item.get_children():
            self.refresh_item(child)

    def refresh(self):
        """Update the GUI from the camera."""
        self.config.refresh() 
        self.refresh_item(self.config.get_root_widget()) 

    def refresh_cb(self, widget, data = None):
        self.refresh() 

    def refresh_queue_cb(self):
        self.refresh() 
        return False

    def refresh_queue(self):
        if self.refresh_timeout:
            glib.source_remove(self.refresh_timeout)
            self.refresh_timeout = 0
        self.refresh_timeout = glib.timeout_add(500, self.refresh_queue_cb)

    def preset_add(self, name, settings):
        """Record the current camera settings as a named preset."""
        self.preset_table[name] = settings
        if not name in self.preset_names:
            self.preset_names += [name]
            self.preset_picker.append_text(name)
        self.preset_picker.set_active(self.preset_names.index(name))

    def preset_remove(self, name):
        """Remove a named preset."""
        if name in self.preset_names:
            index = self.preset_names.index(name)
            del self.preset_names[index]
            del self.preset_table[name]
            self.preset_picker.remove_text(index)

    def presets_load(self, filename):
        """Load presets from the named file."""
        try:
            f = file(filename, 'r')
        except IOError:
            pass
        else:
            try:
                table, names, number = pickle.load(f)
            except ValueError as e:
                logging.debug('unpicking error %s', repr(e))
            else:
                self.preset_table = table
                self.preset_names = names
                self.preset_number = number
            finally:
                f.close()

    def presets_save(self, filename):
        """Save all presets to the named file."""
        try:
            f = file(filename, 'w')
        except IOError:
            pass
        else:
            obj = [self.preset_table, self.preset_names, self.preset_number]
            pickle.dump(obj, f)
            f.close()

    def preset_picker_cb(self, widget, data = None):
        current = self.preset_picker.get_active() 
        if current >= 0:
            preset_name = self.preset_names[current]
            settings = self.preset_table[preset_name]
            self.set_settings(settings)

    def add_cb(self, widget, data = None):
        name = 'preset-%d' % self.preset_number
        self.preset_number += 1
        settings = self.get_settings(self.config.get_root_widget()) 
        self.preset_add(name, settings)

    def remove_cb(self, widget, data = None):
        current = self.preset_picker.get_active() 
        if current >= 0:
            name = self.preset_names[current]
            self.preset_remove(name)

    def update_item_cb(self, widget, name):
        item = self.config.get_root_widget().get_child_by_name(name)
        new_value = self.widget_get(widget, item)
        old_value = item.get_value()
        logging.debug('update_item_cb: %s, new = %s, old = %s', 
                name, str(new_value), str(old_value))
        if new_value != old_value:
            item.set_value(new_value)
            try:
                self.config.set_config()
            except camera.Error as e:
                logging.debug('set error, restoring old value, %s', str(e))
                item.set_value(old_value)
                # we've restored the old value, so next time we update the
                # camera we don't need to resend this setting
                item.set_changed(False)
                # restore the old widget setting 
                # this will cause us to be triggered again, but the new!=old
                # test above will prevent looping
                self.widget_set(widget, item, old_value)
            else:
                # successful change ... changing one setting may change many
                # others, so we have to refresh the GUI from the camera
                self.refresh_queue()

                # we've changed a value, so we can no longer be showing one of
                # the presets
                self.preset_picker.set_active(-1)

    def build_page(self, section, vb): 
        sg = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        for item in section.get_children():
            wtype = item.get_wtype()
            name = item.get_name()
            label = item.get_label()
            value = item.get_value()

            if value == None:
                continue

            widget = None

            if wtype == camera.GP_WIDGET_TOGGLE:
                widget = gtk.CheckButton(label)
                self.widget_table[name] = widget
                widget.set_active(value)
                widget.connect('toggled', self.update_item_cb, name)

            if wtype == camera.GP_WIDGET_TEXT:
                widget = self.align_label(sg, label)
                b = gtk.Entry()
                self.widget_table[name] = b
                b.set_text(value)
                b.connect('activate', self.update_item_cb, name)
                widget.pack_start(b, True)
                b.show()

            if wtype in [camera.GP_WIDGET_MENU, camera.GP_WIDGET_RADIO]:
                choices = item.get_choices()
                widget = self.align_label(sg, label)
                b = gtk.combo_box_new_text()
                self.widget_table[name] = b
                for i in choices:
                    b.append_text(i)
                if value in choices:
                    b.set_active(choices.index(value))
                b.connect('changed', self.update_item_cb, name)
                widget.pack_start(b, True)
                b.show()

            if wtype == camera.GP_WIDGET_RANGE:
                wmin, wmax, winc = item.get_range()
                if wmin == wmax:
                    continue
                widget = self.align_label(sg, label)
                b = gtk.HScale()
                self.widget_table[name] = b
                b.set_value(value)
                b.set_range(wmin, wmax)
                b.set_increments(winc, 4 * winc)
                b.connect('value_changed', self.update_item_cb, name)
                widget.pack_start(b, True)
                b.show()

            if widget != None:
                widget.show()
                widget.set_sensitive(not item.get_readonly())
                vb.pack_start(widget, False);

    def __init__(self, options, cam):
        gtk.Window.__init__(self)
        self.connect('destroy', self.destroy_cb)

        self.options = options
        self.camera = cam
        self.config = camera.Config(self.camera)

        self.refresh_timeout = 0

        # a hash from item name to the widget that displays it
        self.widget_table = {}

        # a hash from preset name to a setting hash, plus a list of current
        # preset name in traverse order
        self.preset_table = {}
        self.preset_names = []

        # the next preset number we allocate
        self.preset_number = 1

        self.presets_load(os.path.join(self.options.tempdir, 'settings'))

        self.set_title(self.config.get_root_widget().get_label())

        self.set_default_size(-1, 300)

        vbox = gtk.VBox()
        vbox.show()
        self.add(vbox)

        book = gtk.Notebook()
        book.set_border_width(3)
        vbox.pack_start(book, True)
        book.show()

        for section in self.config.get_root_widget().get_children():
            page = gtk.ScrolledWindow()
            page.show()

            vb = gtk.VBox(False, 3)
            vb.set_border_width(3)
            page.add_with_viewport(vb)
            vb.show()

            self.build_page(section, vb)

            label = gtk.Label (section.get_label())
            label.show()

            book.append_page(page, label)

        toolbar = gtk.HBox(False, 5)
        toolbar.set_border_width(3)
        vbox.pack_start(toolbar, False)
        toolbar.show()

        button = gtk.Button()
        quit_image = gtk.image_new_from_stock(gtk.STOCK_QUIT, 
                        gtk.ICON_SIZE_SMALL_TOOLBAR)
        quit_image.show()
        button.connect('clicked', self.destroy_cb, None)
        button.add(quit_image)
        toolbar.pack_end(button, False, False)
        button.show()

        button = gtk.Button()
        refresh_image = gtk.image_new_from_stock(gtk.STOCK_REFRESH, 
                        gtk.ICON_SIZE_SMALL_TOOLBAR)
        refresh_image.show()
        button.connect('clicked', self.refresh_cb, None)
        button.add(refresh_image)
        toolbar.pack_start(button, False, False)
        button.show()

        self.preset_picker = gtk.combo_box_new_text()
        for name in self.preset_table:
            self.preset_picker.append_text(name)
        self.preset_picker.set_active(-1)
        self.preset_picker.connect('changed', self.preset_picker_cb, None)
        toolbar.pack_start(self.preset_picker, False, False)
        self.preset_picker.show()

        button = gtk.Button()
        add_image = gtk.image_new_from_stock(gtk.STOCK_ADD, 
                        gtk.ICON_SIZE_SMALL_TOOLBAR)
        add_image.show()
        button.connect('clicked', self.add_cb, None)
        button.add(add_image)
        toolbar.pack_start(button, False, False)
        button.show()

        button = gtk.Button()
        remove_image = gtk.image_new_from_stock(gtk.STOCK_REMOVE, 
                        gtk.ICON_SIZE_SMALL_TOOLBAR)
        remove_image.show()
        button.connect('clicked', self.remove_cb, None)
        button.add(remove_image)
        toolbar.pack_start(button, False, False)
        button.show()

        # make a preset for what we had at startup
        settings = self.get_settings(self.config.get_root_widget()) 
        self.preset_add('startup', settings)

