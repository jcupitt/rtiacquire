===========
RTI Acquire
===========

This program lets you use a digital camera from your computer. It has a
live preview window and a full set of manual controls. 

RTIAcquire uses the libgphoto2 library to control the camera, so you must
have this library on your system and your camera must be supported by
libgphoto2. They have a list of [supported models](http://www.gphoto.org/proj/libgphoto2/support.php).

libgphoto2 does not currently work on Windows without some tinkering. 

It can also control a lighting system for doing Reflectance Transform Imaging,
though you'll need to customise it for your exact dome and lighting hardware.
If you don't have a dome and lighting system, you can just use the program to
take pictures.

The whole thing is in Python so it should be very easy to customise. There are
about 600 lines of C for the live preview. 

Prerequistites
==============

libgphoto2 does not work on Windows, so you need a unix-like system of some
sort. We've used several Linuxes but OS X should work too. On Debian-family
systems this package is called libgphoto2-2.

RTIAcquire uses IJG libjpeg to decompress preview frames. You must have
the headers for this library available: jpeglib.h and jerror.h. On
Debian-family systems this package is called libjpeg-dev. 

The GUI is done in gtk2, so you need the python-gtk2 package. 

RTIAcquire communicates with the lighting system over USB using python-serial.
You need to have this package installed too. 

Screenshots
===========

![screenshot](http://www.vips.ecs.soton.ac.uk/development/rti/snapshot11.jpg)

The program as it starts up. The main area is a live preview running at
about 20 fps. My laptop will go up to about 50 fps, but most cameras can't
supply frames that quickly and anyway we don't want to flood the poor computer,
so the frame rate is throttled. 20 fps seems fine for manual focussing.

If you mouse over the live preview, a 'pause' button appears allowing you
to stop frame grabbing.

The camera is autodetected on startup. 

The buttons along the bottom of the window let you control the dome and
lighting system, set camera controls, take a single photo, take an RTI 
preview, and do a full RTI capture. If no dome is found on startup, the 
lighting controls and the RTI controls do not appear. 

![screenshot](http://www.vips.ecs.soton.ac.uk/development/rti/snapshot13.jpg)

The window you get if you click the camera control button. This is generated
by interrogating the camera for the controls it supports. The screenshot is
for a Nikon D3X.

The controls along the bottom let you refresh the GUI from the camera (in case 
you change one of the camera controls on the camera body), switch between 
presets, add a preset, and remove a preset. Presets are remembered between 
sessions. A special preset called 'startup' records the state of the camera 
when the program was started.

![screenshot](http://www.vips.ecs.soton.ac.uk/development/rti/snapshot8.jpg)

During RTI capture. 

Use Notes
=========

* Install with something like:

```bash
$ python setup.py install --prefix=/my/install/prefix
```

  And run with

```bash
$ RTIAcquire
```

  Make quicklaunch links in the usual way for convenience etc.

* Run with

```bash
$ RTIAcquire --debug &> log
```

  to produce a lot of debugging output in the file "log", handy for testing.

* When you plug the camera in you may get a desktop camera icon --
  right-click and select "unmount" so this program can open it.

* Interrupting the program or unplugging the camera during an operation
  while the view preview is showing may leave the camera in a
  strange state and make it unresponsive. Unplug, turn the camera off and on
  again, and reconnect. Sometimes even that doesn't work, argh. Try pulling out
  the camera power cord if desperate.

* Holding down the two green dot buttons on the lower back of the camera for 
  two seconds resets the camera to a sane state.

* With the Nikon D3X, put the lens into AF-S mode (the control on the front of 
  the camera body, to the right of the lens as you face it). This will let
  you autofocus using the program controls, but not refocus before each shot.

* In image preview, click Edit / Preferences and turn off image smoothing
  (smoothing makes checking focus difficult).

Credits
=======

This software was funded by the UK Arts and Humanities Research Council
"Reflectance Transformation Imaging System for Ancient Document Artefacts
Projects" under the Digital Equipment and Database Enhancement for Impact
Scheme. [Details are available.](http://www.southampton.ac.uk/archaeology/acrg/AHRC_RTI.html)


Current hacking
===============

* move select code to preview

* what's the best way to hook into Preview expose



Todo
====

* in camera.py, try ignoring the return value from `gp.gp_camera_capture()`, do
  we still get a sensible value for `cam_path`? perhaps only fail if 
  `cam_path` is useless

  if this works, we might be able to get rid of the preview() at the beginning 
  of `capture_to_file()`

* break main out into a separate program

* name private members with a leading `_`?

Major new features
==================

* how do we do light calibration? a separate program?

* build and bundle the ptm fitter and viewer

* see the OS X bundler, investigate prebuilt pygtk on OS X packages

* Phil wrote a tiny gui wrapper for doing the fitting - so an extra Build 
  button could be added to yours which runs his script (as the path is needed)

	fitter notes here

	http://rti.ecs.soton.ac.uk/wiki/Oxford:Setup#Fitter

	they need to be able to batch fit

	also, crop before fit to speed the process up

wontfix
=======

* stop mousewheel changing combo boxes

	not possible to fix, sadly

* can we get the preview to reflect actual exposure? it seems to always do
  auto-expose

	nope, doesn't seem to be possible

* can we drive the camera focus ourselves

	nope, doesn't seem to be possible, see:

	http://sourceforge.net/mailarchive/forum.php?thread_name=CAGNS0RsnFcCOBhYtfRwcnb5Av5Y%2BkkQAjTN%3DgKvp2HWhkpSdLw%40mail.gmail.com&forum_name=gphoto-user

	but I'll watch for replies just in case

