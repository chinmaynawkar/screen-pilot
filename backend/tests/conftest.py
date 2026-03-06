import sys
from pathlib import Path

# Ensure repository root is on sys.path so `import backend.*` works under pytest.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

