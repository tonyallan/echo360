#!/usr/bin/env python
#
# Example of the status command.

from capture_device import Echo360CaptureDevice
import sys

device = Echo360CaptureDevice('10.10.10.10', 'admin', 'letmein', timeout=5)

if device.connection_test.success():
    print(str(device.status_system()))
else:
    print('Unknown error ({0}): {1}'.format(device.connection_test._result_code, device.connection_test._result_message))
  