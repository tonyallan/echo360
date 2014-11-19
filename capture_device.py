#!/usr/bin/env python
#
# Python wrapper for Echo360 Capture Device API Version 3_0
# http://confluence.echo360.com/display/54/Capture+Appliance+API
#
# These tools are not associated with echo360.com This is an independant effort
# to implement a python wrapper for their API.
#
# ----------------------------------------------------------------------------
# This file is part of Echo360 Tools.  The tools are free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright 2014 Tony Allan <tony@apms.com.au>
# ----------------------------------------------------------------------------
# 
# Can be used as a CLI tool (use --help) or as classes Echo360CaptureDevice(), Echo360CaptureDeviceResponse()
# the CLI code below shows class usage examples. 

import argparse
import base64
import datetime
import httplib
import json
import socket
import sys
import time
import urllib2
import urlparse
import xml.etree.ElementTree as ET

class Echo360CaptureDevice(object):
    # This class is a wrapper for the Echo360 Capture device API.
    def __init__(self, server, username, password, debuglevel=None, timeout=10):
        self.server = server
        self.username = username
        self.password = password
        self.debug = debuglevel
        self.timeout = int(timeout)
        self.utc_offset = None
        self.connection_test = self.status_system()
        if self.connection_test.success():
            self.utc_offset = self.connection_test.utc_offset

    def request(self, method, path, headers=None, body=None, timeout=None):
        # Perform the request and all exception handling.
        # Returns:
        #     status   - HTTP status or an exception code
        #     reason   - A human readable error message, HTTP reason or exception related message
        #     headers  - A dict that may contain HTTP response headers
        #     data     - None or response data.
        # allow override in a subclass to support other http libraries (such as Diesel.io)
        url = urlparse.urlparse(urlparse.urljoin(self.server, path))
        if len(url.netloc) == 0:
            return('Invalid URL', 'Missing IP address or domain name.', {}, None)
        try:
            if url.scheme == 'https':
                conn = httplib.HTTPSConnection(url.hostname, url.port, timeout=self.timeout)
            elif url.scheme == 'http':
                conn = httplib.HTTPConnection(url.hostname, url.port, timeout=self.timeout)
            else:
                return('Invalid URL', 'The URL scheme must be http or https.', {}, None)
        except Exception as e:
            return('unknown', 'Unknown error: {0}'.format(repr(e)), {}, None)
        if self.debug is not None:
            conn.set_debuglevel(self.debug)
        try:
            conn.request(method, url.path, body, headers)
            resp = conn.getresponse()
            return (resp.status, resp.reason, dict(resp.getheaders()), resp.read())
        except socket.timeout as e:
        # This exception is raised when a timeout occurs on a socket which has had
        # timeouts enabled via a prior call to settimeout().
            if timeout is None:
                return('timeout', 'Network connection timed out.', {}, None)
            else:
                return('timeout', 'Network connection timed out (after {0} seconds).'.format(timeout), {}, None)
        except socket.error as e:
            # This exception is raised for socket-related errors.
            if e.errno == 8:
                # socket.gaierror: [Errno 8] nodename nor servname provided, or not known
                return('socket-8', 'Unknown host: {0}'.format(args.server), {}, None)
            elif e.errno == 61:
                # socket.error: [Errno 61] Connection refused
                return('socket-61', 'Server connection refused: {0}'.format(args.server), {}, None)
            elif e.errno is not None:
                return('socket', 'Network error ({0}): {1}'.format(e.errno, e.strerror), {}, None)
            else:
                return('unknown', 'Network error: {0}'.format(repr(e)), {}, None)

    def call_api(self, command, method=None, post_data=None, title=None, dump_xml=None):
        if method is None:
            if post_data is None:
                method = 'GET'
            else:
                method = 'POST'
        if self.username is not None and self.password is not None: 
            req_headers = { 'Authorization' : 'Basic ' + base64.b64encode(self.username + ':' + self.password) }
        else:
            req_headers = {}
        (status, reason, headers, data) = self.request(method, command, req_headers, post_data, self.timeout)
        if 'Content-Type' in headers and headers['Content-Type'] == 'text/xml':
            xml_data = ET.fromstring(data)
        # some libraries convert to lower-case
        elif 'content-type' in headers and headers['content-type'] == 'text/xml':
            xml_data = ET.fromstring(data)
        else:
            xml_data = None
        if status == 200:
            return Echo360CaptureDeviceResponse(command, 'success', 'Ok', data=data, xml_data=xml_data, 
                device=self, utc_offset=self.utc_offset, title=title, dump_xml=dump_xml)
        else:
            # 409 Conflict is used as an error response for capture/stop, capture/confidence_monitor and possibly others
            # 501 Is used as an error for capture/new-capture
            if self.debug > 0:
                print('Debug command {0}\nStatus: {1} reason:{2}'.format(command, status, reason))
            if self.debug > 4:
                print('Response data:\n{0}'.format(data))
            return Echo360CaptureDeviceResponse(command, status, reason, data=data, xml_data=xml_data,
                device=self, utc_offset=self.utc_offset, title=title, dump_xml=dump_xml)

    def fetch_file(self, command):
        pass

    def capture_status_str(self, sleep=None):
        # Fetch the capture status
        if sleep is not None:
            time.sleep(sleep)
        response = self.status_monitoring()
        if response.success():
            text = 'State={0}'.format(response.state)
            if response.check_attribute('duration'):
                text += '; duration={0}'.format(response.duration)
            if response.check_attribute('start_time_local'):
                text += '; start time (local)={0}'.format(response.start_time_local)
            if response.check_attribute('confidence_monitoring'):
                if response.confidence_monitoring != 'false':
                    text += '; confidence monitoring={0}'.format(response.confidence_monitoring)
            return text
        else:
            if response._result_code == 401:
                return 'User {0} is not authorised to perform status/monitoring, '.format(self.username) + \
                    'or username or password are not correct.'
            return 'Unknown device error ({0}): {1}'.format(
                response._result_code, response._result_message)

    # (3) Device API Calls
    # The method names match the API names.

    # (3.1) Device and Capture Status API Calls
    # The Status API calls are used to return status and capture information for the device. The Status calls 
    # in this section are GET only, and are used specifically to retrieve information.

    def status_system(self, dump_xml=None):
        """
        (3.1.1) Get System Status returns the current status of the device.

        curl --silent --user $adminlogincreds --insecure --url $apiurl"/status/system"
        """
        response = self.call_api('status/system', title='Get System Status', dump_xml=dump_xml)
        if response.success():
            response.add_timestamp('wall-clock-time')
            response.add_value('content/state')
            response.add_value('utc-offset')
            response.add_value('serial-number')
            response.add_value('system-version')
            response.add_timestamp('up-since')
            response.add_timestamp('last-sync')
        return response

    def status_captures(self, dump_xml=None):
        """
        (3.1.2) Get Capture Status returns information on the status of both the next and the current capture.

        curl --silent --user $adminlogincreds --insecure --url $apiurl"/status/captures"
        """
        response = self.call_api('status/captures', title='Get Capture Status', dump_xml=dump_xml)
        if response.success():
            response.add_timestamp('wall-clock-time')
            self._current_capture(response)
            response.state = response.current_state
            self._next_capture(response)
        return response

    def _next_capture(self, response):
        response.add_value('next/schedule/type')
        response.add_timestamp('next/schedule/start-time')
        response.add_value('next/schedule/duration')
        response.add_value('next/schedule/parameters/title')
        response.add_value('next/schedule/parameters/section')
        response.add_value('next/schedule/parameters/capture-profile/name')
        response.add_value('next/state')
        response.add_timestamp('next/start-time')
        response.add_value('next/duration')

    def status_next_capture(self, dump_xml=None):
        """
        (3.1.3) Get Next Capture Status returns information on the status of only the next capture.

        curl --silent --user $adminlogincreds --insecure --url $apiurl"/status/next_capture"
        """
        response = self.call_api('status/next_capture', title='Get Next Capture Status', dump_xml=dump_xml)
        if response.success(): 
            response.add_timestamp('wall-clock-time')
            self._next_capture(response)
        return response

    def _current_capture(self, response):
        response.add_value('current/schedule/type')
        response.add_timestamp('current/schedule/start-time')
        response.add_value('current/schedule/duration')
        response.add_value('current/schedule/parameters/title')
        response.add_value('current/schedule/parameters/section')
        response.add_value('current/schedule/parameters/capture-profile/name')
        response.add_value('current/state')
        response.add_timestamp('current/start-time')
        response.add_value('current/duration')

    def status_current_capture(self, dump_xml=None):
        """
        (3.1.4) Get Current Capture Status returns information on the status of only the current capture.

        curl --silent --user $adminlogincreds --insecure --url $apiurl"/status/current_capture"
        """
        response = self.call_api('status/current_capture', title='Get Current Capture Status', dump_xml=dump_xml)
        if response.success(): 
            response.add_timestamp('wall-clock-time')
            self._current_capture(response)
            response.state = response.current_state
        return response

    def status_monitoring(self, dump_xml=None):
        """
        (3.1.5) Get Capture Status with Monitoring Information returns real-time monitoring information on the 
        current capture. This call is useful for returning the filename for a thumbnail (display or 
        video) to use in the Show Current Video or Display View API call described in 
        'monitoring_snapshot()' below.

        curl --silent --user $adminlogincreds --insecure --url $apiurl"/status/monitoring"
        """
        response = self.call_api('status/monitoring', title='Get Capture Status with Monitoring Information', dump_xml=dump_xml)
        if response.success(): 
            response.add_value('state')
            response.add_timestamp('start-time')
            response.add_value('duration')
            response.add_value('confidence-monitoring')
        return response

    def monitoring_snapshot(self, url, dump_xml=None):
        """
        (3.1.6) Show Current Video or Display View returns a snapshot image of the video or display input  
        for the current capture. This is an image of what the Video input or Display input for the current 
        capture is at the moment the call is made.
        Use the filename information returned from the Get Capture Status call described in 
        status_monitoring() above.

        Video: curl --user admin:password --insecure --data 'duration=900&capture_profile_name=
            Display/Video (Podcast/Vodcast/EchoPlayer). Optimized for quality/full motion video&
            description=test-description' 
            --url https://192.168.61.10:8443/monitoring/video_ntsc_graphics-channel2-stream0.jpg

        Display: curl --user admin:password --insecure --data 'duration=900&capture_profile_name=
            Display/Video (Podcast/Vodcast/EchoPlayer). Optimized for quality/full motion video&
            description=test-description' 
            --url https://192.168.61.10:8443/monitoring/vga_display_graphics-channel1-stream0.jpg
        """
        raise "unimplemented"

    def status_get_user_sections(self, dump_xml=None):
        """
        (3.1.7) Get User Sections returns a list of the sections assigned to the user whose credentials 
        (username and password) are sent with the API call. Response includes both Section Name and 
        GUID along with the capture profile configured for each section.

        curl --silent --user $adminlogincreds --insecure --url $apiurl"/status/get_user_sections"
        """
        return self.call_api('status/get_user_sections', title='Get User Sections', dump_xml=dump_xml)

    def status_get_user_ref(self, dump_xml=None):
        """
        (3.1.8) Get Authenticated User Reference ID returns the user reference ID (GUID) of the user whose 
        credentials (username and password) are sent with the API call.

        curl --user admin:password --insecure --url https://192.168.61.10:8443/status/get_user_ref
        """
        response = self.call_api('status/get_user_ref', title='Get Authenticated User Reference ID', dump_xml=dump_xml)
        if response.success():
            response.add_value('', name='authenticated-user-ref')
        return response        

    # (3.2) Diagnostics API Calls
    # The API calls identified below retrieve and perform diagnostic and maintenance duties for the capture 
    # device identified in the call. This section includes log retrieval calls.
    # The API calls in this section can only be performed by an Administrator.

    def diagnostics_clear_cache(self):
        """
        (3.2.1) Clear User Cache
        Clears the user cache on the device.
        Generally speaking, most Capture API calls can be performed by either "local users", such as an 
        admin or instructor, or ESS users, such as capture devices. When a user accesses any of the capture 
        API calls, the user is authenticated against the ESS. The API sends the credentials to the ESS and 
        the ESS responds to the API indicating authentication (or failure) for the user. This process can 
        take some time, so it is not done for every call. Instead, whenever successful ESS user 
        authentication occurs, the API caches the user credentials and validates against that, speeding up 
        response time. However, if an ESS administrator changes a user's password, deletes an account or a 
        device, or other similar action, the Capture API has no way of knowing. In this instance, the admin 
        can either, reset/power cycle the capture device, or use this API call to force clear the cache.

        curl --silent --user $adminlogincreds --insecure -d --url $apiurl"/diagnostics/clear_cache"
        """
        return self.call_api('diagnostics/clear_cache', method='POST', 
            title='Clear User Cache')

    def diagnostics_ping(self, url):
        """
        (3.2.2) Ping Host Connectivity
        Test the connectivity of a host or an IP using the ping utility.

        curl --silent --user $adminlogincreds --insecure -d --url $apiurl"/diagnostics/ping/www.google.com"
        """
        return self.call_api('diagnostics/ping/' + url, method='POST', title='Ping Host Connectivity')

    def diagnostics_traceroute(self, url):
        """
        (3.2.3) Trace Route Path and Time
        Returns the route path and transit time of a host on an IP.

        curl --silent --user $adminlogincreds --insecure -d --url $apiurl"/diagnostics/traceroute/www.google.com"
        """
        return self.call_api('diagnostics/traceroute/' + url, method='POST', title='Trace Route Path and Time')

    def diagnostics_restart_all(self):
        """
        (3.2.4) Restart Device Executables
        Restarts all of the Device executables.

        curl --silent -d --user $adminlogincreds --insecure --url $apiurl"/diagnostics/restart_all"
        """
        return self.call_api('diagnostics/restart_all', method='POST', title='Restart Device Executables')

    def diagnostics_reboot(self):
        """
        (3.2.5) Reboot Device
        Performs a soft reboot of the Device.

        curl --silent -d --user $adminlogincreds --insecure --url $apiurl"/diagnostics/reboot"
        """
        return self.call_api('diagnostics/reboot', method='POST', title='Reboot Device')

    def diagnostics_system_info_ifconfig(self):
        """
        (3.2.6) Get Device Network Configuration
        Returns the network configuration for the Device.

        curl --silent --user $adminlogincreds --insecure --url $apiurl"/diagnostics/system-info/ifconfig"
        """
        return self.call_api('diagnostics/system-info/ifconfig', title='Get Device Network Configuration')

    def diagnostics_system_info_tasks(self):
        """
        (3.2.7) Get Device Tasks
        Returns the current tasks file for the Device. The task file is basically a list of the 
        currently scheduled captures (tasks) for the device.

        curl --silent --user $adminlogincreds --insecure --url $apiurl"/diagnostics/system-info/tasks"
        """
        return self.call_api('diagnostics/system-info/tasks', title='Get Device Tasks')

    def diagnostics_system_info_device(self):
        """
        (3.2.8) Get Device Configuration File
        Returns the contents of the device XML file for the Device.

        curl --silent --user $adminlogincreds --insecure --url $apiurl"/diagnostics/system-info/device"
        """
        return self.call_api('diagnostics/system-info/device', title='Get Device Configuration File')

    def diagnostics_system_info_top(self):
        """
        (3.2.9) Get Device Processes
        Returns a list of the processes currently running on the Device.

        curl --silent --user $adminlogincreds --insecure --url $apiurl"/diagnostics/system-info/top"
        """
        return self.call_api('diagnostics/system-info/top', title='Get Device Processes')

    def diagnostics_system_info_dmesg(self):
        """
        (3.2.10) Get Device Message Buffer
        Returns the message buffer of the Device kernel.

        curl --silent --user $adminlogincreds --insecure --url $apiurl"/diagnostics/system-info/dmesg"
        """
        return self.call_api('diagnostics/system-info/dmesg', title='Get Device Message Buffer')

    def diagnostics_recovery_saved_content(self):
        """
        (3.2.11) Get Saved Content on the Device
        Returns a list of all saved content on the device. Can be used to determine if recovery of a capture 
        is necessary, and if so, to obtain the capture ID of the capture to be re-uploaded.

        curl --silent --user $adminlogincreds --insecure --url $apiurl"/diagnostics/recovery/saved-content"
        """
        # TODO: Can be many captures. Will cuurently fail if more than one.
        response = self.call_api('diagnostics/recovery/saved-content', title='Get Saved Content on the Device')
        if response.success():
            response.add_value('capture/title')
            response.add_timestamp('capture/start-time')
            response.add_value('capture/duration')
            response.add_value('capture/section')
        return response        

    def diagnostics_capture_id_upload(self, id):
        """
        (3.2.12) Re-Upload Content from the Device to the ESS
        Reuploads saved content from the device to the ESS. Use the capture ID returned from the Get Saved Content 
        on the Device call identified in section 3.2.11 above to identify the capture to upload and obtain the 
        capture ID.

        curl --silent --user $adminlogincreds --insecure -d --url $apiurl"/diagnostics/recovery/4d951a96-9702-4321-abe6-a0f232ae1e36/upload"
        """
        raise "unimplemented"

    def log_list_last_count(self, count, dump_xml=None):
        """
        (3.2.13) Retrieve the Last X Number of Log Messages
        Returns the last x number of log messages specified in the call. 

        curl --silent --user $adminlogincreds --insecure --url $apiurl"/log-list-last-count/3"
        """
        response = self.call_api('log-list-last-count/' + str(count), title='Retrieve the Last X Number of Log Messages', dump_xml=dump_xml)
        if dump_xml:
            return response
        if response.xml() is not None:
            xml = response.xml()
            entries = []
            for child in xml:
                entry = {}
                for line in child.text.split('\n'):
                    if len(line) > 0:
                        #print line
                        part = line.split(':', 1)
                        entry[part[0]] = part[1].replace('"', '').strip()
                entries.append(entry)
            response.entries = entries # List of Dict's
            return response 

    # (3.3) CaptureControlAPICalls
    # The API calls described below are used to create and manipulate captures performed by the capture device 
    # identified in the call.

    def capture_new_capture(self, duration, profile, description):
        """
        (3.3.1) Create New Capture
        Creates and starts a new ad-hoc capture using the parameters described in the table below. 
        All parameters must be defined.

        'duration' is in seconds.

        curl --user $adminlogincreds --insecure --data "duration=300&capture_profile_name=display-audio&description=test-description" -d --url $apiurl"/capture/new_capture"
        # <ok text="Capture scheduled for start" />
        """
        response = self.call_api('capture/new_capture', 
            post_data='duration={0}&capture_profile_name={1}&description={2}'.format(duration, profile, description),
            title='Create New Capture')
        response.check_for_error()
        return response        

    def capture_confidence_monitor(self, duration, profile, description):
        """
        (3.3.2) Create "Confidence Monitor" Capture
        Creates and starts a new ad-hoc "confidence monitor" capture, providing monitoring of the capture. 
        All parameters, described in the below table, must be defined.
        A confidence monitor is a dummy capture that does not get archived, sent to the ESS, or saved in any way. 
        In all other regards. this call functions the same as a "new_capture" call described immediately above.
        If you want to confirm a real capture will work, use the Show Current Video or Display View call described 
        in section 3.1.6 above.

        'duration' is in seconds.

        curl --user admin:password --insecure --data 'duration=900&capture_profile_name=Display/Video (Podcast/Vodcast/EchoPlayer).
            Optimized for quality/full motion video&description=test-description' 
            --url https://192.168.61.10:8443/capture/confidence_monitor
        # <ok text="Capture scheduled for start" />
        """
        response = self.call_api('capture/confidence_monitor', 
            post_data='duration={0}&capture_profile_name={1}&description={2}'.format(duration, profile, description),
            title='Create Confidence Monitor Capture')
        response.check_for_error()
        return response               

    def capture_extend(self, duration):
        """
        (3.3.3) Extend a Capture
        Sends a command to extend the current capture by the amount of time, in seconds, provided in the duration 
        parameter. Captures cannot be extended past the start time of the next scheduled capture.
        If the capture cannot be extended for the duration identified, the capture will be extended as far as 
        possible within the given schedule constraints.

        'duration' is in seconds.

        curl --user $adminlogincreds --insecure --data "duration=300&extend=Submit+Query" --url $apiurl"/capture/extend"
        # <ok text="Extend by 300 seconds recieved" />
        """
        response = self.call_api('capture/extend', 
            post_data='duration={0}&extend=Submit+Query'.format(duration),
            title='Extend a Capture')
        response.check_for_error()
        return response

    def capture_pause(self):
        """
        (3.3.4) Pause a Capture
        Sends a command to pause the current recording. There must be a running capture in the recording state for this 
        command to have any effect.

        curl --user $logincreds --insecure --data "" -d --url $apiurl"/capture/pause"
        # <ok text="Command (pause) submitted" />
        """
        response = self.call_api('capture/pause', method='POST', title='Pause a Capture')
        response.check_for_error()
        return response        

    def capture_record(self):
        """
        (3.3.5) Start or Resume a Capture
        Sends a command to start recording. This command only works under following two conditions:
        There is a running capture that is currently paused. This command resumes the paused capture.
        There is a scheduled capture in the "waiting" or pre-roll state. This command allows you to start the scheduled 
        recording early/immediately.

        curl --user $logincreds --insecure --data "" -d --url $apiurl"/capture/record"
        # <ok text="Command (record) submitted" />
        """
        response = self.call_api('capture/record', method='POST', title='Start or Resume a Capture')
        response.check_for_error()
        return response        

    def capture_stop(self):
        """
        (3.3.6) Stop a Capture
        Sends the command to stop recording. There must be a currently recording capture for this command to have any 
        effect. NOTE that captures are processed and uploaded immediately upon stopping the capture.

        curl --user $logincreds --insecure --data "" -d --url $apiurl"/capture/stop"
        # <ok text="Command (stop) submitted" />
        """
        response = self.call_api('capture/stop', method='POST', title='Stop a Capture')
        response.check_for_error()
        return response               

    def __str__(self):
        return 'Cature device {0}, user {1}'.format(self.server, self.username)
 

