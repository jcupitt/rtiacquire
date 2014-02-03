#!/usr/bin/python

"""Our main application window.

It is designed to capture sequences of images for RTI systems based on 
the design from the ECS dept. University of Southampton.

Author: J.Cupitt
Created as part of the AHRC RTI project in 2011
GNU LESSER GENERAL PUBLIC LICENSE
"""

import os
import logging
import time
import sys
import shutil

# we can't use argparse, we need to work on OS X which is still 
# stuck on python 2.5
import optparse

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import glib

import preview 
import camera 
import info 
import progress 
import ledmap 
import lights 
import config 

# get the directory this source is in
source_dir = os.path.dirname(__file__)

# how long to keep the play/pause button visible after a mouse event,
# in milliseconds
preview_timeout = 5000

# hop the lights after this many ms of no light actions -- prevents burnout
lights_timeout = 3500

# the width of the camera preview
# the Nikon has a 640 x 426 preview, I don't know what other cameras have,
# of whether libgphoto2 has an easy way to find this out
# hardwire this for now
preview_width = 640

def preview_filename():
    return os.path.join(options.tempdir, 'preview_test')

class MainWindow(gtk.Window):
    def destroy_cb(self, widget, data = None):
        if self.config_window:
            self.config_window.destroy()
            self.config_window = None

        self.camera.release()
        self.lights.release()

        gtk.main_quit()

    def preview_hide_cb(self):
        self.live_hide_timeout = 0
        self.live.hide()
        return False

    def preview_motion_cb(self, widget, event):
        self.live.show()
        if self.live_hide_timeout:
            glib.source_remove(self.live_hide_timeout)
            self.live_hide_timeout = 0
        self.live_hide_timeout = glib.timeout_add(preview_timeout, 
                        self.preview_hide_cb)
        return True

    def set_live(self, live):
        if live:
            self.live.set_image(self.pause_image)
        else:
            self.live.set_image(self.play_image)

        self.preview.set_live(live)

    def live_cb(self, widget, data = None):
        self.set_live(not self.preview.get_live())

    def config_destroy_cb(self, widget, data = None):
        self.config_window = None

    def config_cb(self, widget, data = None):
        if self.config_window:
            self.config_window.present()
        else:
            try:
                self.config_window = config.Config(options, self.camera)
            except camera.Error as e:
                self.info.err(e.message, e.detail)
            else:
                self.config_window.connect('destroy', self.config_destroy_cb)
                self.config_window.show()

    def focus_cb(self, widget, data = None):
        config = camera.Config(self.camera) 
        root = config.get_root_widget()
        focus = root.get_child_by_name('autofocusdrive')
        focus.set_value(1)
        config.set_config()

    def photo_cb(self, widget, data = None):
        live = self.preview.get_live()
        self.set_live(False)
        try:
            full_filename = self.camera.capture_to_file(preview_filename())
        except camera.Error as e:
            self.info.err(e.message, e.detail)
        else:
            if sys.platform == "darwin":
                os.system('open "%s"' % full_filename)
            else:
                os.system('xdg-open "%s"' % full_filename)
        self.set_live(live)

    def get_lights(self):
        index = self.dome_picker.get_active()
        name = self.leds.get_names()[index]

        return self.leds.get_bytes(name)

    def light_hop_cb(self):
        nlights = len(self.get_lights())
        self.set_lights((self.last_light + 1) % nlights)
        return False

    def set_lights(self, i):
        if self.light_hop_timeout:
            glib.source_remove(self.light_hop_timeout)
            self.light_hop_timeout = 0
        self.light_hop_timeout = glib.timeout_add(lights_timeout, 
            self.light_hop_cb)

        self.last_light = i
        self.lights.set_triple(self.get_lights()[i])

        light = self.light_picker.get_value_as_int() - 1
        if light != i:
            self.light_picker.set_value(i + 1)

    def lights_refresh(self):
        light = self.light_picker.get_value_as_int() - 1
        self.set_lights(light)

    def dome_picker_cb(self, widget, data = None):
        self.light_picker_refresh()

    def light_picker_refresh(self):
        self.light_picker.set_range(1, len(self.get_lights()))
        self.lights_refresh()

    def light_picker_cb(self, widget, data = None):
        self.lights_refresh()

    # start some kind of long action ... return True if we are good to go
    def action_start(self, message):
        if self.busy:
            return False
        self.busy = True
        self.old_live = self.preview.get_live()

        self.progress.start(message)
        self.toolbar.set_sensitive(False)
        self.live.set_sensitive(False)
        self.set_live(False)

        return True

    # restore state after a long action
    def action_stop(self):
        if not self.busy:
            return 
        self.busy = False

        self.progress.stop()
        self.toolbar.set_sensitive(True)
        self.live.set_sensitive(True)
        self.set_live(self.old_live)
        self.lights_refresh()

    # our general pattern for any long action
    # return True for success, False for error or cancel
    def action(self, message, action):
        result = False

        try:
            if self.action_start(message):
                result = action()
        except Exception as e:
            self.info.err(e.message, e.detail)
            result = False

        self.action_stop()

        return result

    def rti_preview(self):
        nlights = len(self.get_lights())
        for i in range(0, nlights):
            if self.progress.progress(i / float(nlights)):
                return False
            self.set_lights(i)

            # we need to wait to make sure we get a fresh preview frame
            time.sleep(0.1)

            self.camera.preview_to_file(os.path.join(options.tempdir, 
                'rti_preview_%d.jpg' % i))

        return True

    def rti_preview_ptm(self):
        self.progress.progress(0.2)
        shutil.copy(os.path.join(source_dir, "data", "preview.lp"),
                os.path.join(options.tempdir))
        self.progress.progress(0.5)
        retval = os.system('cd %s ; ptmfit -i preview.lp -o preview.ptm' %
                options.tempdir)
        if retval != 0:
                self.info.err('Unable to generate preview PTM', 
                    'failed to run ptmfit, is it installed?')
                return False

        return True

    def rti_preview_view(self):
        self.progress.progress(0.3)
        retval = os.system('PTMviewer %s &' % 
                os.path.join(options.tempdir, 'preview.ptm'))
        self.progress.progress(0.6)
        if retval != 0:
                self.info.err('Unable to launch PTM viewer', 
                    'failed to run PTMviewer, is it installed?')
                return False

        return True

    def rti_preview_cb(self, widget, data = None):
        if not self.action('Taking preview ...', self.rti_preview):
            return
        if not self.action('Generating PTM ...', self.rti_preview_ptm):
            return
        self.action('Starting viewer ...', self.rti_preview_view)

    def rti_capture(self):
        logging.debug('starting capture to %s', self.target)

        start = time.time()
        nlights = len(self.get_lights())

        for i in range(0, nlights):
            if self.progress.progress(i / float(nlights)):
                return False
            self.set_lights(i)

            self.camera.capture_to_file(os.path.join(self.target, '%d' % i))

            # stops the camera locking up
            time.sleep(0.1)

            # unless you preview between captures, the Nikon D3X will 
            # autofocus in AF-S mode
            self.camera.preview()

        logging.debug('capture done in %fs', time.time() - start)

        return False

    def rti_capture_cb(self, widget, data = None):
        chooser = gtk.FileChooserDialog('Select output folder', self, 
                gtk.FILE_CHOOSER_ACTION_CREATE_FOLDER, 
                (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT, 'Capture', 99))
        chooser.set_default_response(99)
        chooser.set_current_folder(self.outdir)
        response = chooser.run()
        filename = chooser.get_filename()
        chooser.hide()

        if response != 99:
            return

        if filename == None:
            self.info.err('Select a destination folder', '')
            return

        # filename is "base/project-name"
        # we remember the base for next time, we make the standard directory
        # structure below project-name
        self.outdir = os.path.dirname(filename)
        project = os.path.basename(filename)

        # remove a trailing '/', if any, it'll confuse os.path.dirname()
        if filename[-1] == '/':
            filename = filename[:-1]

        if os.access(filename, os.W_OK):
            self.info.err('Destination folder exists', 
                          'Pick another name or delete %s.' % filename)
            return

        for i in ['assembly-files', 'finished-files', 
                'original-captures', 'jpeg-exports']:
            target = os.path.join(filename, i)
            if not os.access(target, os.W_OK):
                try:
                    os.makedirs(target)
                except Exception as e:
                    self.info.err('Unable to create folder', 
                                    'Create %s failed with %s' % 
                                       (target, repr(e)))
                    return

        # record camera settings
        try:
            f = open(os.path.join(filename, 'camsettings.txt'), 'w')
            f.write('Original capture by RTI Acquire 1.0\n')
            f.write(time.ctime() + '\n')
            index = self.dome_picker.get_active()
            name = self.leds.get_names()[index]
            f.write('Lights "%s"\n' % name)
            config = camera.Config(self.camera) 
            config.prettyprint(f, config.get_root_widget())
            f.close()
        except Exception as e:
            self.info.err('Unable to create camsettings.txt', 
                            'Create %s failed with %s' % 
                           (target, repr(e)))
            return

        self.target = os.path.join(filename, 'original-captures')

        self.action('Full capture to %s ...' % self.target, 
                    self.rti_capture)

    def __init__(self):
        gtk.Window.__init__(self)
        self.connect('destroy', self.destroy_cb)

        self.config_window = None
        self.live_hide_timeout = 0
        self.light_hop_timeout = 0
        self.busy = False

        self.leds = ledmap.Ledmap(os.path.join(source_dir, 'data', 
                                               'led-maps.txt'))

        logging.debug('loaded %d maps', len(self.leds.get_names()))
        for name in self.leds.get_names():
            bytes = self.leds.get_bytes(name)
            logging.debug('%s: %d lights', name, len(bytes))

        # where project directories get written, see RTI cap above
        self.outdir = options.outdir

        self.lights = lights.Lights()

        # try to reset the lights ... if this fails, disable dome controls
        try:
            self.dome_controls = True
            name = self.leds.get_names()[0]
            self.lights.set_triple(self.leds.get_bytes(name)[0])
        except lights.Error as e:
            logging.debug('no lights found, disabling dome controls')
            self.dome_controls = False

        self.vbox = gtk.VBox(False, 0)
        self.add(self.vbox)
        self.vbox.show()

        fixed = gtk.Fixed()
        self.vbox.pack_start(fixed, False)
        fixed.show()

        eb = gtk.EventBox()
        eb.add_events(gtk.gdk.POINTER_MOTION_MASK)
        eb.connect('motion_notify_event', self.preview_motion_cb)
        fixed.put(eb, 0, 0)
        eb.show()

        self.camera = camera.Camera()
        self.preview = preview.Preview(self.camera)
        eb.add(self.preview)
        self.preview.show()

        if options.verbose:
            try:
                config = camera.Config(self.camera) 
                config.prettyprint(sys.stdout, config.get_root_widget())
            except:
                logging.debug("No Camera detected: unable to print config")
        eb = gtk.EventBox()
        fixed.put(eb, 0, 0)
        eb.show()

        self.progress = progress.Progress()
        self.progress.set_size_request(preview_width, -1)
        eb.add(self.progress)

        eb = gtk.EventBox()
        fixed.put(eb, 0, 0)
        eb.show()

        self.info = info.Info()
        self.info.set_size_request(preview_width, -1)
        eb.add(self.info)

        eb = gtk.EventBox()
        fixed.put(eb, 20, 380)
        eb.show()

        self.play_image = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PLAY, 
                        gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.pause_image = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PAUSE, 
                        gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.live = gtk.Button()
        self.live.set_image(self.play_image)
        self.live.set_tooltip_text("Start/stop live preview")
        self.live.connect('clicked', self.live_cb, None)
        eb.add(self.live)
        self.live.show()

        self.toolbar = gtk.HBox(False, 5)
        self.toolbar.set_border_width(3)
        self.vbox.pack_end(self.toolbar)
        self.toolbar.show()

        button = gtk.Button()
        quit_image = gtk.image_new_from_stock(gtk.STOCK_QUIT, 
                        gtk.ICON_SIZE_SMALL_TOOLBAR)
        quit_image.show()
        button.set_tooltip_text("Quit RTIAcquire")
        button.connect('clicked', self.destroy_cb, None)
        button.add(quit_image)
        self.toolbar.pack_end(button, False, False)
        button.show()

        if self.dome_controls:
            self.dome_picker = gtk.combo_box_new_text()
            for name in self.leds.get_names():
                self.dome_picker.append_text(name)
            self.dome_picker.set_active(0)
            self.dome_picker.set_tooltip_text("Select lighting system")
            self.dome_picker.connect('changed', self.dome_picker_cb, None)
            self.toolbar.pack_start(self.dome_picker, False, False)
            self.dome_picker.show()

            self.light_picker = gtk.SpinButton(climb_rate = 1)
            self.light_picker.set_numeric(True)
            self.light_picker.set_wrap(True)
            self.light_picker.set_increments(1, 1)
            self.light_picker.set_tooltip_text("Pick light")
            self.light_picker_refresh()
            self.light_picker.connect('value_changed', 
                    self.light_picker_cb, None)
            self.toolbar.pack_start(self.light_picker, False, False)
            self.light_picker.show()

        button = gtk.Button()
        menu_image = gtk.image_new_from_stock(gtk.STOCK_PREFERENCES, 
                        gtk.ICON_SIZE_SMALL_TOOLBAR)
        menu_image.show()
        button.set_tooltip_text("Camera settings")
        button.connect('clicked', self.config_cb, None)
        button.add(menu_image)
        self.toolbar.pack_start(button, False, False)
        button.show()

        button = gtk.Button('Focus')
        button.set_tooltip_text("Focus camera automatically")
        button.connect('clicked', self.focus_cb, None)
        self.toolbar.pack_start(button, False, False)
        button.show()

        photo_image = gtk.image_new_from_file(
                os.path.join(source_dir, 'data', 'camera_24.png'))
        photo = gtk.Button()
        photo.set_image(photo_image)
        photo.set_tooltip_text("Take single photo")
        photo.connect('clicked', self.photo_cb, None)
        self.toolbar.pack_start(photo, False, False)
        photo.show()

        if self.dome_controls:
            photo = gtk.Button('RTI Preview')
            photo.set_tooltip_text("Take preview RTI image")
            photo.connect('clicked', self.rti_preview_cb, None)
            self.toolbar.pack_start(photo, False, False)
            photo.show()

            photo = gtk.Button('RTI Capture ...')
            photo.set_tooltip_text("Start full RTI acquisition")
            photo.connect('clicked', self.rti_capture_cb, None)
            self.toolbar.pack_start(photo, False, False)
            photo.show()

        self.info.msg('Welcome to RTI Acquire', 'v1.2, November 2013')

        self.show()

    def main(self):
        gtk.main()

