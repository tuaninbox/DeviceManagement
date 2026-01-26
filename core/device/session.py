import os
import sys, re
import traceback
#from napalm import get_network_driver
from netmiko import ConnectHandler
from core.utility.utility import format_msg
from core.utility.sanitizer import SecretSanitizer, ConfigSanitizer
from core.utility.detection import detect_os, normalize_os
from app.databases.devices import SessionLocal
from app.models.devices import Device

import configparser
from pathlib import Path

class DeviceSession:
    def __init__(self, hostname, host, os, user, password, cmdlist, port: int =22, success_logger=None, fail_logger=None, debug=0, 
                outfolder="output", 
                sanitizeconfig=True, 
                removepassword: int = 1|2|4|8,
                location=None,
                group=None):
        try: 
            self.port = int(port) if str(port).strip() else 22 
        except ValueError: 
            self.port = 22 # fallback
        self.hostname = hostname
        self.host = host
        self.os = os
        self.user = user
        self.password = password
        self.cmdlist = cmdlist
        self.success_logger = success_logger
        self.fail_logger = fail_logger
        self.debug = debug
        self.outfolder = outfolder
        self.sanitizeconfig = sanitizeconfig
        self.removepassword = removepassword
        self.location = location
        self.group = group
        self.result = {
            "hostname": hostname,
            "host": host,
            "detected_os": None,
            "success": False,
            "output": "",
            "error": None
        }

    def _run_session(self, removepassword: int = 0, out_format: str = "text", optional_args=None):
        # ------------------------------------------------------------
        # 1. Lazy OS detection (moved from run_parallel)
        # ------------------------------------------------------------
        if not self.os or self.os == "unknown":
            detected = detect_os(self.host, self.user, self.password, self.port)
            normalized = normalize_os(detected)
            self.os = normalized

        # Store detected OS in result so run_parallel can update DB later
        self.result["detected_os"] = self.os

        # Map OS string to Netmiko device_type
        device_type_map = {
            "ios": "cisco_ios",
            "iosxe": "cisco_iosxe",
            "nxos": "cisco_nxos",
            "aironet": "cisco_wlc",
            "dellos10": "dell_os10",
            "f5": "f5_tmsh",  # or "f5_ltm" depending on CLI
        }
        device_type = device_type_map.get(self.os)
        if not device_type:
            # Fallback: try IOS (most common)
            device_type = "cisco_ios"
            self.result["error"] = f"{self.hostname} - Using default OS type: {self.os}"
            if self.fail_logger:
                self.fail_logger.error(self.result["error"])
            return self.result

        conn_params = {
            "device_type": device_type,
            "ip": self.host,
            "username": self.user,
            "password": self.password,
            "port": self.port, 
        }
        if optional_args:
            conn_params.update(optional_args)

        with ConnectHandler(**conn_params) as conn:
            sanitizer = SecretSanitizer()
            commands = self.cmdlist if isinstance(self.cmdlist, list) else [self.cmdlist]

            # Decide output container
            output_lines = {} if out_format == "json" else []

            for cmd in commands:
                if out_format == "json":
                    # Use Genie parser for structured data
                    raw_output = conn.send_command(cmd, use_genie=True)
                    parsed_output = raw_output if isinstance(raw_output, dict) else {}
                    sanitized_output = sanitizer.apply(parsed_output, removepassword)
                    output_lines[cmd] = sanitized_output
                else:
                    # Plain text mode
                    raw_output = conn.send_command(cmd)
                    if self.sanitizeconfig:
                        clean_config = ConfigSanitizer.sanitize(raw_output, self.os, cmd)
                    else:
                        clean_config = raw_output
                    sanitized_output = sanitizer.apply(clean_config, removepassword)
                    output_lines.append(f"{self.hostname}# {cmd}\n{sanitized_output}")

            self.result["success"] = True
            # print(output_lines)
            # self.result["output"] = "\n".join(output_lines)
            self.result["output"] = output_lines

            if self.success_logger:
                self.success_logger.info(
                    f"{self.hostname} - {self.host} - Configuration retrieved successfully"
                )

        return self.result

if __name__=="__main__":
    pass