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
# label.py - A module used to encode and decode internal variables accessible to interactive
#            sessions and scripts. 
#
# ******************************************************************************************
#

from core.trace import TraceLevel, Trace

################################################################################
# Label
################################################################################
class Label:

    ldict = {'Unknown': 'Label not found in dictionary.'} 

    #
    # encode - Store a value for a label
    #
    @classmethod
    def encode(cls, label, value):
        try:
            cls.ldict[str(label)] = value 

        except Exception as e:
            Trace.log(TraceLevel.ERROR, '   -- encode: Unable to store label ({}) and vlaue {}: Exception: {}'.format(label, value, str(e)))

    #
    # decode - Return the value for a label, or the default value provided. If the variable is a list, use the index to extract the value.
    #
    @classmethod
    def decode(cls, label, default = None, index = 0):

        labelValue = default
        labelString = None
        Trace.log(TraceLevel.TRACE, '-- decode: label={} default={} index={}'.format(label, default, index))

        try:
            # Handle a string label, and a list of strings
            if isinstance(label, str): 
                labelString = label
                Trace.log(TraceLevel.TRACE, '-- decode: (string) label={} labelString={}'.format(label, labelString))
            elif isinstance(label, list): 
                labelString = str(label[index])
                Trace.log(TraceLevel.TRACE, '-- decode: (list) label={} labelString={}'.format(label, labelString))

            if labelString in cls.ldict.keys(): 
                labelValue = cls.ldict[labelString]
                Trace.log(TraceLevel.TRACE, '-- decode: label={} labelValue={}'.format(label, labelValue))

        except Exception as e:
            # Return the default value
            Trace.log(TraceLevel.DEBUG, '   -- decode: Unable to get label value ({}): Exception: {}'.format(label, str(e)))
        
        return labelValue