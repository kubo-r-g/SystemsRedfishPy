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
# show_pools.py 
#
# ******************************************************************************************
#
# @command show pools
#
# @synopsis Display all allocated virtual pools and pool information
#
# @description-start
#
# 'show pools' displays details about all available pools, including
# name, serial number, class, size, and health.
#
# Example:
#
#  Name                      SerialNumber  BlockSize  Volumes  Capacity  ReadRequests     ReadBytes  ReadTime  WriteRequests    WriteBytes  WriteTime  AllocatedBytes  ConsumedBytes  Health
# ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#     A  00c0ff5112490000d9d69d5e01000000        512        1        99         34035  142753136640      9848           8456   34568012288          0   3544811831296          16384      OK
#     B  00c0ff511254000026d79d5e01000000        512        1        99         34026  142715387904     14801           8402   34550940160          0   3544811831296          16384      OK
#
# @description-end
# 

from commands.commandHandlerBase import CommandHandlerBase
from core.redfishSystem import RedfishSystem
from core.trace import TraceLevel, Trace
from core.urlAccess import UrlAccess, UrlStatus

################################################################################
# PoolInformation
################################################################################
class PoolInformation:
    """Pool Information"""

    Name = ''
    Id = ''
    Description = ''
    MaxBlockSizeBytes = ''
    AllocatedVolumes = ''
    RemainingCapacityPercent = ''
    ReadHitIORequests = ''
    ReadIOKiBytes = ''
    ReadIORequestTime = ''
    WriteHitIORequests = ''
    WriteIOKiBytes = ''
    WriteIORequestTime = ''
    AllocatedBytes = ''
    ConsumedBytes = ''
    State = ''
    Health = ''

    def init_from_url(self, redfishConfig, url):

        isPool = False
        Trace.log(TraceLevel.DEBUG, '   ++ Pool init from URL {}'.format(url))
        link = UrlAccess.process_request(redfishConfig, UrlStatus(url))
        Trace.log(TraceLevel.DEBUG, '   ++ Pool UrlAccess: link.valid={} link.jsonData={}'.format(link.valid, link.jsonData is not None))

        if (link.valid and link.jsonData is not None):

            Trace.log(TraceLevel.DEBUG, '   ++ Pool: ({}, {}, {})'.format(link.jsonData['Id'], link.jsonData['Name'], link.jsonData['@odata.type']))

            self.Name = link.jsonData['Name']
            self.Id = link.jsonData['Id']
            self.Description = link.jsonData['Description']

            if (link.jsonData['@odata.type'] == 'ERROR'):
                self.Health = 'ERROR'

            else:
                try:
                    if (self.Description == 'Pool'):
                        isPool = True
                except:
                    isPool = False

                if (isPool):
                    self.MaxBlockSizeBytes = link.jsonData['MaxBlockSizeBytes']

                    try:
                        avs = link.jsonData['AllocatedVolumes']
                        self.AllocatedVolumes = len(avs)
                    except:
                        self.AllocatedVolumes = 0

                    self.RemainingCapacityPercent = link.jsonData['RemainingCapacityPercent']

                    iostats = link.jsonData['IOStatistics']
                    self.ReadHitIORequests = iostats['ReadHitIORequests']
                    self.ReadIOKiBytes = iostats['ReadIOKiBytes']
                    self.ReadIORequestTime = iostats['ReadIORequestTime']
                    self.WriteHitIORequests = iostats['WriteHitIORequests']
                    self.WriteIOKiBytes = iostats['WriteIOKiBytes']
                    self.WriteIORequestTime = iostats['WriteIORequestTime']
    
                    capacity = link.jsonData['Capacity']
                    data = capacity['Data']
                    self.AllocatedBytes = data['AllocatedBytes']
                    self.ConsumedBytes = data['ConsumedBytes']
    
                    status = link.jsonData['Status']
                    self.State = status['State']
                    self.Health = status['Health']

        return (isPool)


