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


    def __init__(self, name="Logger", log_file=None, level="DEBUG"):
        self.name = name
        if log_file and not log_file.endswith(".csv"):
            log_file += ".csv"
        self.log_file = Path(os.path.join(LOG_DIR, log_file)) if log_file else None

        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            if not self.log_file.exists():
                self.log_file.write_text("")


    def _log(self, level, message):
        timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")
        colored_level = f"{self.COLORS.get(level, '')}{level:<11}{self.COLORS['RESET']}"
        full_msg = f"[{timestamp}] [{self.name}] {colored_level} {message}"

        # Print to terminal
        print(full_msg)

        # Save to file if enabled
        if self.log_file:
            uncolored = f"[{timestamp}] [{self.name}] {level:<11} {message}"
            with self.log_file.open("a", encoding="utf-8") as f:
                f.write(uncolored + "\n")


    def info(self, message): self._log("INFO", message)
    def debug(self, message): self._log("DEBUG", message)
    def warning(self, message): self._log("WARNING", message)
    def error(self, message): self._log("ERROR", message)
    def critical(self, message): self._log("CRITICAL", message)
    def performance(self, message): self._log("PERFORMANCE", message)
    def output(self, message): self._log("OUTPUT", message)
