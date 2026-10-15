# Garantiza que `import books_scrapy` funcione al correr pytest desde la raiz
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