################################################################################
# CommandHandler
################################################################################
class CommandHandler(CommandHandlerBase):
    """Command - show pools"""
    name = 'show pools'
    pools = []
    link = None

    @classmethod
    def prepare_url(self, redfishConfig, command):
        self.pools = []
        return (RedfishSystem.get_uri(redfishConfig, 'StoragePools'))

    @classmethod
    def process_json(self, redfishConfig, url):
        
        # GET Pools
        self.link = UrlAccess.process_request(redfishConfig, UrlStatus(url))
        
        # Retrieve a listing of all pools for this system
        # Note: Version 1.2 returns storage groups and pools, use Description to determine Pool vs DiskGroup

        if (self.link.valid and self.link.jsonData):

            total = 0 
            created = 0
            urls = []
            
            # Create a list of all the pool URLs
            for (key, value) in self.link.jsonData.items():
                if (key == 'Members@odata.count'):
                    total = value
                    Trace.log(TraceLevel.VERBOSE, '... GET total ({})'.format(total))
                elif (key == 'Members'):
                    Trace.log(TraceLevel.TRACE, '... Members value ({})'.format(value))
                    if (value != None):
                        for link in value:
                            url = link['@odata.id']
                            Trace.log(TraceLevel.VERBOSE, '... ADD url ({})'.format(url))
                            urls.append(url)
                            created += 1

            # Create Pool object based on each drive URL
            if (created > 0 and created == total):
                for i in range(len(urls)):
                    Trace.log(TraceLevel.VERBOSE, '... GET pool data ({0: >3}) of ({1: >3}) url ({2})'.format(i, len(urls), urls[i]))
                    pool = PoolInformation()
                    if (pool.init_from_url(redfishConfig, urls[i])):
                        self.pools.append(pool)
            elif (created > 0):
                Trace.log(TraceLevel.ERROR, '   ++ CommandHandler: Information mismatch: Members@odata.count ({}), Memebers {}'.format(total, created))


    @classmethod
    def display_results(self, redfishConfig):

        if (self.link.valid == False):
            self.link.print_status()

        else:
            print('')
            # Name Serial Number                    Class    Blocksize Total Size Avail  Snap Size OverCommit  Disk Groups Volumes  Low Thresh  Mid Thresh  High Thresh  Sec Fmt   Health
            # -----------------------------------------------------------------------------
            # A    00c0ff5112460000f75a925d01000000 Virtual  512       2341.6GB   2341.5GB  0B        Enabled     2           1        50.00 %     75.00 %  90.82 %      512n      OK
    
            #          0                                 1          2        3         4             5             6         7              8             9         10              11             12      13
            print(' Name                      SerialNumber  BlockSize  Volumes  Capacity  ReadRequests     ReadBytes  ReadTime  WriteRequests    WriteBytes  WriteTime  AllocatedBytes  ConsumedBytes  Health')
            print(' -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------')
    
            if (self.pools != None):
                for i in range(len(self.pools)):
                    print(' {0: >4}  {1: >32}  {2: >9}  {3: >7}  {4: >8}  {5: >12}  {6: >12}  {7: >8}  {8: >13}  {9: >12}  {10: >9}  {11: >14}  {12: >13}  {13: >6}'.format(
                        self.pools[i].Name,
                        self.pools[i].Id,
                        self.pools[i].MaxBlockSizeBytes,
                        self.pools[i].AllocatedVolumes,
                        self.pools[i].RemainingCapacityPercent,
                        self.pools[i].ReadHitIORequests,
                        self.pools[i].ReadIOKiBytes,
                        self.pools[i].ReadIORequestTime,
                        self.pools[i].WriteHitIORequests,
                        self.pools[i].WriteIOKiBytes,
                        self.pools[i].WriteIORequestTime,
                        self.pools[i].AllocatedBytes,
                        self.pools[i].ConsumedBytes,
                        self.pools[i].Health))