class Echo360CaptureDeviceResponse(object):
    """
    Other results are added as attributes of the object.
    """

    def __init__(self, command=None, result_code=None, result_message=None, data=None, xml_data=None, 
            device=None, utc_offset=None, title=None, dump_xml=None):
        self._command = command.replace('/', '_').replace('-', '_')
        self._result_code = result_code
        self._result_message = result_message
        self._data = data
        self._xml = xml_data    # might be None
        self.title(title)
        self._device = device
        self._utc_offset = utc_offset
        self._dump_xml = dump_xml

    def title(self, new_title):
        if new_title is None:
            if self._title is None:
                return self._command
            else:
                return self._title
        else:
            self._title = new_title
            return self._title

    def add_value(self, xpath, name=None):
        # Adds a value to the response using attribute name 'name'.
        # Return 'name' (e.g. 'start_time'). Method will fail if no XML data.
        # The attribute is set to the desired value, if found in the XML data, or None.
        if name is None:
            name = xpath.replace('/', '_').replace('-', '_')
        text = self._xml.find('./' + xpath)
        if text is None:
            self.__dict__[name] = None
        else:
            self.__dict__[name] = text.text
        return name

    def add_timestamp(self, xpath, name=None):
        # Adds a value to the response using appribute name 'name', and also name_local with the
        # timestamp in local time, using self._utc_offset.
        # Returns the attribute 'name' or 'name'_local. (e.g. 'start_time' or 'start_time_local').
        # Method will fail if no XML data.
        # Capture device timestamps are always UTC (e.g. '2014-06-05T00:27:37.000Z').
        # The attribute is set to the local time, or None if the timestamp is None or if self._utc_offset is None.
        name = self.add_value(xpath, name)
        node_value = self.__dict__[name]
        if node_value is None:
            return name
        local_name = name + '_local'
        if self._utc_offset is None:
            self.__dict__[local_name] = None
        else:
            ts_struct_time = time.strptime(node_value.split('.',1)[0], "%Y-%m-%dT%H:%M:%S")
            ts_datetime = datetime.datetime.fromtimestamp(time.mktime(ts_struct_time)) + \
                datetime.timedelta(minutes = int(self._utc_offset))
            self.__dict__[local_name] = ts_datetime.strftime('%Y-%m-%dT%H:%M:%S')
        return local_name

    def check_attribute(self, attr):
        if attr in self.__dict__:
            if self.__dict__[attr] is not None:
                return True
        return False

    def check_for_error(self):
        # check for:
        #    <ok text="Command (pause) submitted" />
        #    <error text="Failed on command (stop).  No capture is running." />
        if self._xml is not None:
            if self._xml.tag == 'ok':
                self._result_code = 'success'
                self._result_message = self._xml.attrib['text']
            elif self._xml.tag == 'error':
                self._result_code = 'error'
                self._result_message = self._xml.attrib['text']

    def xml(self):
        return self._xml

    def __str__(self):
        # Useful for testing and in CLI situations.
        if self.success():
            string = '{0}: {1} {2}'.format(self._command, self._result_code, self._result_message)
            data = []
            for key in sorted(self.__dict__):
                if not key.startswith('_'):
                    data.append('{0}: {1}'.format(key, self.__dict__[key]))
            if len(data) > 0:
                string += '\nData: ' + '\n  '.join(data)
            if self._dump_xml:
                string = string + '\nRaw XML:\n' + self._data
            return string
        elif self._result_code == 401:
            return 'You are not authorised to use the command {0}'.format(self._command)
        else:
            return 'Command failed {0}: {1} {2}'.format(self._command, self._result_code, self._result_message)

    def success(self):
        return self._result_code == 'success'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Echo360 Capture Device CLI',
        )
    parser.add_argument('-s', '--server', help='capture device ', required=True)
    parser.add_argument('-u', '--user', help='username', default='admin')
    parser.add_argument('-p', '--password', help='password', default=None)
    parser.add_argument('-d', '--debug', help='debug level', default=0, type=int)
    parser.add_argument('-t', '--timeout', help='HTTP timeout', default=4, type=int)
    parser.add_argument('-l', '--sleep', help='sleep before status (seconds)', default=2, type=int)
    parser.add_argument('-c', '--command', help='command (e.g. status)', default='status',
        choices=['system-status', 'status', 
            'new-capture', 'confidence-monitor', 'pause', 'resume', 'extend', 'stop',
            'status-get-user-sections', 'status-get-user-ref', 'diagnostics-clear-cache',
            'ping', 'traceroute', 'restart-all', 'reboot', 'log', 'system-info',
            'status-captures', 'status-current-capture', 'status-next-capture',
            'test-system', 'test-status', 'test-capture', 'test-confidence'])
    parser.add_argument('--duration', help='duration (seconds)', default=3600+1800, type=int)
    parser.add_argument('--profile', help='profile name', default=None)
    parser.add_argument('--description', help='description', default='capture-device.py')
    parser.add_argument('--count', help='execute command multiple times', default=1, type=int)
    parser.add_argument('--url', help='URL for ping and traceroute', default=None)
    parser.add_argument('--xml', help='Print the raw XML', action='store_true')
    args = parser.parse_args()

    try:    # catch ctrl-c
        device = Echo360CaptureDevice(args.server, args.user, args.password, 
            debuglevel=args.debug, timeout=args.timeout)

        # test access
        if not device.connection_test.success():
            if device.connection_test._result_code == 401:
                print('Connection Test Error (401): Incorrect capture device username or password.')
                sys.exit(1)
            elif device.connection_test._result_code == 404:
                print('Connection Test Error (404): Capture Device API error: command not found.')
                sys.exit(2)
            else:
                print('Connection Test Error ({0}): {1} to {2}'.format(
                    device.connection_test._result_code, device.connection_test._result_message, args.server))
                sys.exit(3)

        if args.command == 'system-status':
            print(str(device.status_system(dump_xml=args.xml)))
        elif args.command == 'status':
            print(device.capture_status_str())
            if args.count > 1:
                for i in range(1, args.count):
                    print(device.capture_status_str(sleep=args.sleep))
        # TODO: monitoring_snapshot(self, url)
        elif args.command == 'new-capture':
            print(str(device.capture_new_capture(args.duration, args.profile , args.description)))
            print(device.capture_status_str(sleep=args.sleep))
        elif args.command == 'confidence-monitor':
            print(str(device.capture_confidence_monitor(args.duration, args.profile , args.description)))
            print(device.capture_status_str(sleep=args.sleep))
        elif args.command == 'pause':
            print(str(device.capture_pause()))
            print(device.capture_status_str(sleep=args.sleep))
        elif args.command == 'resume':
            print(str(device.capture_record()))
            print(device.capture_status_str(sleep=args.sleep))
        elif args.command == 'extend':
            print(str(device.capture_extend(args.duration)))
            print(device.capture_status_str(sleep=args.sleep))
        elif args.command == 'stop':
            print(str(device.capture_stop()))
            print(device.capture_status_str(sleep=args.sleep))
        elif args.command == 'status-get-user-sections':
            # TODO: print(str(device.status_get_user_sections()))
            print('Not implemented yet.')
        elif args.command == 'status-get-user-ref':
            print(str(device.status_get_user_ref(dump_xml=args.xml)))
        elif args.command == 'diagnostics-clear-cache':
            print(str(device.diagnostics_clear_cache()))
        elif args.command == 'ping':
            if args.url is None:
                print("No ping URL specified. Use '--url'")
            else:
                response = device.diagnostics_ping(args.url)
                if response.success():
                    print('{0}\n{1}'.format(str(response), response._data))
                else:
                    print(str(response))
        elif args.command == 'traceroute':
            if args.url is None:
                print("No traceroute URL specified. Use '--url'")
            else:
                response = device.diagnostics_traceroute(args.url)
                if response.success():
                    t = response._data.replace('<br/>', '\n')
                    print('{0}\n{1}'.format(str(response), t))
                else:
                    print(str(response))
        elif args.command == 'restart-all':
            print(str(device.diagnostics_restart_all()))
        elif args.command == 'reboot':
            print(str(device.diagnostics_reboot()))
        elif args.command == 'log':
            print(json.dumps(device.log_list_last_count(args.count, dump_xml=args.xml).entries, indent=4, sort_keys=True))
        elif args.command == 'system-info':
            response = device.diagnostics_system_info_ifconfig()
            if response.success():
                t = response._data.replace('<pre>', '\n').replace('</pre>', '\n')
                print('{0}\n{1}'.format(str(response), t))
            else:
                print(str(response))
            # TODO: XML result
            # response = device.diagnostics_system_info_device()
            # print('{0}\n{1}'.format(str(response), response._data))
            response = device.diagnostics_system_info_top()
            if response.success():
                t = response._data.replace('<head><meta http-equiv="refresh" content="5"></head>', '').replace('<pre>', '\n').replace('</pre>', '\n')
                print('{0}\n{1}'.format(str(response), t))
            else:
                print(str(response))
            response = device.diagnostics_system_info_dmesg()
            if response.success():
                t = response._data.replace('<pre>', '\n').replace('</pre>', '\n')
                print('{0}\n{1}'.format(str(response), t))
            else:
                print(str(response))
        elif args.command == 'status-captures':
            print(str(device.status_captures(dump_xml=args.xml)))
        elif args.command == 'status-current-capture':
            print(str(device.status_current_capture(dump_xml=args.xml)))
        elif args.command == 'status-next-capture':
            print(str(device.status_next_capture(dump_xml=args.xml)))
        elif args.command == 'test-system':
            print('\nDevice status_system')
            print(str(device.status_system(dump_xml=args.xml)))
        elif args.command == 'test-status':
            print('\nDevice status_system')
            print(str(device.status_system(dump_xml=args.xml)))
            print('\nDevice status_monitoring')
            print(str(device.status_monitoring(dump_xml=args.xml)))
            print('\nDevice status_captures')
            print(str(device.status_captures(dump_xml=args.xml)))
            print('\nDevice status_current_capture')
            print(str(device.status_current_capture(dump_xml=args.xml)))
            print('\nDevice status_next_capture')
            print(str(device.status_next_capture(dump_xml=args.xml)))
        elif args.command == 'test-capture':
            sleep = args.sleep
            print('\nstop; new_capture; pause; record; extend; pause; stop')
            print(str(device.capture_stop()))
            print(device.capture_status_str(sleep=sleep))
            print(str(device.capture_new_capture(3500, 'Trinity Standard Lecture', 'test from python')))
            print(device.capture_status_str(sleep=sleep))
            print(str(device.capture_pause()))
            print(device.capture_status_str(sleep=sleep))
            print(str(device.capture_record()))
            print(device.capture_status_str(sleep=sleep))
            print(str(device.capture_extend(400)))
            print(device.capture_status_str(sleep=sleep))
            print(str(device.capture_pause()))
            print(device.capture_status_str(sleep=sleep))
            print(str(device.capture_stop()))
            print(device.capture_status_str(sleep=sleep))
        elif args.command == 'test-confidence':
            sleep = args.sleep
            print('\nconfidence_monitor; stop')
            print(str(device.capture_confidence_monitor(360, 'Trinity Standard Lecture', 'test from python')))
            print(device.capture_status_str(sleep=sleep))
            print(str(device.capture_stop()))
            print(device.capture_status_str(sleep=sleep))

    except KeyboardInterrupt:
        print('\nCtrl-C User requested exit.')


