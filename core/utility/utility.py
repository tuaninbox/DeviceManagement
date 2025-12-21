import re, sys
import os
from datetime import datetime

BASE_DIR = "device_data"  # folder at project root

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

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{device_hostname}_{category}_{timestamp}.txt"
    file_path = os.path.join(BASE_DIR, filename)

    with open(file_path, "w") as f:
        f.write(content)

    return file_path
