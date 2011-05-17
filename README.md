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


