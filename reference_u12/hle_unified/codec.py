"""Allowlisted canonical U2 JSON, isolated from the legacy wire registry."""
from dataclasses import fields, is_dataclass
from enum import Enum
import hashlib
import json

from hle.contracts import Record, Moment, TimeScope, ClaimStatus, EvidenceStatus
from . import records

RECORDS = {cls.__name__: cls for cls in vars(records).values()
           if isinstance(cls, type) and issubclass(cls, Record) and cls.__module__ == records.__name__}
RECORDS.update({cls.__name__: cls for cls in (Moment, TimeScope)})
ENUMS = {cls.__name__: cls for cls in vars(records).values()
         if isinstance(cls, type) and issubclass(cls, Enum) and cls.__module__ == records.__name__}
ENUMS.update({cls.__name__: cls for cls in (ClaimStatus, EvidenceStatus)})


def encode(value):
    if type(value) in ENUMS.values():
        return {"enum": type(value).__name__, "value": value.value}
    if is_dataclass(value) and type(value) in RECORDS.values():
        return {"record": type(value).__name__, "fields": {f.name: encode(getattr(value, f.name)) for f in fields(value)}}
    if type(value) is tuple:
        return {"tuple": [encode(x) for x in value]}
    if value is None or type(value) in (str, int, bool):
        return value
    raise ValueError("unsupported U2 wire value")


def decode(value):
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is not dict:
        raise ValueError("invalid U2 wire value")
    if set(value) == {"enum", "value"} and type(value["enum"]) is str and value["enum"] in ENUMS:
        cls = ENUMS[value["enum"]]
        if type(value["value"]) is not str:
            raise ValueError("invalid enum value type")
        return cls(value["value"])
    if set(value) == {"tuple"} and type(value["tuple"]) is list:
        return tuple(decode(v) for v in value["tuple"])
    if set(value) == {"record", "fields"} and type(value["record"]) is str and value["record"] in RECORDS:
        cls = RECORDS[value["record"]]
        data = value["fields"]
        if type(data) is dict and set(data) == {f.name for f in fields(cls)}:
            return cls(**{k: decode(v) for k, v in data.items()})
    raise ValueError("unknown or malformed U2 record")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def dumps(value):
    payload = encode(value)
    return canonical({"format": "hle-unified-typed-json-v1", "payload": payload,
                      "sha256": hashlib.sha256(canonical(payload).encode()).hexdigest()})


def _unique(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def loads(text):
    data = json.loads(text, object_pairs_hook=_unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON number")))
    if type(data) is not dict or set(data) != {"format", "payload", "sha256"} or data["format"] != "hle-unified-typed-json-v1":
        raise ValueError("unsupported U2 format")
    if hashlib.sha256(canonical(data["payload"]).encode()).hexdigest() != data["sha256"]:
        raise ValueError("U2 checkpoint checksum mismatch")
    return decode(data["payload"])
