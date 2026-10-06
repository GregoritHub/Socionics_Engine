"""The Model A cube routes processing; Fold edges realize perspective changes.

The four type coordinates, three position coordinates, two perspective bits,
and the fixed function dimensionality have separate operational fields.
Numerical prices and polarity support seats carry the legacy R4 hypothesis.
"""
from hle.model_a import (element_at, position_of, position, fields, jungian,
                         shortest_paths)
from hle.crux import Perspective, Polarity, CODE
from hle.concept_structure import bridge


def route(tim, active, elements, origin, destination, polarity):
    origin, destination, polarity = Perspective(origin), Perspective(destination), Polarity(polarity)
    if not elements:
        raise ValueError("at least one realized Fold edge required")
    rows = []
    current = origin
    price = lambda e: 5 - fields(position_of(tim, e))["dimensionality"]
    support_seats = (5, 7) if polarity == Polarity.ACCUMULATION else (6, 8)
    for element in elements:
        edge = bridge(tim, element, current)
        candidates = []
        for seat in support_seats:
            support = element_at(tim, seat)
            for first in shortest_paths(tim, active, support):
                for second in shortest_paths(tim, support, element):
                    path = first + second[1:]
                    charges = tuple(price(e) for e in path[1:])
                    candidates.append((sum(charges), len(path), path, seat, len(first)-1, charges))
        _, _, path, support, support_at, charges = min(candidates)
        row = {"element": element, "origin": current.value,
            "destination": edge.route.destination.value, "name": edge.route.name,
            "polarity": polarity.value, "seat": edge.seat,
            "dimensionality": fields(edge.seat)["dimensionality"],
            "support_seat": support, "support_at": support_at,
            "content_units": price(element), "path": path, "charges": charges,
            "position": position(edge.seat), "type_coordinates": jungian(tim),
            "origin_bits": CODE[current], "destination_bits": CODE[edge.route.destination]}
        rows.append(row)
        current, active = edge.route.destination, element
    if current != destination:
        raise ValueError("Fold composition does not realize the requested destination")
    return tuple(rows)


def flatten_route(rows):
    data = {}
    for i, row in enumerate(rows):
        for key, value in row.items():
            if type(value) is tuple:
                data.update({f"route.{i}.{key}.{j}": v for j, v in enumerate(value)})
            else:
                data[f"route.{i}.{key}"] = value
    data["route_count"] = len(rows)
    return data


def progress(data):
    """Last fully paid hop and edge; partial/cancelled work remains inspectable."""
    remaining = max(0, data["completed"] - data["recall_units"])
    active, perspective, edges = data["active_start"], data["origin"], 0
    for i in range(data["route_count"]):
        prefix = f"route.{i}."
        j = 0
        while prefix + "charges." + str(j) in data:
            cost = data[prefix + "charges." + str(j)]
            if remaining < cost:
                return active, perspective, edges
            remaining -= cost
            active = data[prefix + "path." + str(j+1)]
            j += 1
        cost = data[prefix + "content_units"]
        if remaining < cost:
            return active, perspective, edges
        remaining -= cost
        active, perspective, edges = data[prefix + "element"], data[prefix + "destination"], edges+1
    return active, perspective, edges
