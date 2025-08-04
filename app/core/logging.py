from datetime import datetime
from pathlib import Path
import os
from zoneinfo import ZoneInfo

LOG_DIR = Path("logs")
if not LOG_DIR.exists():
    LOG_DIR.mkdir(parents=True, exist_ok=True)



class Logger:
    COLORS = {
        "INFO": "\033[94m",       # Blue
        "DEBUG": "\033[90m",      # Gray
        "WARNING": "\033[93m",    # Yellow
        "ERROR": "\033[91m",      # Red
        "CRITICAL": "\033[95m",   # Magenta
        "PERFORMANCE": "\033[92m",# Green
        "OUTPUT": "\033[96m",     # Cyan
        "RESET": "\033[0m",
    }


    def __init__(self, name="Logger"):
        self.name = name


    def _log(self, level, message, log_file=None):
        timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
        colored_level = f"{self.COLORS.get(level, '')}{level:<11}{self.COLORS['RESET']}"
        full_msg = f"[{timestamp}] [{self.name}] {colored_level} {message}"

        # Print to terminal
        if level == "ERROR":
            print(full_msg)

        # Save to file if enabled
        if log_file:
            uncolored = f"[{timestamp}] [{self.name}] {level:<11} {message}"
            with log_file.open("a", encoding="utf-8") as f:
                f.write(uncolored + "\n")


    def info(self, message): self._log(level="INFO", message=message, log_file=Path(os.path.join(LOG_DIR, "operation.csv")))
    def debug(self, message): self._log(level="DEBUG", message=message, log_file=Path(os.path.join(LOG_DIR, "operation.csv")))
    def warning(self, message): self._log(level="WARNING", message=message, log_file=Path(os.path.join(LOG_DIR, "operation.csv")))
    def error(self, message): self._log(level="ERROR", message=message, log_file=Path(os.path.join(LOG_DIR, "operation.csv")))
    def critical(self, message): self._log(level="CRITICAL", message=message, log_file=Path(os.path.join(LOG_DIR, "operation.csv")))
    def performance(self, message): self._log(level="PERFORMANCE", message=message, log_file=Path(os.path.join(LOG_DIR, "performance.csv")))
    def output(self, message): self._log(level="OUTPUT", message=message, log_file=Path(os.path.join(LOG_DIR, "outputs.csv")))
