#!/usr/bin/python

# A proof of concept script.
# Works from an OS/X terminal window or a Raspberry Pi (optionally with an Adafruit 2x16 LCD).
# Usage: sudo nohup python echo360/monitor.py room_name &

from capture_device import Echo360CaptureDevice
import ConfigParser
import datetime
import os
import socket
import sys
import thread
import time
import urlparse

class DieselCaptureDevice(Echo360CaptureDevice):
    # use the Diesel HTTP methods so we can run in a simple loop.
    def __init__(self, server, username, password, debuglevel=None, timeout=10):
        Echo360CaptureDevice.__init__(self, server, username, password, debuglevel, timeout)

    def request(self, method, path, headers=None, body=None, timeout=None):
        url = urlparse.urlparse(urlparse.urljoin(self.server, path))
        try:
            if url.scheme == 'https':
                client = diesel.protocols.http.HttpsClient(url.hostname, url.port or 443, timeout=timeout)
            elif url.scheme == 'http':
                client = diesel.protocols.http.HttpClient(url.hostname, url.port or 80, timeout=timeout)
            resp = client.request(method, url.path, headers, body, timeout)
        except Exception as e:
            # the following error popped up on a Sunday after the device was inactive for 3 days:
            # SysCallError: (-1, 'Unexpected EOF')
            return('unknown', 'Unknown error: {0}'.format(repr(e)), {}, None)
        (status, reason) = resp.status.split(' ', 1)
        return (int(status), reason, resp.headers, resp.response[0])

def local_time_now(format='%Y-%m-%d %H:%M'):
    # return the local time
    ts_struct_time = time.gmtime()
    ts_datetime = datetime.datetime.fromtimestamp(time.mktime(ts_struct_time)) + \
        datetime.timedelta(minutes = int(device.connection_test.utc_offset))
        #datetime.timedelta(minutes = 600)
    return ts_datetime.strftime(format)

def state_machine(current, char):
    # state transitions based on the current state and a command character
    # states: inactive, waiting, active, paused, complete
    # characters: a (start/extend), b (pause/resume), c (stop)
    states = { # current_state?command_char:next
        'inactive?a': 'start',  'inactive?b':  None,    'inactive?c':  None,
        'waiting?a':   None,    'waiting?b':   None,    'waiting?c':   None,
        'active?a':   'extend', 'active?b':   'pause',  'active?c':   'stop',
        'paused?a':   'extend', 'paused?b':   'resume', 'paused?c':   'stop',
        'complete?a': 'start',  'complete?b':  None,    'complete?c':  None,
        }
    if current in ['inactive', 'waiting', 'active', 'paused', 'complete']:
        return states[str(current) + '?' + char]
    else:
        return None

# Diesel loop - process command_queue
def device_command():
    global current_state
    while True:
        c = command_queue.get()
        if device is None:
            log.info('No Device for command: ' + c)
        else:
            log.info('Device command: ' + c)
            # No extend command?
            if c == 'start':
                #record for 90 minutes.
                name = 'Lecture Capture {0} {1}'.format(local_time_now(), capture_location)
                log.info('Name={0}'.format(name))
                # record for 90 minutes
                resp = device.capture_new_capture(60*90, capture_profile, name)
                #print str(resp)
            elif c == 'pause':
                resp = device.capture_pause()
            elif c == 'extend':
                # extend by 10 minutes
                resp = device.capture_extend(60*10)
                # extend doesn't change the state so we clear the current state to 
                # force it to be updated in the next status check
                current_state = 'Extended'
            elif c == 'resume':
                resp = device.capture_record()
            elif c == 'stop':
                resp = device.capture_stop()
            if not resp.success():
                log.warning(str(resp))

# Diesel loop - process output_queue
def text_output():
    while True:
        message = output_queue.get()
        log.info(message)
        if lcd is not None:
            lcd.clear()
            lcd.message('Echo360: {0}\n{1}'.format(capture_location, message))

# Diesel loop - process each command character
def execute_command():
    while True:
        char = command_char_queue.get()
        log.info('Execute user command: {0}'.format(char))
        if char == 't':
            output_queue.put('Test command')
        elif char == 's':
            output_queue.put('State: ' + current_state)
        else:
            next = state_machine(current_state, char)
            if next is None:
                log.info('State remains {0}'.format(current_state))
            else:
                log.info('Change state to {0}'.format(next))
                diesel.fork_from_thread(output_queue.put, 'Command: ' + next)
                diesel.fork_from_thread(command_queue.put, next)                

