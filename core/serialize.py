from __future__ import absolute_import

import math

from core.compatibility import iteritems


_CACHE = {bin: {}, int: {}}

_NONETYPE = type(None)

_TYPES = (None, _NONETYPE, bool, str, int, float, list, tuple, dict, complex, set)

_TYPES_INDEXED = {v: i for i, v in enumerate(_TYPES)}

DUPLICATES = {long: int}

TYPE_LEN = 4


def str_to_ints(s):
    return [ord(i) for i in s]


def ints_to_str(s):
    return ''.join(chr(i) for i in s)


def int_to_bin(i, padding=0, cache=True, signed=False):
    
    dict_key = (i, padding)
    try:
        return _CACHE[bin][dict_key][signed]
    except KeyError:
        result = str(bin(i))
        if i < 0:
            result_signed = '1' + result[3:].zfill(padding-1)
            result_unsigned = result[3:].zfill(padding)
        else:
            result_signed = '0' + result[2:].zfill(padding-1)
            result_unsigned = result[2:].zfill(padding)
        if cache:
            _CACHE[bin][dict_key] = (result_unsigned, result_signed)
    return result_signed if signed else result_unsigned


def bin_to_int(b, signed=False):
    multiplier = -1 if signed and b[0] == '1' else 1
    if signed:
        b = b[1:]
    try:
        return _CACHE[int][b] * multiplier
    except KeyError:
        _CACHE[int][b] = int(b, 2)
    return _CACHE[int][b] * multiplier


def bin_len(b):
    try:
        return _CACHE['bin_len'][b]
    except KeyError:
        if isinstance(b, str):
             _CACHE['bin_len'][b] = len(b)
        else:
             _CACHE['bin_len'][b] = len(int_to_bin(b))
    return _CACHE['bin_len'][b]


def dumps(x, _sign=True):
    item_type = type(x)
    try:
        item_type = DUPLICATES[item_type]
    except KeyError:
        pass

    try:
        type_id = _TYPES_INDEXED[item_type]
    except KeyError:
        raise ValueError('invalid type: {}'.format(item_type))

    current = int_to_bin(type_id, TYPE_LEN)

    if item_type == _NONETYPE:
        pass
    
    elif item_type == bool:
        item_binary = '1' if x else '0'
        current += item_binary

    elif item_type in (tuple, list, set):
        length_bytes = int_to_bin(len(x))
        current += '0'*(len(length_bytes)-1) + '1' + length_bytes
        for item in x:
            current += dumps(item)

    elif item_type == int:
        item_binary = int_to_bin(x, signed=_sign)
        length_bytes = int_to_bin(len(item_binary))
        current += '0'*(len(length_bytes)-1) + '1' + length_bytes
        current += item_binary

    elif item_type == float:
        if math.isnan(x):
            current += '10'
        elif math.isinf(x):
            current += '11'
        else:
            sign = ('1' if x < 0 else '0')
            parts = str(x).split('.')
            if parts[1] == '0':
                current += '00' + sign + dumps(int(parts[0]), _sign=False)
            else:
                current += '01' + sign + dumps(int(parts[0]), _sign=False) + dumps(int(parts[1]), _sign=False)

    elif item_type == str:
        length_bytes = int_to_bin(len(x))
        current += '0'*(len(length_bytes)-1) + '1' + length_bytes
        for integer in str_to_ints(x):
            current += dumps(integer, _sign=False)

    elif item_type == complex:
        real = dumps(int(x.real))
        imaginary = dumps(int(x.imag))
        current += real + imaginary

    elif item_type == dict:
        length_bytes = int_to_bin(len(x))
        current += '0'*(len(length_bytes)-1) + '1' + length_bytes
        for k, v in iteritems(x):
            current += dumps(k) + dumps(v)
    
    return current


def _loads(x, offset=0, _sign=True):
    _offset = offset
    offset += TYPE_LEN
    item_type = _TYPES[bin_to_int(x[_offset:offset])]
    
    if item_type == _NONETYPE:
        return (None, offset)
    
    elif item_type == bool:
        return (True if x[offset] == '1' else False, offset+1)

    elif item_type == int:
        i = 0
        while x[offset+i] == '0':
            i += 1
        offset += i + 1
        
        int_length = bin_to_int(x[offset:offset+i+1])
        offset += i+1
        int_value = bin_to_int(x[offset:offset+int_length], signed=_sign)
        return (int_value, offset+int_length)

    elif item_type == float:
        float_type = x[offset]
        offset += 1
        if float_type == '0':
            point_zero = x[offset] == '0'
            offset += 1
            multiplier = 1 if x[offset] == '0' else -1
            offset += 1
            if point_zero:
                float1, offset = _loads(x, offset=offset, _sign=False)
                result = float(float1) * multiplier
            else:
                float1, offset = _loads(x, offset=offset, _sign=False)
                float2, offset = _loads(x, offset=offset, _sign=False)
                result = float('{}.{}'.format(float1, float2)) * multiplier
        elif float_type == '1':
            if x[offset] == '0':
                result = float('nan')
            elif x[offset] == '1':
                result = float('inf')
        return (result, offset)

    elif item_type == str:
        i = 0
        while x[offset+i] == '0':
            i += 1
        offset += i+1
        
        str_length = bin_to_int(x[offset:offset+i+1])
        offset += i+1
        result = []
        for _ in range(str_length):
            character, offset = _loads(x, offset=offset, _sign=False)
            result.append(chr(character))
        return (''.join(result), offset)
            

    elif item_type == complex:
        real, offset = _loads(x, offset=offset)
        imaginary, offset = _loads(x, offset=offset)
        return real + imaginary * 1j, offset + 1

    elif item_type in (tuple, list, set):
        i = 0
        while x[offset+i] == '0':
            i += 1
        offset += i + 1
        
        list_length = bin_to_int(x[offset:offset+i+1])
        offset += i+1
        
        data = []
        for _ in range(list_length):
            value, offset = _loads(x, offset=offset)
            data.append(value)

        if item_type == tuple:
            data = tuple(data)
        elif item_type == set:
            data = set(data)
            
        return (data, offset)

    elif item_type == dict:
        i = 0
        while x[offset+i] == '0':
            i += 1
        offset += i+1
        
        dict_length = bin_to_int(x[offset:offset+i+1])
        offset += i+1
        
        result = {}
        for _ in range(dict_length):
            k, offset = _loads(x, offset=offset)
            v, offset = _loads(x, offset=offset)
            result[k] = v
        return (result, offset)
        

def loads(x):
    return _loads(x)[0]


if __name__ == '__main__':
    
    test= []
    test.append('this is a string')
    test.append(10025)
    test.append(-0.25)
    test.append(5.0+72j)
    test.append(range(5))
    test.append(None)
    test.append(False)
    test.append({'k': 'v'})
    test.append([None, True, False])
    test.append((46.2, 'abcdefg', (set([52, 7, 'item']), {5: True, '65': range(4)})))

    for i in test:
        print 'Testing {}'.format(i)
        if loads(dumps(i)) != i:
            print 'Error'
        else:
            print 'Passed'
    
