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
# redfish_metadata.py 
#
# ******************************************************************************************
#
# @command redfish metadata
#
# @synopsis GET and display the metadata reported by the Redfish Service
#
# @description-start
#
# This command will display the XML metadata returned from /redfish/v1/$metadata.
#
# Example:
# 
# (redfish) redfish metadata
# Redfish Metadata
# ---------------------------------------------------------------------------------------------------------
# <?xml version="1.0" ?>
# <edmx:Edmx Version="4.0" xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx">
#     <edmx:Reference Uri="http://redfish.dmtf.org/schemas/v1/ServiceRoot_v1.xml">
#         <edmx:Include Namespace="ServiceRoot"/>
#         <edmx:Include Namespace="ServiceRoot.v1_2_0"/>
#     </edmx:Reference>
#     (... ommitted to reduce output ...) 
#     <edmx:DataServices>
#         <Schema Namespace="Service" xmlns="http://docs.oasis-open.org/odata/ns/edm">
#             <EntityContainer Extends="ServiceRoot.v1_2_0.ServiceContainer" Name="Service"/>
#         </Schema>
#     </edmx:DataServices>
# </edmx:Edmx>
# 
# @description-end
#

import xml.dom.minidom
from commands.commandHandlerBase import CommandHandlerBase
from core.redfishSystem import RedfishSystem
from core.trace import TraceLevel, Trace
from core.urlAccess import UrlAccess, UrlStatus


################################################################################
# CommandHandler
################################################################################
class CommandHandler(CommandHandlerBase):
    """Command - redfish metadata """
    name = 'redfish metadata'
    link = None

    def prepare_url(self, redfishConfig, command):
        RedfishSystem.initialize_service_root_uris(redfishConfig)
        return (RedfishSystem.get_uri(redfishConfig, 'metadata'))

    @classmethod
    def process_json(self, redfishConfig, url):

        self.link = UrlAccess.process_request(redfishConfig, UrlStatus(url), 'GET', False)

        Trace.log(TraceLevel.TRACE, '[[ urlData DATA ]]')
        Trace.log(TraceLevel.TRACE, '{}'.format(self.link.urlData))
        Trace.log(TraceLevel.TRACE, '[[ urlData DATA END ]]')

    @classmethod
    def display_results(self, redfishConfig):

        print('Redfish Metadata')
        print('---------------------------------------------------------------------------------------------------------')
        if (self.link.valid):
            Trace.log(TraceLevel.INFO, '{}'.format(self.link.urlData))
        else:
            Trace.log(TraceLevel.ERROR, '   ++ CommandHandler: redfish metadata // ERROR receiving data from ({}): Error {}: {}'.format(self.link.url, self.link.urlStatus, self.link.urlReason))
