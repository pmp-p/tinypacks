#!/usr/bin/env python3
#
#  TinyPacks - Copyright (c) 2012 Francisco Castro <http://fran.cc>
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#  THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.

try:
    from struct import pack, unpack
    const = int
except:
    from ustruct import pack, unpack


TP_NONE = const(0x00)
TP_BOOLEAN = const(0x20)
TP_INTEGER = const(0x40)
TP_REAL = const(0x60)
TP_STRING = const(0x80)
TP_BYTES = const(0xA0)
TP_LIST = const(0xC0)
TP_MAP = const(0xE0)

TP_SMALL_SIZE_MASK = const(0x1F)
TP_SMALL_SIZE_MAX = const(0x1E)
TP_EXTENDED_SIZE_16 = const(0x1F)
TP_EXTENDED_SIZE_32 = const(0xFFFF)

TP_TYPE_MASK = const(0b11100000)
TP_FAMILY_MASK = const(0b11000000)

TP_NUMBER = const(0b01000000)
TP_BLOCK = const(0b10000000)
TP_CONTAINER = const(0b11000000)


def bit_len(n):
    s = bin(n)  # binary representation:  bin(-37) --> '-0b100101'
    s = s.lstrip("-0b")  # remove leading zeros and minus sign
    return len(s)  # len('100101') --> 6


def dumpb(obj, use_double=False):
    if obj is None:
        return bytes([TP_NONE])

    if isinstance(obj, bool):
        if obj:
            return bytes( [0x21,0x01] )
        return bytes( [TP_BOOLEAN] )

    if isinstance(obj, int):
        bit_length = bit_len(obj)
        if bit_length == 0:
            return bytes([TP_INTEGER])

        if bit_length <= 7:
            return pack(">Bb", TP_INTEGER | 1, obj)

        if bit_length <= 15:
            return pack(">Bh", TP_INTEGER | 2, obj)

        if bit_length <= 31:
            return pack(">Bl", TP_INTEGER | 4, obj)

        if bit_length <= 63:
            return pack(">Bq", TP_INTEGER | 8, obj)

        raise ValueError("Integer number too big")

    if isinstance(obj, float):
        if obj == 0:
            return bytes([TP_REAL])
        if use_double:
            return pack(">Bd", TP_REAL | 8, obj)

        return pack(">Bf", TP_REAL | 4, obj)

    if isinstance(obj, str):
        obj = bytes(obj, "utf_8")
        blen = len(obj)

        if blen <= TP_SMALL_SIZE_MAX:
            return pack(">B%is" % blen, TP_STRING | blen, obj)

        if blen < 0xFFFF:
            return pack(">BH%is" % blen, TP_STRING | TP_EXTENDED_SIZE_16, blen, obj)

        if blen < 0xFFFFFFFF:
            return pack(">BHL%is" % blen, TP_STRING | TP_EXTENDED_SIZE_16, TP_EXTENDED_SIZE_32, blen, obj)

        raise ValueError("String too long")

    if isinstance(obj, (bytes,bytearray) ):
        blen = len(obj)
        if blen <= TP_SMALL_SIZE_MAX:
            return pack(">B%is" % blen, TP_BYTES | blen, obj)

        if blen < 0xFFFF:
            return pack(">BH%is" % blen, TP_BYTES | TP_EXTENDED_SIZE_16, blen, obj)

        if blen < 0xFFFFFFFF:
            return pack(">BHL%is" % blen, TP_BYTES | TP_EXTENDED_SIZE_16, TP_EXTENDED_SIZE_32, blen, obj)

        raise ValueError("Bytearray too long")

    if isinstance(obj, (list, tuple)):
        content = b"".join([pack(value) for value in obj])
        blen = len(content)

        if blen <= TP_SMALL_SIZE_MAX:
            return pack(">B%is" % blen, TP_LIST | blen, content)

        if blen < 0xFFFF:
            return pack(">BH%is" % blen, TP_LIST | TP_EXTENDED_SIZE_16, blen, content)

        if blen < 0xFFFFFFFF:
            return pack(">BHL%is" % blen, TP_LIST | TP_EXTENDED_SIZE_16, TP_EXTENDED_SIZE_32, blen, content)

        raise ValueError("List too long")

    if isinstance(obj, dict):
        elements = []
        for item in list(obj.items()):
            elements.append(dumpb(item[0]))
            elements.append(dumpb(item[1]))
        content = b"".join(elements)
        blen = len(content)

        if blen <= TP_SMALL_SIZE_MAX:
            return pack(">B%is" % blen, TP_MAP | blen, content)

        if blen < 0xFFFF:
            return pack(">BH%is" % blen, TP_MAP | TP_EXTENDED_SIZE_16, blen, content)
        if blen < 0xFFFFFFFF:
            return pack(">BHL%is" % blen, TP_MAP | TP_EXTENDED_SIZE_16, TP_EXTENDED_SIZE_32, blen, content)

        raise ValueError("Dict too long")

    raise ValueError("Unknown type")

import sys
def _loadb(ba):
    if len(ba) == 0:
        raise ValueError("Cannot unpack an empty pack")

    ct = ba[0] & TP_TYPE_MASK
    content_length = ba[0] & TP_SMALL_SIZE_MASK
    element_length = content_length + 1

    if content_length != TP_EXTENDED_SIZE_16:
        content_raw = ba[1:element_length]
    else:
        content_length = unpack(">BH", ba[0:3])[1]
        element_length = content_length + 3
        if content_length != TP_EXTENDED_SIZE_32:
            content_raw = ba[3:element_length]
        else:
            content_length = unpack(">BHL", bytes)[2]
            element_length = content_length + 7
            content_raw = ba[7:element_length]

    if ct == TP_NONE:
        obj = None

    elif ct == TP_BOOLEAN:
        obj = False
        if content_length:
            if content_raw[0]:
                obj=True
            else:
                raise ValueError("Invalid True value")

    elif ct == TP_INTEGER:
        if content_length == 0:
            obj = 0
        elif content_length == 1:
            obj = unpack(">b", content_raw)[0]
        elif content_length == 2:
            obj = unpack(">h", content_raw)[0]
        elif content_length == 4:
            obj = unpack(">l", content_raw)[0]
        elif content_length == 8:
            obj = unpack(">q", content_raw)[0]
        else:
            raise ValueError("Integer number too big")

    elif ct == TP_REAL:
        if content_length == 0:
            obj = 0.0
        elif content_length == 4:
            obj = unpack(">f", content_raw)[0]
        elif content_length == 8:
            obj = unpack(">d", content_raw)[0]
        else:
            raise ValueError("Real number too big")

    elif ct == TP_STRING:
        obj = content_raw.decode("utf8")

    elif ct == TP_BYTES:
        obj = content_raw

    elif ct == TP_LIST:
        obj = []
        while len(content_raw):
            item, content_raw = unpack(content_raw)
            obj.append(item)

    elif ct == TP_MAP:
        obj = {}
        while len(content_raw):
            key, content_raw = _loadb(content_raw)
            if len(content_raw):
                value, content_raw = _loadb(content_raw)
                obj[key] = value
            else:
                raise ValueError("Dict key/value invalid")

    return (obj, ba[element_length:])

def loadb(ba):return _loadb(ba)[0]








if __name__ == '__main__':
    data = {"text": "Hello world!",b"bin": b"ary", "status": True, "not_status":False, 'avg': 50.0/100, "count": 123, "countdown" : -123}
    print("Data: " +  repr(data))
    packed_data=  dumpb(data)
    print("Packed: " + repr( packed_data ))
    print("Unpacked: " + repr( loadb(packed_data) ) )
