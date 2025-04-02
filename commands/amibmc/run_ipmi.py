#
# Do NOT modify or remove this copyright and license
#
# Copyright (c) 2024 Seagate Technology LLC and/or its Affiliates, All Rights Reserved
#
# This software is subject to the terms of the MIT License. If a copy of the license was
# not distributed with this file, you can obtain one at https://opensource.org/licenses/MIT.
#
# ******************************************************************************************
#
# run_ipmi.py 
#
# ******************************************************************************************
#
# @command run ipmi <NetFn> <command> [data [data ...]]
#
# @synopsis Run an IPMI command on supported systems
#
# @description-start
#
# Use the 'run ipmi' command to run any IPMI command. The 'run ipmi ' is
# removed from the passed in string and the entire remaining substring is sent to the
# management controller. Any JSON data returned from the controller is displayed.
#
# Examples:
#
#     (1) (redfish) run ipmi 0x30 0xA
#
#     [] URL        : /redfish/v1/Managers/Self/Oem/IpmiCommand
#     [] Status     : 201
# 
#     [[ JSON DATA START ]]
#     {
#         "Request": {
#             "NetFn": "0x30",
#             "Command": "0xA",
#         }
#         "Response": {
#             "Completion": 0,
#             "Data": [0]
#         }
#     }
#     [[ JSON DATA END ]]
#
#     (2) (redfish) run ipmi 0x30 0x2F
# 
#     [] URL        : /redfish/v1/Managers/Self/Oem/IpmiCommand
#     [] Status     : 201
#     
#     [[ JSON DATA START ]]
#     {
#         "Request": {
#             "NetFn": "0x30",
#             "Command": "0xA",
#         }
#         "Response": {
#             "Completion": 0,
#             "Data": [0]
#         }
#     }
#     [[ JSON DATA END ]]
# 
# @description-end
#

from commands.commandHandlerBase import CommandHandlerBase
from core.jsonBuilder import JsonBuilder, JsonType
from core.redfishConfig import RedfishConfig
from core.redfishScript import RedfishScript
from core.redfishSystem import RedfishSystem
from core.trace import TraceLevel, Trace
from core.urlAccess import UrlAccess, UrlStatus
from core import util
import json

################################################################################
# CommandHandler
################################################################################
class CommandHandler(CommandHandlerBase):
    """Command - run ipmi """
    name = 'run ipmi'
    netfn = ''
    cmd = ''
    data = []

    @classmethod
    def prepare_url(cls, redfishConfig: RedfishConfig, command: str):
        cls.data = command.strip().replace('run ipmi ', '').split(' ')
        cls.netfn = cls.data.pop(0)
        cls.cmd = cls.data.pop(0)
        uri = '/redfish/v1/Managers/Self/Oem/IpmiCommand'
        Trace.log(TraceLevel.DEBUG, 'Run IPMI Command ({} {}) to ({})'.format(cls.netfn, cls.cmd, uri))
        return (uri)

    @classmethod
    def process_json(cls, redfishConfig: RedfishConfig, uri: str):

        # Example: http post /redfish/v1/Systems/00C0FF437ED5/Actions/ComputerSystem.ExecuteMCCommand { "Command": "show volumes" }

        JsonBuilder.startNew()
        JsonBuilder.newElement('main', JsonType.DICT)
        JsonBuilder.addElement('main', JsonType.STRING, 'netfn', cls.netfn)
        JsonBuilder.addElement('main', JsonType.STRING, 'command', cls.cmd)
        if len(cls.data) > 0:
            JsonBuilder.addElement('main', JsonType.ARRAY, 'data', cls.netfn)

        cls.link = UrlAccess.process_request(redfishConfig, UrlStatus(uri), 'POST', True, JsonBuilder.getElement('main'))

        if cls.link is not None:
            cls.link.print_status()

        if (cls.link.jsonData != None):
            Trace.log(TraceLevel.DEBUG, '[[ JSON DATA START ]]')
            Trace.log(TraceLevel.DEBUG, json.dumps(cls.link.jsonData, indent=4))
            Trace.log(TraceLevel.DEBUG, '[[ JSON DATA END ]]')

    @classmethod
    def display_results(cls, redfishConfig: RedfishConfig):
        dictResult = cls.link.jsonData
        ''' Example response data from Bonneville
        {
            "Request": {
                "netfn": 48
            },
            "Completion": "0",
                "Data": [
                ]
            }
        }'''
        strResult = 'No Response'
        if hasattr(dictResult, 'get'):
            if cls.link.urlStatus == 400:
                # This indicates a non-zero IPMI completion code, need to parse error message to get code
                errorCode = util.listget(dictResult, 
                                        "error", "@Message.ExtendedInfo", 0, "MessageArgs", 0)
                dictResult['Response'] = {'Completion': errorCode}
            d = dictResult.get('Response', None)
            if hasattr(d, 'get'):
                strCompletion = d.get('Completion', "None")
                strResult = 'Completion Code {}'.format(strCompletion)
                respData = d.get('Data', None)
                if hasattr(respData, 'index'):  # expect list of bytes in decimal
                    strResult += '\nData: '
                    s = ''
                    for index, value in enumerate(respData):
                        s = hex(int(value))[2:]  # change to hex but strip out '0x'
                        if len(s) == 1:
                            s = '0' + s
                        if index % 16 == 0:
                            s = '\n' + s  # Starts with newline, and line break every 16 bytes for legibility
                    respData[index] = s
                    strResult += ' '.join(respData)

        Trace.log(TraceLevel.INFO, strResult)
