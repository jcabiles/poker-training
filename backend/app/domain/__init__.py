"""Pure domain core.

NO web (fastapi) or DB (sqlmodel/sqlalchemy) imports may appear anywhere under
this package — enforced by tests/test_domain_purity.py. Everything here is
plain Pydantic + stdlib so it stays independently testable and reusable across
the heuristic -> solver provider swap.
"""
