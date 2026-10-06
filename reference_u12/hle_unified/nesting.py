"""Trusted projections over exact history. No function here delivers actor knowledge.

Membership is a DAG; ordinary account references may point back to its root.
Projection scopes deliberately omit tool condition and procedure permissions.
"""
from .records import Composition, Material, Role, Lifecycle
from .material import attrs, available


def walk(world, root, limit, *, overrides=None, material=False):
    overrides = overrides or {}
    groups, leaves, resources, dependencies, visiting = {}, {}, {}, {}, set()
    stack = [(root, False)]
    visited, examined = set(), set()
    while stack:
        identity, returning = stack.pop()
        if returning:
            visiting.remove(identity)
            continue
        if identity in visiting:
            raise ValueError("membership cycle")
        if identity in visited:
            continue
        if identity not in examined and len(examined) >= limit:
            raise ValueError("membership traversal budget exhausted")
        examined.add(identity)
        visited.add(identity)
        value = overrides.get(identity) or world.head(identity)
        # Only native U11 groups are executable membership nodes. Ordinary
        # references, including representations of groups, are terminal members.
        part = value.facet(Composition) if identity.namespace == "u11.group" else None
        if part is None:
            leaves[identity] = value
            if value.facet(Material) is not None:
                resources[identity] = value
            continue
        if value.lifecycle != Lifecycle.ACTIVE: raise ValueError("inactive composite")
        groups[identity] = value
        dependencies[identity] = value.ref
        visiting.add(identity)
        stack.append((identity, True))
        for resource in part.resources:
            if resource not in examined and len(examined) >= limit:
                raise ValueError("resource traversal budget exhausted")
            examined.add(resource)
            item = world.head(resource)
            if item.facet(Material) is None or item.lifecycle != Lifecycle.ACTIVE:
                raise ValueError("active material resource required")
            resources[resource] = item
        stack.extend((child, False) for child in reversed(part.members))
    if material:
        if any(v.lifecycle != Lifecycle.ACTIVE for v in resources.values()):
            raise ValueError("inactive material resource")
        dependencies.update((i, v.ref) for i, v in resources.items())
    return dict(groups=groups, leaves=leaves, resources=resources,
                dependencies=tuple(sorted(dependencies.values())), visits=len(examined))


def project(world, root, scope, limit, *, use_cache=True):
    if scope not in ("inventory", "membership"):
        raise ValueError("unsupported projection scope")
    key = ("u11.projection", root, scope)
    if use_cache and key in world.cache.values:
        result = world.cache.values[key]
        if result["visits"] > limit:
            raise ValueError("projection traversal budget exhausted")
        return dict(result)
    graph = walk(world, root, limit, material=scope == "inventory")
    # Named membership counts do not depend on a person's private mental state.
    members = tuple(sorted(graph["leaves"]))
    if scope == "membership":
        public = (("members", members), ("member_count", len(members)),
                  ("group_count", len(graph["groups"])))
    else:
        quantities, stocks = {}, {}
        for item in graph["resources"].values():
            m = item.facet(Material)
            k = (m.owner, m.unit)
            quantities[k] = quantities.get(k, 0) + m.quantity
            if m.condition == "stock":
                k = (m.owner, m.unit, attrs(item)["purpose"])
                stocks[k] = stocks.get(k, 0) + available(item)
        public = (("resource_count", len(graph["resources"])),
                  ("quantities_by_owner_unit", tuple((*k, n) for k, n in sorted(quantities.items()))),
                  ("stock_by_owner_unit_purpose", tuple((*k, n) for k, n in sorted(stocks.items()))))
    result = dict(root=world.head(root).ref, scope=scope, public=public,
                  dependencies=graph["dependencies"], visits=graph["visits"])
    if use_cache:
        world.cache.put(key, result, (r.identity for r in graph["dependencies"]))
    return dict(result)


def observed_ref(view, identity):
    """Newest received exact reference; never consult current world heads."""
    refs = {p.subject for p in view.lookup(subject=identity) if p.subject.identity == identity}
    if not refs:
        raise ValueError("required detail has not been received")
    return max(refs, key=lambda r:r.revision)


def observed_material(view, identity, *, stock=False):
    ref = observed_ref(view, identity)
    values = {p.address.key:p.value for p in view.resolve(ref)}
    required = {"owner", "custodian", "quantity", "condition"}
    required |= {"consumed", "purpose"} if stock else {"wear", "max_wear"}
    if not required <= values.keys():
        raise ValueError("summary lacks the material distinctions needed for this action")
    return ref, tuple(p.address for p in view.resolve(ref))


def syntax_size(value):
    return 1 + sum(syntax_size(x) for x in value) if type(value) is tuple else 1
