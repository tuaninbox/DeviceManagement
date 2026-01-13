import re, sys
import os
from datetime import datetime, timezone

BASE_DIR = "device_data"  # folder at project root
MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MB safeguard

class bcolors:
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def format_msg(msg,color=""):
    if color == "":
        return f"{msg}"
    else:
        return f"{getattr(bcolors,color)}{msg}{bcolors.ENDC}"
    
def print_result(result, colorize=True,debug=0):
    # print(result)
    if result["success"]:
        header = format_msg(f"{result['hostname']} - {result['host']}", "CYAN") if colorize else f"{result['hostname']} - {result['host']}"
        print(header)
        print("\n".join(result["output"]))
    else:
        err = result["error"]
        msg = f"{result['hostname']} - {result['host']} - {err['message']} at {err['filename']}: {err['line']} - {err['code']}" if debug else f"{result['hostname']} - {result['host']} - {err['message']}"
        print(format_msg(msg, "RED") if colorize else msg)



def save_text_file(device_hostname: str, category: str, content: str) -> str:
    """
    Saves text content to a file and returns the file path.
    category = "running_config", "routing_table", "mac_table"
    """
    os.makedirs(BASE_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{device_hostname}_{category}_{timestamp}.txt"
    file_path = os.path.join(BASE_DIR, filename)

    with open(file_path, "w") as f:
        f.write(content)

    return file_path

def safe_datetime(value):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except:
        return None
    
def safe_read_text(path_str: Optional[str], max_bytes: int = MAX_FILE_BYTES) -> Optional[str]:
    """
    Reads up to max_bytes from a file and returns it as UTF-8 text.
    - Returns None if path is missing/invalid.
    - Reads in binary and decodes with UTF-8, replacing invalid sequences.
    - Returns a formatted error string when an exception occurs.
    """
    if not path_str:
        return None

    path = Path(path_str)
    if not path.exists() or not path.is_file():
        return None

    try:
        # Read only the first max_bytes bytes to avoid large payloads.
        with path.open("rb") as f:
            chunk = f.read(max_bytes)

        text = chunk.decode("utf-8", errors="replace")

        # Optional: indicate truncation (uncomment if you want this behavior)
        # if path.stat().st_size > max_bytes:
        #     text += "\n...[truncated]..."

        return text

    except Exception as exc:
        # Return a formatted error string instead of None.
        return f"[Unable to read file: {path.name}. Error: {type(exc).__name__}: {exc}]"
