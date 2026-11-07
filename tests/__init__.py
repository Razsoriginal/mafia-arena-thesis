import os
import tempfile

os.environ.setdefault("MAFIA_RAW_DIR", tempfile.mkdtemp(prefix="mafia-test-raw-"))
