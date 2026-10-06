"""Allowlisted, exact typed JSON; no executable deserialization (W08)."""
from dataclasses import fields, is_dataclass
from enum import Enum
import hashlib
import json

from . import contracts, world_records, memory_records, metabolism_records, assessment_records, socion_records, composition_records, language_records, organization_records, semantic_records, crux


def _classes(base):
    return {c.__name__: c for module in (contracts, world_records, memory_records, metabolism_records, assessment_records, socion_records, composition_records, language_records, organization_records, semantic_records, crux)
            for c in vars(module).values() if isinstance(c, type)
            and issubclass(c, base) and c.__module__ == module.__name__}


RECORDS = _classes(contracts.Record)
RECORDS.update({c.__name__: c for c in (crux.Route, crux.FormalMovement)})
ENUMS = _classes(Enum)


def encode(value):
    if isinstance(value, Enum):
        return {"enum": type(value).__name__, "value": value.value}
    if is_dataclass(value) and type(value).__name__ in RECORDS:
        return {"record": type(value).__name__, "fields": {f.name: encode(getattr(value, f.name)) for f in fields(value)}}
    if type(value) is tuple:
        return {"tuple": [encode(v) for v in value]}
    if value is None or type(value) in (str, int, bool):
        return value
    raise ValueError("unsupported checkpoint value")


def decode(value):
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is not dict:
        raise ValueError("invalid encoded value")
    if set(value) == {"enum", "value"} and value["enum"] in ENUMS:
        return ENUMS[value["enum"]](value["value"])
    if set(value) == {"tuple"} and type(value["tuple"]) is list:
        return tuple(decode(v) for v in value["tuple"])
    if set(value) == {"record", "fields"} and value["record"] in RECORDS:
        cls = RECORDS[value["record"]]
        if type(value["fields"]) is dict and set(value["fields"]) == {f.name for f in fields(cls)}:
            return cls(**{k: decode(v) for k, v in value["fields"].items()})
    raise ValueError("unknown or malformed checkpoint record")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def dumps(value):
    payload = encode(value)
    digest = hashlib.sha256(canonical(payload).encode()).hexdigest()
    return canonical({"format": "hle-typed-json-v1", "sha256": digest, "payload": payload})


def _unique(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def loads(text):
    data = json.loads(text, object_pairs_hook=_unique)
    if type(data) is not dict or set(data) != {"format", "sha256", "payload"} or data["format"] != "hle-typed-json-v1":
        raise ValueError("unknown checkpoint format")
    if hashlib.sha256(canonical(data["payload"]).encode()).hexdigest() != data["sha256"]:
        raise ValueError("checkpoint checksum mismatch")
    return decode(data["payload"])
