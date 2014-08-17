# Echo360 Tools

## Summary

The Python script `capture_device.py` is a wrapper that implements [Echo360 Capture Device API Version 3_0](http://confluence.echo360.com/display/54/Capture+Appliance+API).

It is useful as a support tool to control and monitor a capture device.

The classes `Echo360CaptureDevice` and `Echo360CaptureDeviceResponse` can be used to automate the operation of a capture device.

I am not associated in any way with [echo360.com](http://echo360.com).

## CLI Examples

Simple help is available using:
`python capture_device.py --help`

The following are examples of typical commands:
```
python capture_device.py -s https://10.10.10.10 -p "letmein" -c new-capture --profile "Standard Lecture"
python capture_device.py -s https://10.10.10.10 -p "letmein" -c confidence-monitor --profile "Standard Lecture"
python capture_device.py -s https://10.10.10.10 -p "letmein" -c status --count 4 --sleep 5
python capture_device.py -s https://10.10.10.10 -p "letmein" -c status --count 9999 --sleep 1
python capture_device.py -s https://10.10.10.10 -p "letmein" -c pause
python capture_device.py -s https://10.10.10.10 -p "letmein" -c resume
python capture_device.py -s https://10.10.10.10 -p "letmein" -c extend --duration 300
python capture_device.py -s https://10.10.10.10 -p "letmein" -c stop
python capture_device.py -s https://10.10.10.10 -p "letmein" -c ping --url www.google.com
python capture_device.py -s https://10.10.10.10 -p "letmein" -c traceroute --timeout 20 --url www.google.com
python capture_device.py -s https://10.10.10.10 -p "letmein" -c system-info --timeout 20
python capture_device.py -s https://10.10.10.10 -p "letmein" -c test-status
python capture_device.py -s https://10.10.10.10 -p "letmein" -c test-capture --sleep 15
python capture_device.py -s https://10.10.10.10 -p "letmein" -c test-confidence --sleep 15
```
The default username is `admin`. Note all lecture controllers are able to use secure HTTP (HTTPS). If that is the case, use `http` instead of `https`.

Replace the IP address (`10.10.10.10`) in the URL with the IP address of your Lecture Capture device.

## Typical Usage
Two command windows, one for monitoring:
```
python capture_device.py -s https://10.10.10.10 -p "letmein" -c status --count 9999 --sleep 1
```
And the other for the control commands:
```
python capture_device.py -s https://10.10.10.10 -p "letmein" -c new-capture --profile "Standard Lecture"
python capture_device.py -s https://10.10.10.10 -p "letmein" -c pause
python capture_device.py -s https://10.10.10.10 -p "letmein" -c resume
python capture_device.py -s https://10.10.10.10 -p "letmein" -c extend --duration 300
python capture_device.py -s https://10.10.10.10 -p "letmein" -c stop
```
The monitoring output while the commands above are executed will look something like:
```
...
State=inactive
State=waiting; duration=5400; start time (local)=2014-07-09T15:08:22
State=waiting; duration=5400; start time (local)=2014-07-09T15:08:22
State=waiting; duration=5400; start time (local)=2014-07-09T15:08:22
State=waiting; duration=5400; start time (local)=2014-07-09T15:08:22
State=active; duration=5400; start time (local)=2014-07-09T15:08:22
State=active; duration=5400; start time (local)=2014-07-09T15:08:22
...
State=active; duration=5400; start time (local)=2014-07-09T15:08:22
State=active; duration=5400; start time (local)=2014-07-09T15:08:22
State=paused; duration=5400; start time (local)=2014-07-09T15:08:22
State=paused; duration=5400; start time (local)=2014-07-09T15:08:22
...
State=paused; duration=5400; start time (local)=2014-07-09T15:08:22
State=paused; duration=5400; start time (local)=2014-07-09T15:08:22
State=active; duration=5400; start time (local)=2014-07-09T15:08:22
State=active; duration=5400; start time (local)=2014-07-09T15:08:22
...
State=active; duration=5700; start time (local)=2014-07-09T15:08:22
State=active; duration=5700; start time (local)=2014-07-09T15:08:22
State=complete; duration=5700; start time (local)=2014-07-09T15:08:22
State=complete; duration=5700; start time (local)=2014-07-09T15:08:22
State=complete; duration=5700; start time (local)=2014-07-09T15:08:22
State=complete; duration=5700; start time (local)=2014-07-09T15:08:22
State=complete; duration=5700; start time (local)=2014-07-09T15:08:22
State=complete; duration=5700; start time (local)=2014-07-09T15:08:22
State=complete; duration=5700; start time (local)=2014-07-09T15:08:22
State=complete; duration=5700; start time (local)=2014-07-09T15:08:22
State=complete; duration=5700; start time (local)=2014-07-09T15:08:22
State=complete; duration=5700; start time (local)=2014-07-09T15:08:22
State=complete; duration=5700; start time (local)=2014-07-09T15:08:22
State=complete; duration=5700; start time (local)=2014-07-09T15:08:22
State=complete; duration=5700; start time (local)=2014-07-09T15:08:22
State=complete; duration=5700; start time (local)=2014-07-09T15:08:22
State=complete; duration=5700; start time (local)=2014-07-09T15:08:22
State=complete; duration=5700; start time (local)=2014-07-09T15:08:22
State=inactive
State=inactive
...
```

## Python Classes

The script contains examples of how to use the classes `Echo360CaptureDevice` and `Echo360CaptureDeviceResponse`.

`sample-status.py` is an example using the `status/system` API:

```python
from capture_device import Echo360CaptureDevice
import sys

device = Echo360CaptureDevice('https://10.10.10.10', 'admin', 'letmein', timeout=5)

if device.connection_test.success():
    print(str(device.status_system()))
else:
    print('Unknown error ({0}): {1}'.format(device.connection_test._result_code, device.connection_test._result_message))
 ```

It returns:
```
status_system: success Ok
Data: content_state: idle
  last_sync: 2014-06-11T02:50:41.276Z
  last_sync_local: 2014-06-11T12:50:41
  serial_number: ff-ff-08-00-ff-ff
  system_version: 5.4.39512
  up_since: 2014-06-07T15:33:45.198Z
  up_since_local: 2014-06-08T01:33:45
  utc_offset: 600
  wall_clock_time: 2014-06-11T02:50:56.749Z
  wall_clock_time_local: 2014-06-11T12:50:56
```

## Sample device controller (Raspberry Pi)

This is a proof of concept for a Smart Capture HD Python controller. It works from a Linux, OS/X command line, or a Raspberry Pi.

Requires [diesel.io](http://diesel.io/).

If used on a [Raspberry Pi](http://www.raspberrypi.org/) Model B, an [LCD Display](http://www.adafruit.com/products/1109) (and its associated [software](https://learn.adafruit.com/adafruit-16x2-character-lcd-plus-keypad-for-raspberry-pi/usage)) is recommended.

The command `sudo python echo360/monitor.py room_name` or `sudo nohup python echo360/monitor.py room_name &` will start the controller. The script runs as `root` to access the LCD display.

### Usage

The Raspberry Pi button and CLI character mapping is as follows:

button | character | function
------ | --------- | --------
select | a | start
left | b | pause/resume
right | c | stop
up | t | button press test
down | s | display current status

The functions (characters: `a`, `b`, `c`, `t`, `s`) can also be used from the command line.

Typical log output (log timestamps are UTC):
```
[2014/07/21 00:56:46] {monitor} INFO:starting state change monitor for https://10.10.10.10 user admin
[2014/07/21 00:56:46] {monitor} INFO:Commands: a=start/extend; b=pause/resume; c=stop
[2014/07/21 00:56:46] {monitor} INFO:No command line input. Probably running as a daemon.
[2014/07/21 00:56:46] {monitor} INFO:Ready for LCD button
[2014/07/21 00:56:47] {monitor} INFO:Message: State: inactive
[2014/07/21 00:56:55] {monitor} INFO:Execute user command: a
[2014/07/21 00:56:55] {monitor} INFO:Change state to start
[2014/07/21 00:56:55] {monitor} INFO:Message: Command: start
[2014/07/21 00:56:55] {monitor} INFO:Device command: start
[2014/07/21 00:56:55] {monitor} INFO:Name=Lecture Capture 2014-07-21 10:56 room_name
[2014/07/21 00:56:56] {monitor} INFO:Message: State: waiting
[2014/07/21 00:57:05] {monitor} INFO:Message: State: active
[2014/07/21 00:57:17] {monitor} INFO:Execute user command: c
[2014/07/21 00:57:17] {monitor} INFO:Change state to stop
[2014/07/21 00:57:17] {monitor} INFO:Message: Command: stop
[2014/07/21 00:57:17] {monitor} INFO:Device command: stop
[2014/07/21 00:57:17] {monitor} INFO:Message: State: complete
[2014/07/21 00:57:36] {monitor} INFO:Message: State: inactive

```
