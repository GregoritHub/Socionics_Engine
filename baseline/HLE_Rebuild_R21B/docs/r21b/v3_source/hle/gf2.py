"""Exact finite algebra. Rules M01 and E01 in docs/rules.json.

Affine.compose(other) means self AFTER other. No floating-point approximation.
"""
from dataclasses import dataclass
from itertools import product

Vector = tuple[int, ...]
Matrix = tuple[Vector, ...]


def vector(x: Vector) -> Vector:
    if type(x) is not tuple or not x or any(type(v) is not int or v not in (0, 1) for v in x):
        raise ValueError("expected a nonempty tuple of GF(2) bits")
    return x


def matrix(m: Matrix, *, square: bool = False) -> Matrix:
    if type(m) is not tuple or not m:
        raise ValueError("expected a nonempty matrix of tuples")
    for row in m:
        vector(row)
    if len({len(row) for row in m}) != 1 or (square and len(m) != len(m[0])):
        raise ValueError("matrix shape mismatch")
    return m


def vectors(n: int) -> tuple[Vector, ...]:
    if type(n) is not int or n < 1:
        raise ValueError("dimension must be a positive integer")
    return tuple(product((0, 1), repeat=n))


def add(a: Vector, b: Vector) -> Vector:
    vector(a); vector(b)
    if len(a) != len(b):
        raise ValueError("vector dimensions differ")
    return tuple(x ^ y for x, y in zip(a, b))


def dot(a: Vector, b: Vector) -> int:
    vector(a); vector(b)
    if len(a) != len(b):
        raise ValueError("vector dimensions differ")
    return sum(x * y for x, y in zip(a, b)) % 2


def identity(n: int) -> Matrix:
    if type(n) is not int or n < 1:
        raise ValueError("dimension must be a positive integer")
    return tuple(tuple(int(i == j) for j in range(n)) for i in range(n))


def matvec(m: Matrix, x: Vector) -> Vector:
    matrix(m); vector(x)
    return tuple(dot(row, x) for row in m)


def matmul(a: Matrix, b: Matrix) -> Matrix:
    matrix(a); matrix(b)
    if len(a[0]) != len(b):
        raise ValueError("matrix dimensions differ")
    return tuple(tuple(dot(row, col) for col in zip(*b)) for row in a)


def rank(m: Matrix) -> int:
    matrix(m)
    rows = [list(r) for r in m]
    r = 0
    for c in range(len(m[0])):
        pivot = next((i for i in range(r, len(rows)) if rows[i][c]), None)
        if pivot is None:
            continue
        rows[r], rows[pivot] = rows[pivot], rows[r]
        for i in range(len(rows)):
            if i != r and rows[i][c]:
                rows[i] = [x ^ y for x, y in zip(rows[i], rows[r])]
        r += 1
    return r


def inverse(m: Matrix) -> Matrix:
    matrix(m, square=True)
    n = len(m)
    rows = [list(row + unit) for row, unit in zip(m, identity(n))]
    for c in range(n):
        pivot = next((i for i in range(c, n) if rows[i][c]), None)
        if pivot is None:
            raise ValueError("singular matrix over GF(2)")
        rows[c], rows[pivot] = rows[pivot], rows[c]
        for i in range(n):
            if i != c and rows[i][c]:
                rows[i] = [x ^ y for x, y in zip(rows[i], rows[c])]
    return tuple(tuple(row[n:]) for row in rows)


@dataclass(frozen=True)
class Affine:
    """An invertible affine map on one finite binary space (M01)."""

    linear: Matrix
    offset: Vector

    def __post_init__(self):
        matrix(self.linear, square=True); vector(self.offset)
        if len(self.linear) != len(self.offset):
            raise ValueError("affine dimensions differ")
        if rank(self.linear) != len(self.offset):
            raise ValueError("affine map must be invertible")

    def __call__(self, x: Vector) -> Vector:
        return add(matvec(self.linear, x), self.offset)

    def compose(self, other: "Affine") -> "Affine":
        return Affine(matmul(self.linear, other.linear),
                      add(matvec(self.linear, other.offset), self.offset))

    def inverse(self) -> "Affine":
        inv = inverse(self.linear)
        return Affine(inv, matvec(inv, self.offset))


def unit(n: int = 3) -> Affine:
    return Affine(identity(n), (0,) * n)
