#
# Do NOT modify or remove this copyright and license
#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates, All Rights Reserved
#
# This software is subject to the terms of the MIT License. If a copy of the license was
# not distributed with this file, you can obtain one at https://opensource.org/licenses/MIT.
#
# ******************************************************************************************
#
# listener.py - Thread for Redfish event listener.
#
# ******************************************************************************************
#

import traceback
import json
import ssl
import socket
from datetime import datetime
import threading
from http_parser.http import HttpStream
from http_parser.reader import SocketReader
from core.trace import TraceLevel, Trace

event_count = {}

################################################################################
# Listener - Class to listen for events
################################################################################

class Listener(threading.Thread):

    #
    # Init the listener thread
    #
    def __init__(self, redfishConfig):
        super(Listener, self).__init__()
        self.redfishConfig = redfishConfig
        self.stop = False

    #
    # Stop the listener thread
    #
    def shutdown(self):
        self.stop = True
        self.join()
        self.redfishConfig.listener = None

    #
    # Listener thread
    #
    def run(self):
        Trace.log(TraceLevel.DEBUG, '++ Starting the listener...')
        # Accept the TCP connection using certificate validation using Socket wrapper
        useSSL = self.redfishConfig.get_bool('listenerusessl')
        context = None
        if useSSL:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(certfile=self.redfishConfig.get_value('certfile'), keyfile=self.redfishConfig.get_value('keyfile'))

        # Bind socket connection and listen on the specified port
        my_host = (self.redfishConfig.get_value('listenerip'), self.redfishConfig.get_int('listenerport'))
        Trace.log(TraceLevel.DEBUG, '++ Listening on {}:{} via {}'.format(self.redfishConfig.get_value('listenerip'), self.redfishConfig.get_int('listenerport'), 'HTTPS' if useSSL else 'HTTP'))

        # Check if the listener is IPv4 or IPv6; defaults to IPv4 if the lookup fails
        try:
            family = socket.getaddrinfo(self.redfishConfig.get_value('listenerip'), self.redfishConfig.get_int('listenerport'))[0][0]
        except:
            family = socket.AF_INET
        socket_server = socket.create_server(my_host, family=family)
        socket_server.listen(5)
        socket_server.settimeout(3)

        while True:
            # Stop listener if needed
            if self.stop:
                Trace.log(TraceLevel.DEBUG, '++ Stopping the listener...')
                socket_server.close()
                break

            newsocketconn = None
            try:
                # Socket Binding
                newsocketconn, fromaddr = socket_server.accept()
                try:
                    # Multiple Threads to handle different request from different servers
                    Trace.log(TraceLevel.DEBUG, '\n++ Socket connected::')
                    ProcessData(newsocketconn, fromaddr, useSSL, context).start()
                except Exception as err:
                    Trace.log(TraceLevel.ERROR, traceback.print_exc())
            except socket.timeout:
                Trace.log(TraceLevel.DEBUG, '++')
            except Exception as err:
                Trace.log(TraceLevel.ERROR, "Exception occurred in socket binding.")
                Trace.log(TraceLevel.ERROR, traceback.print_exc())


################################################################################
# ProcessData - Class to read data in json format using HTTP Stream reader,
#               parse Headers and Body data, Response status OK to service and
#               Update the output into file
################################################################################

