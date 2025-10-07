# app.api.v1 package - exports submodules so imports like
# "from app.api.v1 import health, auth, transactions, categories, receipts" work.

# always export health
from . import health

# optional: import other routers if present; if they raise at import time,
# swallow the exception so package import still succeeds.
try:
    from . import auth
except Exception:
    pass

try:
    from . import transactions
except Exception:
    pass

try:
    from . import categories
except Exception:
    pass

try:
    from . import receipts
except Exception:
    pass
