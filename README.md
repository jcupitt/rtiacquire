===========
RTI Acquire
===========

This program lets you use a digital camera from your computer. It has a
live preview window and a full set of manual controls. 

RTIAcquire uses the libgphoto2 library to control the camera, so you must
have this library on your system and your camera must be supported by
libgphoto2. They have a list of supported models here:

http://www.gphoto.org/proj/libgphoto2/support.php

libgphoto2 does not currently work on Windows.

RTIAcquire uses IJG libjpeg to decompress preview frames. You must have
the headers for this library available: jpeglib.h and jerror.h.

It can also control a lighting system for doing Reflectance Transform Imaging,
though you'll need to customise it for your exact dome and lighting hardware.
If you don't have a dome and lighting system, you can just use the program to
take pictures.

The whole thing is in Python so it should be very easy to customise.

Screenshots
===========

http://www.vips.ecs.soton.ac.uk/development/rti/snapshot11.jpg

The program as it starts up. The main area is a live preview running at
about 20 fps. My laptop will go up to about 50 fps, but most cameras can't
supply frames that quickly and anyway we don't want to flood the poor computer,
so the frame rate is throttled. 20 fps seems fine for manual focussing.

If you mouse over the live preview, a 'pause' button appears allowing you
to stop frame grabbing.

The camera is autodetected on startup. 

The buttons along the bottom of the window let you control the dome and
lighting system (if no dome is found, these do nothing), set camera controls,
take a single photo, take an RTI preview, and do a full RTI capture.

http://www.vips.ecs.soton.ac.uk/development/rti/snapshot13.jpg

The window you get if you click the camera control button. This is generated
by interrogating the camera for the controls it supports. The screenshot is
for a Nikon D3X.

The controls along the bottom let you refresh the GUI from the camera (if you
change one of the camera controls yourself), switch between presets, add a
preset, and remove a preset. Presets are remembered between sessions. A
special preset called 'startup' records the state of the camera when the
program was started.

http://www.vips.ecs.soton.ac.uk/development/rti/snapshot8.jpg

During RTI capture. 

Use Notes
=========

* When you plug the camera in you may get a desktop camera icon --
  right-click and select "unmount" so this program can open it.

* Interrupting the program or unplugging the camera during an operation, 
  for example, while the view preview is showing, may leave the camera in a
  strange state and make it unresponsive. Unplug, turn the camera off and on
  again, and reconnect. Sometimes even that doesn't work, argh. Try pulling out
  the camera power cord if desperate.

* Holding down the two green dot buttons on the lower back of the camera for 
  two seconds resets the camera to a sane state.

* With the Nikon, put the lens into AF-S mode (the control on the front of the
  camera body, to the right of the lens as you face it). This will let you
  autofocus using the program controls, but not refocus before each shot.

* In image preview, click Edit / Preferences and turn off image smoothing
  (smoothing makes checking focus difficult).

Credits
=======

This software was funded by the UK Arts and Humanities Research Council
"Reflectance Transformation Imaging System for Ancient Document Artefacts
Projects" under the Digital Equipment and Database Enhancement for Impact
Scheme. Details are available at:

http://www.southampton.ac.uk/archaeology/acrg/AHRC_RTI.html

Todo
====

* in camera.py, try ignoring the return value from gp.gp_camera_capture(), do
  we still get a sensible value for cam_path? perhaps only fail if cam_path is
  useless

  if this works, we might be able to get rid of the preview() at the beginning 
  of capture_to_file()




* how do we do light calibration? a separate program?

* can we get the preview to reflect actual exposure? it seems to always do
  auto-expose

    nope, doesn't seem to be possible

* build and bundle the ptm fitter and viewer

* see the OS X bundler, investigate prebuilt pygtk on OS X packages

* break main out into a separate program

* name private members with a leading _?