# Diesel thread - read characters from the command line
def read_line_thread():
    try:
        log.info('Commands: a=start/extend; b=pause/resume; c=stop')
        while True:
            char = raw_input()
            if char in ['a', 'b', 'c','t', 's']:
                diesel.fork_from_thread(command_char_queue.put, char) 
            else:
                log.info('Ignored invalid command.')
    except:
        log.info('No command line input. Probably running as a daemon.')

# Diesel loop - loops on LCD button pressed + 0.15 seconds
def read_button():
    if lcd is None:
        return
    log.info('Ready for LCD button')
    # Poll buttons and translate to a command
    btn = ((lcd.LEFT  , 'b'),
           (lcd.UP    , 't'),
           (lcd.DOWN  , 's'),
           (lcd.RIGHT , 'c'),
           (lcd.SELECT, 'a'))
    while True:
        prev = -1
        for b in btn:
            if lcd.buttonPressed(b[0]):
                if b is not prev:
                    diesel.fork_from_thread(command_char_queue.put, (b[1]))
                    prev = b
        diesel.sleep(0.15)

# Diesel loop - poll device status every 0.25 seconds (or 60 seconds after 10 errors)
# current_state is a bit of a hack. It can be a device state, Extended, Error,  No connection, Exception.
def state_change_monitor():
    global device
    global current_state
    log.info('starting state change monitor for {0} user {1}'.format(device_uri, device_username))
    # Try to recover from errors
    while True:
        try:
            device = DieselCaptureDevice(device_uri, device_username, device_password, timeout=timeout)
            if device.connection_test.success():
                # current_state = None
                error_count = 0
                while True:
                    mon = device.status_monitoring()
                    if mon.success():
                        state = mon.state
                        if state != current_state:
                            current_state = state
                            output_queue.put('State: ' + current_state)
                    else:
                        log.warning('Monitoring error: ' + str(mon))
                        current_state = 'Error'
                        error_count += 1
                        if error_count > 9:
                            log.warning('Too many errors. Retry in 60 seconds.')
                            break
                    diesel.sleep(0.25)
            else:
                log.warning('Connection not established: {0}. Retry in 60 seconds.'.format(str(device.connection_test._result_code)))
                current_state = 'No connection'
                diesel.fork_from_thread(output_queue.put, current_state)
        except socket.timeout as e:
            device = None
            log.info('network timeout connecting to {0} as {1}. Retry in 60 seconds.'.format(device_uri, device_username))
            current_state = 'Exception'
            diesel.fork_from_thread(output_queue.put, current_state)
        except:
            device = None
            log.info('Unknown error. Retry in 60 seconds.')
            current_state = 'Exception'
            diesel.fork_from_thread(output_queue.put, current_state)

        # only try to reconnect every minute
        diesel.sleep(60)

if __name__ == '__main__':
    # process configuration
    if len(sys.argv) == 2:
        capture_location = sys.argv[1]
    else:
        print('The room_name must be specified.')
        sys.exit(1)
    timeout = 5
    config_filename = 'echo360.config'

    config = ConfigParser.ConfigParser()
    config.readfp(open(config_filename))

    section = 'capture ' + capture_location
    device_uri      = config.get(section, 'uri')
    device_username = config.get(section, 'username')
    device_password = config.get(section, 'password')
    capture_profile = config.get(section, 'profile')

    # start LCD if present
    lcd_path = 'Adafruit-Raspberry-Pi-Python-Code/Adafruit_CharLCDPlate'
    sys.path.append(lcd_path)
    try:
        from Adafruit_CharLCDPlate import Adafruit_CharLCDPlate
        lcd = Adafruit_CharLCDPlate()
        lcd.begin(16, 2)
        lcd.message('Echo360\nMonitor starting')
    except:
        lcd = None

    # Diesel import takes a while on the Raspberry Pi (which is why it is after the first lcd message)
    import diesel
    from diesel.protocols.http import HttpClient, HttpsClient

    log = diesel.log.name('monitor')

    # create Diesel queues
    output_queue = diesel.util.queue.Queue()
    command_queue = diesel.util.queue.Queue()
    command_char_queue = diesel.util.queue.Queue()

    # Global written by state_change_monitor and read by 
    current_state = 'Unknown'

    # Start Diesel
    thread.start_new_thread(read_line_thread, ())
    diesel.quickstart(text_output, device_command, state_change_monitor, read_button, execute_command)
    if lcd is not None:
        lcd.clear()
        lcd.message('Echo360\nMonitor stopped')

