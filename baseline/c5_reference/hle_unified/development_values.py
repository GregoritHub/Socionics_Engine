"""Lossless tuple fields over the common substrate's scalar attributes."""
from .material import attrs as scalar_attrs


def pack(values):
    result = {}
    def put(key,value):
        if type(value) is tuple:
            result[key+".__length"] = len(value)
            for i,child in enumerate(value):
                put(key+"."+str(i),child)
        else:
            result[key] = value
    for key,value in values.items():
        put(key,value)
    return result


def attrs(value):
    result = scalar_attrs(value)
    lengths = sorted((k for k in result if k.endswith(".__length")), key=len, reverse=True)
    for key in lengths:
        prefix = key[:-9]
        size = result.pop(key)
        result[prefix] = tuple(result.pop(prefix+"."+str(i)) for i in range(size))
    return result
