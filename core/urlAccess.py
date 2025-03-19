#
# Do NOT modify or remove this copyright and license
#
# Copyright (c) 2019 Seagate Technology LLC and/or its Affiliates, All Rights Reserved
#
# This software is subject to the terms of the MIT License. If a copy of the license was
# not distributed with this file, you can obtain one at https://opensource.org/licenses/MIT.
#
# ******************************************************************************************
#
# urlAccess.py - This module provides a common access point for all URL accesses. 
#
# ******************************************************************************************
#

from core.label import Label
from core.redfishConfig import RedfishConfig
from core.trace import TraceLevel, Trace
from core.jsonBuilder import JsonBuilder, JsonType
import base64
import config
import json
import os
import requests
import socket
import ssl
import sys
import time
import traceback
import urllib.request, urllib.error
import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning

################################################################################
# UrlStatus
################################################################################
class UrlStatus():
    url = ''
    urlStatus = 0
    urlReason = ''
    response = None
    urlData = None
    jsonData = None
    xmlData = None
    sessionKey = ''
    checked = False
    valid = False
    elapsedMicroseconds = 0
    parent = ''
    context = ''

    def __init__(self, url):
        self.url = url

    def do_check(self):
        return (self.checked == False)

    def add_url(self, url):
        self.url = url
        Trace.log(TraceLevel.TRACE, '   ++ UrlStatus(add): url=({})'.format(url))

    def update_status(self, status, reason):
        self.urlStatus = status
        self.urlReason = reason
        self.checked = True
        Label.encode(config.httpStatusVariable, status)

        if (status == 200 or status == 201):
            self.valid = True

        Trace.log(TraceLevel.TRACE, '   ++ UrlStatus(update_status): status={} reason={} valid={}'.format(status, reason, self.valid))

    def print_status(self): # TODO change to Trace.log
        Trace.log(TraceLevel.INFO, '')
        Trace.log(TraceLevel.INFO, ' [] URL        : {}'.format(self.url))
        Trace.log(TraceLevel.INFO, ' [] Status     : {}'.format(self.urlStatus))
        Trace.log(TraceLevel.INFO, ' [] Reason     : {}'.format(self.urlReason))
        if self.urlStatus > 200 and self.context != '':
            Trace.log(TraceLevel.INFO, ' [] Context    : {}'.format(self.context))

