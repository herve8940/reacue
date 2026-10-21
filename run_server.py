"""Point d'entrée pour Claude Desktop (chemin absolu, pas besoin de cwd)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reacue_mcp.server import main  # noqa: E402

main()
