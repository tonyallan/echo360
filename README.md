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
python capture_device.py -s 10.10.10.10 -p "letmein" -c new-capture --profile "Standard Lecture"
python capture_device.py -s 10.10.10.10 -p "letmein" -c confidence-monitor --profile "Standard Lecture"
python capture_device.py -s 10.10.10.10 -p "letmein" -c status --count 4 --sleep 5
python capture_device.py -s 10.10.10.10 -p "letmein" -c status --count 9999 --sleep 1
python capture_device.py -s 10.10.10.10 -p "letmein" -c pause
python capture_device.py -s 10.10.10.10 -p "letmein" -c resume
python capture_device.py -s 10.10.10.10 -p "letmein" -c extend --duration 300
python capture_device.py -s 10.10.10.10 -p "letmein" -c stop
python capture_device.py -s 10.10.10.10 -p "letmein" -c ping --url www.google.com
python capture_device.py -s 10.10.10.10 -p "letmein" -c traceroute --timeout 20 --url www.google.com
python capture_device.py -s 10.10.10.10 -p "letmein" -c system-info --timeout 20
python capture_device.py -s 10.10.10.10 -p "letmein" -c test-status
python capture_device.py -s 10.10.10.10 -p "letmein" -c test-capture --sleep 15
python capture_device.py -s 10.10.10.10 -p "letmein" -c test-confidence --sleep 15
```

Replace the IP address 10.10.10.10 with the IP address of your Lecture Capture device.

## Python Classes

The script contains examples of how to use the classes `Echo360CaptureDevice` and `Echo360CaptureDeviceResponse`.

`sample-status.py` is an example using the `status/system` API:

```
from capture_device import Echo360CaptureDevice
import sys

device = Echo360CaptureDevice('10.10.10.10', 'admin', 'letmein', timeout=5)

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