################################################################################
# UrlAccess
################################################################################
class UrlAccess():

    #
    # process_push
    #     Used to perform an HTTP push of a file and possible JSON data.
    #     Authentication data is automatically added to the HTTP request.
    #     These method uses the python requests package
    #
    @classmethod
    def process_push(self, redfishConfig: RedfishConfig, link: UrlStatus, filename, payload = None):
        Trace.log(TraceLevel.INFO, '++ UrlAccess: process_push - ({}) session ({}:{})'.format(link.url, Label.decode(config.sessionIdVariable), redfishConfig.sessionKey))

        startTime = time.time()

        warnings.filterwarnings('ignore', message='Unverified HTTPS request')

        s = requests.Session()

        fullUrl = redfishConfig.get_value('http') + '://' + redfishConfig.get_ipaddress() + ":" + redfishConfig.get_port() + link.url
        Trace.log(TraceLevel.INFO, '   -- fullUrl: {}'.format(fullUrl))
        Trace.log(TraceLevel.INFO, '   -- filename ({})'.format(filename))

        JsonBuilder.startNew()
        JsonBuilder.newElement('jsonpayload', JsonType.DICT)

        # Add authentication
        if redfishConfig.get_basicauth():
            encoded = base64.b64encode(str.encode(redfishConfig.get_value('username') + ':' + redfishConfig.get_value('password')))
            Trace.log(TraceLevel.DEBUG, '   -- HTTP Basic Authorization: {}'.format(encoded))
            s.headers.update({'Authorization': 'Basic ' + str(encoded), })
        else:
            Trace.log(TraceLevel.INFO, '   -- X-Auth-Token: {}'.format(redfishConfig.sessionKey))
            s.headers.update({'X-Auth-Token': redfishConfig.sessionKey})

        # Add passed in JSON data
        if payload is not None:
            Trace.log(TraceLevel.INFO, '   -- post w/ JSON')
            if (redfishConfig.get_bool('dumppostdata')):
                Trace.log(TraceLevel.INFO, '[[ PAYLOAD DATA ({}) ]]'.format(link.url))
                Trace.log(TraceLevel.INFO, json.dumps(payload, indent=4))
                Trace.log(TraceLevel.INFO, '[[ PAYLOAD DATA END ]]')
        else:
            payload = {}

        files = {
            'json': (None, json.dumps(payload), 'application/json'),
            'file': (os.path.basename(filename), open(filename, 'rb'), 'application/octet-stream')
        }

        try:
            response = s.request('POST', fullUrl, files=files, verify=False)
            link.urlData = response.text
            link.update_status(response.status_code, response.reason)
            try:
                link.jsonData = json.loads(link.urlData)
            except:
                pass

            # Trace.log(TraceLevel.INFO, '============================== RESPONSE ==============================')
            # Trace.log(TraceLevel.INFO, response.content)
            # Trace.log(TraceLevel.INFO, response.text)
            # Trace.log(TraceLevel.INFO, 'status_code: {}'.format(response.status_code))
            # Trace.log(TraceLevel.INFO, 'reason: {}'.format(response.reason))
            # Trace.log(TraceLevel.INFO, 'request: {}'.format(response.request))
            # Trace.log(TraceLevel.INFO, '============================== END RESPONSE ==============================')

        except Exception as e:
            Trace.log(TraceLevel.ERROR, 'Exception: request(POST) - {}'.format(e))
            link.update_status(418, 'Exception: request(POST) - ' + str(e))

        link.elapsedMicroseconds = (time.time() - startTime) * 1000000

        return link

    #
    # process_request
    #     Used to perform an HTTP operation of GET, POST, DELETE.
    #     Authentication data is automatically added to the HTTP request.
    #     These method should be updated to use the python requests package
    #
    @classmethod
    def process_request(self, redfishConfig: RedfishConfig, link: UrlStatus, method = 'GET', addAuth = True, data = None, decode = True):

        try:
            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

            Trace.log(TraceLevel.TRACE, '   ++ UrlAccess: process_request - {} ({}) session ({}:{})'.format(method, link.url, Label.decode(config.sessionIdVariable), redfishConfig.sessionKey))
            fullUrl = redfishConfig.get_value('http') + '://' + redfishConfig.get_ipaddress() + ":" + redfishConfig.get_port() + link.url
            Trace.log(TraceLevel.TRACE, '   -- fullUrl: {}'.format(fullUrl))

            headers = {}
            headers['Host'] = socket.gethostname()

            authorization = None
            if redfishConfig.get_basicauth() == True:
                Trace.log(TraceLevel.DEBUG, '   -- Using HTTP Basic Auth')
                authorization = (redfishConfig.get_value('username'), redfishConfig.get_value('password'))
                Trace.log(TraceLevel.DEBUG, '   ++ Authorization: {}'.format(authorization))
            elif addAuth == True and redfishConfig.sessionKey is not None:
                headers['X-Auth-Token'] = redfishConfig.sessionKey
                Trace.log(TraceLevel.DEBUG, '   ++ X-Auth-Token: {}'.format(redfishConfig.sessionKey))

            startTime = time.time()
            Trace.log(TraceLevel.TRACE, '   >> startTime={}'.format(startTime))

            if data is not None:
                headers['If-None-Match'] = '""'
                headers['Content-Type'] = 'application/json; charset=UTF-8'
                if (redfishConfig.get_bool('dumppostdata')):
                    Trace.log(TraceLevel.INFO, '[[ POST DATA ({}) ]]'.format(link.url))
                    Trace.log(TraceLevel.INFO, "{}".format(json.dumps(data, indent=4)))
                    Trace.log(TraceLevel.INFO, '[[ POST DATA END ]]')

            Trace.log(TraceLevel.DEBUG, '   >> headers={}'.format(headers))
            link.response = requests.request(
                method, fullUrl, headers=headers, auth=authorization, json=data,
                timeout=redfishConfig.get_urltimeout(), verify=redfishConfig.get_bool('certificatecheck'))
            
            Trace.log(TraceLevel.TRACE, '   >> request.headers={}'.format(link.response.request.headers))
            Trace.log(TraceLevel.TRACE, '   >> request.body={}'.format(link.response.request.body))

            endTime = time.time()
            elapsed = (endTime - startTime) * 1000000
            Trace.log(TraceLevel.TRACE, '   >> endTime={}'.format(endTime))
            Trace.log(TraceLevel.TRACE, '   >> elapsed={}'.format(elapsed))
            link.elapsedMicroseconds = elapsed

            if decode:
                link.urlData = link.response.text
            else:
                link.urlData = link.response.content

            Trace.log(TraceLevel.TRACE, '[[ response.text ]]')
            Trace.log(TraceLevel.TRACE, '{}'.format(link.response.text))
            Trace.log(TraceLevel.TRACE, '[[ response.text END ]]')

            Trace.log(TraceLevel.TRACE, '[[ response.content ]]')
            Trace.log(TraceLevel.TRACE, '{}'.format(link.response.content))
            Trace.log(TraceLevel.TRACE, '[[ response.content END ]]')

            if link.response.text != '' and link.response.headers is not None:
                try:
                    contentTypeHandled = False                    
                    headers = link.response.headers
                    Trace.log(TraceLevel.TRACE, '   -- headers: {}'.format(headers))
                    for key, value in headers.items():
                        Trace.log(TraceLevel.TRACE, '   -- HEADER {}: {}'.format(key, value))
                        if key == 'Content-Type':
                            if 'json' in value:
                                link.jsonData = link.response.json()
                                contentTypeHandled = True
                            elif 'application/xml' in value:
                                contentTypeHandled = True
                                link.xmlData = link.urlData
                            elif 'application/zip' in value:
                                contentTypeHandled = True
                            elif 'IntentionallyUnknownMimeType' in value:
                                contentTypeHandled = True
                            elif 'text/html' in value:
                                Trace.log(TraceLevel.VERBOSE, 'html: {}'.format(link.response.text))

                    if not contentTypeHandled:
                        Trace.log(TraceLevel.WARN, '   ++ UrlAccess: unhandled Content-Type: {}'.format(headers['Content-Type']))

                except Exception as inst:
                    Trace.log(TraceLevel.INFO, '   -- Exception: Trying to convert to JSON data, url={}'.format(fullUrl))
                    Trace.log(TraceLevel.INFO, '   -- jsonData={} -- {}'.format(link.jsonData, sys.exc_info()[0], inst))
                    Trace.log(TraceLevel.INFO, '-'*100)
                    Trace.log(TraceLevel.INFO, '   -- urlData={}'.format(link.urlData))
                    Trace.log(TraceLevel.INFO, '-'*100)
                    traceback.print_exc(file=sys.stdout)
                    Trace.log(TraceLevel.INFO, '-'*100)

            else:
                Trace.log(TraceLevel.TRACE, '   ++ UrlAccess: process_request // No urlData')

            link.update_status(link.response.status_code, link.response.reason)

            if (redfishConfig.get_bool('dumpjsondata')):
                if (link.jsonData is not None):
                    Trace.log(TraceLevel.INFO, '[[ JSON DATA ({}) ]]'.format(link.url))
                    Trace.log(TraceLevel.INFO, json.dumps(link.jsonData, indent=4))
                    Trace.log(TraceLevel.INFO, '[[ JSON DATA END ]]')

            link.response.close()

        except socket.timeout:
            link.update_status(598, 'socket.timeout')
            Trace.log(TraceLevel.TRACE, '   ++ UrlAccess: process_request // ERROR receiving data from ({}): Socket Error {}: {}'.format(link.url, 598, 'socket.timeout'))

        except urllib.error.HTTPError as err:
            link.update_status(err.code, err.reason)
            Trace.log(TraceLevel.TRACE, '   ++ UrlAccess: process_request // ERROR receiving data from ({}): HTTP Error {}: {}'.format(link.url, err.code, err.reason))
            Trace.log(TraceLevel.TRACE, '===== [[ headers DATA ]] =====')
            Trace.log(TraceLevel.TRACE, '{}'.format(err.headers))
            Trace.log(TraceLevel.TRACE, '[[ headers DATA END ]]')

            link.context = err.headers.get('command-status')
            Trace.log(TraceLevel.DEBUG, '   -- command-status: {}'.format(link.context))

        except urllib.error.URLError as err:
            errorCode = 0
            if hasattr(err,'code'):
                errorCode = err.code
            errorReason = 'Unknown'
            if hasattr(err,'reason'):
                errorReason = err.reason
            Trace.log(TraceLevel.TRACE, '   ++ UrlAccess: process_request // ERROR receiving data from ({}): URL Error code={} reason={}'.format(link.url, errorCode, errorReason))
            link.update_status(errorCode, errorReason)

            # Print the contents of the HTTP message response
            read_op = getattr(err, "read", None)
            if (callable(read_op)):
                Trace.log(TraceLevel.INFO, '')
                Trace.log(TraceLevel.INFO, '='*120)
                errorMessage = err.read()
                if (redfishConfig.get_bool('dumphttpdata')):
                    Trace.log(TraceLevel.INFO, 'httpData: {}'.format(errorMessage))
                else:
                    Trace.log(TraceLevel.INFO, 'errorMessage = {}'.format(errorMessage))
                Trace.log(TraceLevel.INFO, '='*120)
        
        return link
