# Makes `neev_pipeline` importable when the suite is run straight from a repo
# checkout, before `pip install -e src/agents` has been done. Once the agents venv
# exists (Python 3.11), the editable install puts the package on sys.path and
# this becomes a harmless no-op. Kept so `python3 -m tests.test_offline` works
# on a clean clone with no environment set up at all.

import os
import sys

_AGENTS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "agents"
)
if _AGENTS not in sys.path:
    sys.path.insert(0, _AGENTS)
