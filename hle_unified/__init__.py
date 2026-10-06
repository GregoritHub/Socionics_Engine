"""U2 versioned objects. Put the frozen baseline on PYTHONPATH (see README).

This namespace adds no participant policy or implicit access to world truth.
"""

from .efficiency import install_validators
install_validators()

__version__ = "u13-v1"