def main():
    global options

    # try to find a default value for our destination directory
    home = os.getenv('HOME')
    if home == None:
        home = '/tmp'

    parser = optparse.OptionParser()
    parser.add_option("-d", "--debug", 
                    action = "store_true", dest = "verbose", default = False, 
                    help = "print debug messages")
    parser.add_option("-t", "--tempdir", 
                    dest = "tempdir", default = "/tmp", metavar = "DIR",
                    help = "set directory for temporary files to DIR")
    parser.add_option("-o", "--outdir", 
                    dest = "outdir", default = home, metavar = "DIR",
                    help = "set output directory to DIR")
    options, args = parser.parse_args()

    if options.verbose:
        logging.basicConfig(level = logging.DEBUG)

    if not os.access(options.tempdir, os.W_OK):
        logging.error('tempdir %s not writeable, defaulting to /tmp',
                        options.tempdir)
        options.tempdir = '/tmp'

    if not os.access(options.outdir, os.W_OK):
        logging.error('outdir %s not writeable, defaulting to /tmp',
                        options.outdir)
        options.outdir = '/tmp'

    logging.debug('tempdir set to %s', options.tempdir)
    logging.debug('outdir set to %s', options.outdir)

    window = MainWindow()
    window.main()

# if we are run directly, show our window
if __name__ == '__main__':
    main()
