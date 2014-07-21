#!/usr/bin/python

# A proof of concept script.
# Works from an OS/X terminal window or a Raspberry Pi.
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
                client = diesel.protocols.http.HttpsClient(url.hostname, url.port or 443)
            elif url.scheme == 'http':
                client = diesel.protocols.http.HttpClient(url.hostname, url.port or 80)
            resp = client.request(method, url.path, headers, body, timeout)
        except SysCallError as e:
            # this error popped up on a Sunday after the device was inactive for 3 days.
            # SysCallError: (-1, 'Unexpected EOF')
            return('unknown', 'Error: {0}'.format(repr(e)), {}, None)
        except Exception as e:
            return('unknown', 'Unknown error: {0}'.format(repr(e)), {}, None)
        #resp.status = 200 OK 
        (status, reason) = resp.status.split(' ', 1)
        return (int(status), reason, resp.headers, resp.response[0])

# Diesel loop - waits on command_queue
def device_command():
    while True:
        c = command_queue.get()
        if device is None:
            log.info('No Device for command: ' + c)
        else:
            log.info('Device command: ' + c)
            # No extend command?
            if c == 'start':
                #record for 90 minutes.
                name = 'Lecture Capture {0} {1}'.format(time_now(), capture_location)
                log.info('Name={0}'.format(name))
                resp = device.capture_new_capture(60*90, capture_profile, name)
                #print str(resp)
            elif c == 'pause':
                resp = device.capture_pause()
            elif c == 'extend':
                # extend by 10 minutes
                resp = device.capture_extend(60*10)
            elif c == 'resume':
                resp = device.capture_record()
            elif c == 'stop':
                resp = device.capture_stop()
            if not resp.success():
                log.warning(str(resp))

def time_now(format='%Y-%m-%d %H:%M'):
    ts_struct_time = time.gmtime()
    ts_datetime = datetime.datetime.fromtimestamp(time.mktime(ts_struct_time)) + \
        datetime.timedelta(minutes = 600)
    ##############################datetime.timedelta(minutes = int(device.connection_test.utc_offset))
    # '%Y-%m-%d\n%H:%M:%S'
    return ts_datetime.strftime(format)

def lcd_message(message):
    if lcd is not None:
        lcd.clear()
        lcd.message('Echo360: {0}\n{1}'.format(capture_location, message))

# Diesel loop - waits on output_queue
def text_output():
    while True:
        v = output_queue.get()
        log.info('Message: ' + v)
        lcd_message(v)
        diesel.sleep(0.1)

def change_state(current, char):
    # state transitions for a three button input
    # inactive, waiting, active, paused, complete
    states = { # current_state?command_char:next
        #'None?a':    'start',  'None?b':      None,    'None?c':      None,
        'inactive?a': 'start',  'inactive?b':  None,    'inactive?c':  None,
        'waiting?a':   None,    'waiting?b':   None,    'waiting?c':   None,
        'active?a':   'extend', 'active?b':   'pause',  'active?c':   'stop',
        'paused?a':   'extend', 'paused?b':   'resume', 'paused?c':   'stop',
        'complete?a': 'start',  'complete?b':  None,    'complete?c':  None,
        }
    return states[str(current) + '?' + char]

def execute_command(char):
    log.info('Execute user command: {0}'.format(char))
    if char == 't':
        output_queue.put('Test command')
    elif char == 's':
        output_queue.put('State: ' + current_state)
    else:
        #try:
            next = change_state(current_state, char)
            if next is None:
                log.info('State remains {0}'.format(current_state))
            else:
                log.info('Change state to {0}'.format(next))
                diesel.fork_from_thread(output_queue.put, 'Command: ' + next)
                diesel.fork_from_thread(command_queue.put, next)                
        #except:
        #    pass

# Diesel thread
def read_line_thread():
    try:
        log.info('Commands: a=start/extend; b=pause/resume; c=stop')
        while True:
            char = raw_input()
            if char in ['a', 'b', 'c','t', 's']:
                execute_command(char)
            else:
                log.info('Ignored invalid command.')
    except:
        log.info('No command line input. Probably running as a daemon.')

# Diesel loop - loops on LCD button pressed + 0.25 seconds
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
                    execute_command(b[1])
                    prev = b
        diesel.sleep(0.15)

    while True:
        #log.info('Commands: a=start/extend; b=pause/resume; c=stop')
        char = raw_input()
        if char == 't':
            log.info('Command test.')
        elif char == 's':
            state = device.status_monitoring().state
            output_queue.put(state)
        else:
            try:
                next = change_state(current, char)
                if next is not None:
                    current = next
                    diesel.fork_from_thread(output_queue.put, next)
                    diesel.fork_from_thread(command_queue.put, next)
            except:
                pass

#def status_thread():
#    #current_state = None
#    while True:
#        try:
#            state = device.status_monitoring().state
#        except socket.timeout:
#            state = 'timeout'
#        if state != current_state:
#            output_queue.put(state)
#            current_state = state
#        time.sleep(1.0)

def say_hi_forever():
    while True:
        output_queue.put('hi')
        diesel.sleep(1.0)

# Diesel loop - loops on device statis + 0.25 seconds
def state_change_monitor():
    global device
    global current_state
    log.info('starting state change monitor for {0} user {1}'.format(device_uri, device_username))
    try:
        device = DieselCaptureDevice(device_uri, device_username, device_password, timeout=timeout)
        if not device.connection_test.success():
            log.warning('Connection not established: ' + str(device.connection_test._result_code))
    except socket.timeout as e:
        device = None
        log.info('network timeout connecting to {0} as {1}'.format(device_uri, device_username))

    # current_state = None
    while True:
        mon = device.status_monitoring()
        if mon.success():
            state = mon.state
            if state != current_state:
                current_state = state
                output_queue.put('State: ' + state)
        else:
            log.warning('Monitoring error: ' + str(mon))
        diesel.sleep(0.25)

if __name__ == '__main__':
    # future cli options
    capture_location = sys.argv[1]
    timeout = 5
    config_filename = 'echo360.config'

    config = ConfigParser.ConfigParser()
    config.readfp(open(config_filename))

    device_uri = config.get('capture ' + capture_location, 'uri')
    device_username = config.get('capture ' + capture_location, 'username')
    device_password = config.get('capture ' + capture_location, 'password')
    capture_profile = config.get('capture ' + capture_location, 'profile')

    lcd_path = 'Adafruit-Raspberry-Pi-Python-Code/Adafruit_CharLCDPlate'
    sys.path.append(lcd_path)
    try:
        from Adafruit_CharLCDPlate import Adafruit_CharLCDPlate
        lcd = Adafruit_CharLCDPlate()
        lcd_start_message = None
        lcd.begin(16, 2)
        lcd_message('Monitor starting')
        lcd_start_message = 'LCD active.'
    except ImportError:
        lcd = None
        lcd_start_message = 'Adafruit module not found. Cannot use LCD.'
    except IOError as e:
        lcd = None
        lcd_start_message = 'Must run as root to use the LCD.'

    import diesel
    from diesel.protocols.http import HttpClient, HttpsClient

    log = diesel.log.name('monitor')
    if lcd_start_message is not None:
        log.info(lcd_start_message)

    output_queue = diesel.util.queue.Queue()
    command_queue = diesel.util.queue.Queue()

    # Global written by state_change_monitor and read by 
    current_state = None

    thread.start_new_thread(read_line_thread, ())
    diesel.quickstart(text_output, device_command, state_change_monitor, read_button)
    if lcd is not None:
        lcd_message('Monitor stopped')
        time.sleep(1)