class ProcessData(threading.Thread):

    #
    # Init the process data thread
    #
    def __init__(self, newsocketconn, fromaddr, useSSL, context):
        super(ProcessData, self).__init__()
        self.newsocketconn = newsocketconn
        self.fromaddr = fromaddr
        self.useSSL = useSSL
        self.context = context

    #
    # Process data thread
    #
    def run(self):
        if self.useSSL:
            connstreamout = self.context.wrap_socket(self.newsocketconn, server_side=True)
        else:
            connstreamout = self.newsocketconn
        # Output File Name
        outputfile = "Events_" + str(self.fromaddr[0]) + ".txt"
        global event_count
        outdata = headers = hostdetails = ""
        try:
            try:
                # Read the json response using Socket Reader and split header and body
                r = SocketReader(connstreamout)
                p = HttpStream(r)
                headers = p.headers()
                Trace.log(TraceLevel.DEBUG, '++ headers: {}'.format(headers))

                if p.method() == 'POST':
                    bodydata = p.body_file().read()
                    bodydata = bodydata.decode("utf-8")
                    Trace.log(TraceLevel.DEBUG, '\n')
                    Trace.log(TraceLevel.DEBUG, '++ bodydata: {}'.format(bodydata))
                    for eachHeader in headers.items():
                        if eachHeader[0] == 'Host' or eachHeader[0] == 'host':
                            hostdetails = eachHeader[1]

                    # Read the json response and print the output
                    Trace.log(TraceLevel.DEBUG, '\n')
                    Trace.log(TraceLevel.DEBUG, '++ Server IP Address is {}'.format(self.fromaddr[0]))
                    Trace.log(TraceLevel.DEBUG, '++ Server PORT number is {}'.format(self.fromaddr[1]))
                    Trace.log(TraceLevel.DEBUG, '++ Listener IP is {}'.format(hostdetails))
                    Trace.log(TraceLevel.DEBUG, '\n')
                    outdata = json.loads(bodydata)
                    if 'Events' in outdata:
                        event_array = outdata['Events']
                        for event in event_array:
                            if 'EventType' in event:
                                Trace.log(TraceLevel.DEBUG, '++ EventType is {}'.format(event['EventType']))
                            if 'MessageId' in event:
                                Trace.log(TraceLevel.DEBUG, '++ MessageId is {}'.format(event['MessageId']))
                            if 'EventId' in event:
                                Trace.log(TraceLevel.DEBUG, '++ EventId is {}'.format(event['EventId']))
                            if 'EventGroupId' in event:
                                Trace.log(TraceLevel.DEBUG, '++ EventGroupId is {}'.format(event['EventGroupId']))
                            if 'EventTimestamp' in event:
                                Trace.log(TraceLevel.DEBUG, '++ EventTimestamp is {}'.format(event['EventTimestamp']))
                            if 'Severity' in event:
                                Trace.log(TraceLevel.DEBUG, '++ Severity is {}'.format(event['Severity']))
                            if 'MessageSeverity' in event:
                                Trace.log(TraceLevel.DEBUG, '++ MessageSeverity is {}'.format(event['MessageSeverity']))
                            if 'Message' in event:
                                Trace.log(TraceLevel.DEBUG, '++ Message is {}'.format(event['Message']))
                            if 'MessageArgs' in event:
                                Trace.log(TraceLevel.DEBUG, '++ MessageArgs is {}'.format(event['MessageArgs']))
                            if 'Context' in outdata:
                                Trace.log(TraceLevel.DEBUG, '++ Context is {}'.format(outdata['Context']))
                            Trace.log(TraceLevel.DEBUG, '\n')

                    res = "HTTP/1.1 200 OK\r\n" \
                          "Connection: close\r\n" \
                          "\r\n"
                    connstreamout.send(res.encode())

                    try:
                        if event_count.get(str(self.fromaddr[0])):
                            event_count[str(self.fromaddr[0])] = event_count[str(self.fromaddr[0])] + 1
                        else:
                            event_count[str(self.fromaddr[0])] = 1

                        Trace.log(TraceLevel.DEBUG, '++ Event Counter for Host {} = {}'.format(str(self.fromaddr[0]), event_count[self.fromaddr[0]]))
                        Trace.log(TraceLevel.DEBUG, '\n')
                        fd = open(outputfile, "a")
                        fd.write("Time:%s Count:%s\nHost IP:%s\nEvent Details:%s\n" % (
                            datetime.now(), event_count[str(self.fromaddr[0])], str(self.fromaddr), json.dumps(outdata)))
                        fd.close()
                    except Exception as err:
                        Trace.log(TraceLevel.ERROR, traceback.print_exc())

                if p.method() == 'GET':
                    res = "HTTP/1.1 200 OK\n"
                    connstreamout.send(res.encode())
            except Exception as err:
                Trace.log(TraceLevel.ERROR, traceback.print_exc())
        finally:
            connstreamout.shutdown(socket.SHUT_RDWR)
            connstreamout.close()
