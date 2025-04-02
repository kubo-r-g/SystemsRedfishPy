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
# util.py - Common helper routines
#
# ******************************************************************************************
#

def convertHexToAscii(hex: list[int]) -> str:
    result = ""
    for i in hex:
        if i == 0xD: # Carriage return: ignore
            continue
        elif i == 0xA: # New Line
            result += "\n"
        else:
            result += i.to_bytes(1,'big').decode('latin-1')

    return result

def listget(d: dict, *keys):
    '''Retrieves a value from nested dicts using multiple keys
    :returns: dict value, or None if key error
    '''
    for key in keys:
        if hasattr(d, 'get'):
            d = d.get(key, None)
        elif hasattr(d, 'index'):
            try:
                d = d[int(key)]
            except ValueError:
                raise ValueError(f'Key {key} cannot be used as a list index')
                
    return d