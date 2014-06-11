# Echo360 Tools

## Summary

The Python script `capture_device.py` can be used as a CLI tool that implements [Echo360 Capture Device API Version 3_0](http://confluence.echo360.com/display/54/Capture+Device+API).

It is useful as a support tool to control and monitor a capture device.

To implement more automation, see the section on Python Classes Below.

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

Replace the IP address 10.10.10.10 with the IP address of your LEcture Capture device.

## Python Classes

The script contains examples of how to use the classes `Echo360CaptureDevice` and `Echo360CaptureDeviceResponse`.

