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
# run_gem.py 
#
# ******************************************************************************************
#
# @command run gem <command> [data [data ...]]
#
# @synopsis Run a GEM command on supported systems
#
# @description-start
#
# Use the 'run gem' command to run any IPMI command. The 'run gem ' is
# removed from the passed in string and the entire remaining substring is sent to the
# management controller. Any data returned from the controller is displayed.
#
# Examples:
#
#     (1) (redfish) run gem ver
#
#     [] URL        : /redfish/v1/Managers/Self/Oem/IpmiCommand
#     [] Status     : 201
# 
#     [[ DATA START ]]
#     
#     
#     [[ DATA END ]]
#
#     (2) (redfish) run gem 0x30 0x2F
# 
#     [] URL        : /redfish/v1/Managers/Self/Oem/IpmiCommand
#     [] Status     : 201
#     
#     [[ DATA START ]]
#     
#     
#     [[ DATA END ]]
# 
# @description-end
#

from commands.commandHandlerBase import CommandHandlerBase
from core.jsonBuilder import JsonBuilder, JsonType
from core.redfishConfig import RedfishConfig
from core.redfishScript import RedfishScript
from core.redfishSystem import RedfishSystem
from core.trace import TraceLevel, Trace
from core import util
from core.urlAccess import UrlAccess, UrlStatus
import json
from time import sleep

################################################################################
# CommandHandler
################################################################################
class CommandHandler(CommandHandlerBase):
    """Command - run gem """
    name = 'run gem'
    cmd = ''            # GEM command
    hexcmd = []         # GEM command as ints
    result = []         # list of text results
    waitTime = 0.8        # Seconds to wait between submitting GEM command and polling for first result
    maxPayload = 511    # Max number of bytes returned by Redfish IPMI

    @classmethod
    def prepare_url(cls, redfishConfig: RedfishConfig, command: str):
        cls.cmd = command.strip().replace('run gem ', '')

        # convert ASCII text to hex data
        cls.hexcmd = []
        for char in cls.cmd:
            cls.hexcmd.append(hex(ord(char)))
        uri = '/redfish/v1/Managers/Self/Oem/IpmiCommand'
        Trace.log(TraceLevel.DEBUG, 'Run GEM Command ({})'.format(cls.cmd))
        return (uri)

    @classmethod
    def process_json(cls, redfishConfig: RedfishConfig, uri: str):
        # Submit GEM command for processing, expect error code 0x81
        completion, listResult = cls.__send_ipmi(cls.hexcmd, redfishConfig, uri)
        Trace.log(TraceLevel.DEBUG, 'Completion Code {}, Data: \n{}'.format(completion, listResult))
        if completion == 0:
            Trace.log(TraceLevel.DEBUG, 'Pause for {}s before retrieving results'.format(cls.waitTime))
            sleep(cls.waitTime) # If results are retrieved too soon, IPMI Retrieve will incorrectly respond with 0x81
            if completion is not None and listResult is not None:
                while completion == 0 and len(listResult) % cls.maxPayload == 0:
                    completion, listResult = cls.__send_ipmi(None, redfishConfig, uri)
                    Trace.log(TraceLevel.DEBUG, 'Completion Code {}, Data: \n{}'.format(completion, listResult))
                
                    # Print resulting text and append to result[]
                    strResult = util.convertHexToAscii(listResult)
                    Trace.log(TraceLevel.INFO, strResult, end='')
                    cls.result.append(strResult)
        elif completion == 0x81 or completion == 0x82:
            Trace.log(TraceLevel.INFO, 'GEM \'{}\' command successful'.format(cls.cmd))
        else:
            Trace.log(TraceLevel.INFO, 'GEM \'{}\' completion code {}'.format(cls.cmd, completion))


    @classmethod
    def display_results(cls, redfishConfig: RedfishConfig):

        # dictResult = cls.link.jsonData

        # if hasattr(dictResult, 'get'):
        #     d = dictResult.get('Response', None)
        #     if hasattr(d, 'get'):
        #         strCompletion = d.get('Completion', "None")
        #         strResult = f'Completion Code {strCompletion}'
        #         respData = d.get('Data', None)
        #         if hasattr(respData, 'index'):  # expect list of bytes in decimal
        #             for index, value in enumerate(respData):
        #                 s = hex(int(value))[2:]  # change to hex but strip out 0x
        #                 if len(s) == 1:
        #                     s = "0" + s
        #                 if index % 16 == 0:
        #                     s = "\n" + s  # Starts with newline, and line break every 16 bytes for legibility
        #             respData[index] = s
        #             strResult += ' '.join(respData)
        #         strResult += '\n'
        
        # Favor printing results as they come in, within process_json(), over waiting until the end
        # Trace.log(TraceLevel.INFO, ''.join(cls.result))
        pass

    @classmethod
    def __send_ipmi(cls, cmdData: list, redfishConfig: RedfishConfig, uri: str):
        Trace.log(TraceLevel.DEBUG, 'cmdData={}'.format(cmdData))
        JsonBuilder.startNew()
        JsonBuilder.newElement('main', JsonType.DICT)
        JsonBuilder.addElement('main', JsonType.STRING, 'netfn', "0x30")
        JsonBuilder.addElement('main', JsonType.STRING, 'command', "0x24")
        if cmdData is not None:
            JsonBuilder.addElement('main', JsonType.ARRAY, 'data', cmdData)
        Trace.log(TraceLevel.DEBUG, json.dumps(JsonBuilder.getElement('main'), indent=4))
        
        cls.link = UrlAccess.process_request(redfishConfig, UrlStatus(uri), 'POST', True, JsonBuilder.getElement('main'))

        if cls.link is not None:
            if hasattr(cls.link.jsonData, 'get'):
                Trace.log(TraceLevel.DEBUG, '[[ JSON DATA START ]]')
                Trace.log(TraceLevel.DEBUG, json.dumps(cls.link.jsonData, indent=4))
                Trace.log(TraceLevel.DEBUG, '[[ JSON DATA END ]]')

                if cls.link.urlStatus == 400:
                    # This indicates a non-zero IPMI completion code, need to parse error message to get code
                    errorCode = util.listget(cls.link.jsonData, 
                                            "error", "@Message.ExtendedInfo", 0, "MessageArgs", 0)
                    return errorCode, None
                else:
                    d = cls.link.jsonData.get('Response', {})
                    completion = int(d.get('Completion', 1), 16)
                    resultData = d.get('Data', [])

                    return completion, resultData
        return None, None
