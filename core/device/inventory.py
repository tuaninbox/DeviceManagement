from .session import DeviceSession
import sys, traceback
from core.logging_manager import setup_loggers

success_logger, fail_logger = setup_loggers(logger_name="normalize_interfaces")

class DeviceInventoryCollector(DeviceSession):
    def get_host_info(self):
        try:
            os_cmds = {
                "ios": ["show version"],
                "iosxe": ["show version"],
                "nxos": ["show version"],
            }

            commands = os_cmds.get(self.os.lower())
            if not commands:
                raise ValueError(f"Unsupported OS type: {self.os}")

            original_cmdlist = self.cmdlist
            self.cmdlist = commands

            # Run both commands
            result = self._run_session(out_format="json")
            self.cmdlist = original_cmdlist

            host_info = {
                "hostname": self.hostname,
                "ip": self.host,
                "os": self.os,
                "version": None,
                "uptime": None,
                "serial": None,
                "model": None,
                "mgmt_interface": None,
                "mgmt_vrf": None,
                "location": self.location,
                "group": self.group,
            }

            if not result.get("success"):
                return host_info

            output = result["output"]

            # -----------------------------
            # 1. Parse show version
            # -----------------------------
            show_ver = output.get("show version", {})
            version_info = show_ver.get("version", {})
            # NX-OS Genie structure 
            platform_info = show_ver.get("platform", {})
            hardware_info = platform_info.get("hardware", {})

            host_info["version"] = version_info.get("version") or platform_info.get("software", {}).get("system_version")
            host_info["uptime"] = version_info.get("uptime") or platform_info.get("kernel_uptime")
            host_info["serial"] = version_info.get("chassis_sn") or version_info.get("processor_board_id") or hardware_info.get("processor_board_id") or hardware_info.get("serial_number") or hardware_info.get("chassis_sn")
            host_info["model"] = version_info.get("chassis") or version_info.get("platform") or hardware_info.get("model") or hardware_info.get("chassis")
            return host_info

        except Exception as e:
            tb = traceback.extract_tb(sys.exc_info()[2])[0]
            self.result["success"] = False
            self.result["error"] = {
                "message": str(e),
                "filename": tb.filename,
                "line": tb.lineno,
                "code": tb.line
            }
            return self.result


    # --- fallback parser for non-Cisco ---
    def _fallback_parse_version(self, output: str) -> str:
        for line in output.splitlines():
            if "Version" in line or "Software" in line:
                return line.strip()
        return None
    
    def get_interfaces(self):
        try:
            """
            Collect detailed interface information and VRF membership.

            Commands used:
            - IOS/IOSXE:
                show interface
                show vrf
            - NXOS:
                show interface
                show vrf interface
            """

            # -----------------------------
            # Determine commands
            # -----------------------------
            if self.os.lower() in ["ios", "iosxe"]:
                cmd_interface = "show interface"
                cmd_vrf = "show vrf"
            elif self.os.lower() == "nxos":
                cmd_interface = "show interface"
                cmd_vrf = "show vrf interface"
            else:
                raise ValueError(f"Unsupported OS type for VRF lookup: {self.os}")

            # -----------------------------
            # Run both commands in one session
            # -----------------------------
            original_cmdlist = self.cmdlist
            self.cmdlist = [cmd_interface, cmd_vrf]
            result = self._run_session(out_format="json")
            self.cmdlist = original_cmdlist

            if not result.get("success"):
                return []

            output = result["output"]

            # -----------------------------
            # Build VRF map
            # -----------------------------
            vrf_map = self._parse_vrf_map(output.get(cmd_vrf, {}))
            # print(f"vrf map: {vrf_map}")
            # -----------------------------
            # Parse interface details
            # -----------------------------
            interfaces = self._parse_interface_details(
                output.get(cmd_interface, {}),
                vrf_map
            )

            return interfaces

        except Exception as e:
            tb = traceback.extract_tb(sys.exc_info()[2])[0]
            self.result["success"] = False
            self.result["error"] = {
                "message": str(e),
                "filename": tb.filename,
                "line": tb.lineno,
                "code": tb.line
            }
            return self.result

    def _parse_vrf_map(self, vrf_output):
        vrf_map = {}

        if not isinstance(vrf_output, dict):
            return vrf_map

        os_type = self.os.lower()

        # -----------------------------
        # IOS / IOS-XE
        # -----------------------------
        if os_type in ["ios", "iosxe"]:
            # Expecting structure: {"vrf": { vrf_name: { "interfaces": [...] }}}
            vrf_data = vrf_output.get("vrf", {})

            for vrf_name, data in vrf_data.items():
                interfaces = data.get("interfaces", [])
                for intf in interfaces:
                    vrf_map[intf] = vrf_name

        # -----------------------------
        # NX-OS
        # -----------------------------
        elif os_type == "nxos":
            # Expecting structure: {"vrf_interface": { intf: { "vrf_name": ... }}}
            vrf_data = vrf_output.get("vrf_interface", {})

            for intf, data in vrf_data.items():
                vrf_name = data.get("vrf_name", "default")
                vrf_map[intf] = vrf_name

        return vrf_map


    def _parse_interface_details(self, parsed, vrf_map):
        interfaces = []

        if not isinstance(parsed, dict):
            fail_logger.error( f"Interface output for device {getattr(self, 'hostname', 'unknown')} " 
                              f"is not a dict: {type(parsed)}" )
            return interfaces

        for name, data in parsed.items():
            if data.get("is_deleted", False):
                continue
            try:
                iface = {
                    "name": name,
                    "status": data.get("oper_status") if data.get("enabled") else "administratively down",
                    "line_protocol": data.get("line_protocol") or data.get("link_state"),
                    "link_down_reason": data.get("link_down_reason"),
                    "port_mode": data.get("port_mode"),
                    "description": data.get("description"),
                    "mac_address": data.get("phys_address") or data.get("mac_address"),
                    "mtu": data.get("mtu"),
                    "speed": f"{data.get('port_speed')}{data.get('port_speed_unit') or ''}",
                    "duplex": data.get("duplex_mode"),
                    "type": data.get("type") or data.get("types"),
                    "fec_mode": data.get("fec_mode"),
                    "media_type": data.get("media_type"),
                    "auto_mdix": data.get("auto_mdix") or data.get("link_type"),
                    "auto_negotiate": data.get("auto_negotiate"),
                    "ip_address": None,
                    "prefix_length": None,
                    "last_link_flapped": data.get("last_link_flapped"),
                    "vrf": vrf_map.get(name),
                }

                # IPv4 block
                ipv4 = data.get("ipv4")
                if isinstance(ipv4, dict):
                    for ip, ipinfo in ipv4.items():
                        iface["ip_address"] = ipinfo["ip"]
                        iface["prefix_length"] = ipinfo["prefix_length"]
                        break

                interfaces.append(iface)
            except Exception as e: 
                fail_logger.error( f"Failed to parse interface {name} for device {getattr(self, 'hostname', 'unknown')}: {e}", exc_info=True )
            
            success_logger.info( f"Parsed {len(interfaces)} interfaces for device {getattr(self, 'hostname', 'unknown')}" )
        return interfaces

    
    # def get_modules_no_sfp_nxos(self):
    #     try:
    #         os_cmds = {
    #             "ios": ["show inventory"],
    #             "iosxe": ["show inventory"],
    #             "nxos": ["show inventory"],   # use show inventory for consistency
    #             "aironet": ["show inventory"],
    #             "dellos10": ["show inventory"],
    #             "f5": ["show sys hardware"],
    #         }

    #         commands = os_cmds.get(self.os.lower())
    #         if not commands:
    #             raise ValueError(f"Unsupported OS type: {self.os}")

    #         original_cmdlist = self.cmdlist
    #         self.cmdlist = commands
    #         result = self._run_session(out_format="json")
    #         self.cmdlist = original_cmdlist

    #         modules = []
    #         cmd = commands[0]

    #         if not result.get("success"):
    #             return modules

    #         parsed = result["output"].get(cmd, {})

    #         def walk_inventory(inv):
    #             if not isinstance(inv, dict):
    #                 return

    #             for k, v in inv.items():
    #                 if isinstance(v, dict):
    #                     # Leaf entry: has inventory fields
    #                     if any(field in v for field in (
    #                         "pid", "product_id", "descr", "description",
    #                         "sn", "serial_number", "vid", "hw_rev", "hardware_revision"
    #                     )):
    #                         entry_name = (
    #                             v.get("name")           # Genie often provides a proper name here
    #                             or k                    # fallback to dict key
    #                             or v.get("pid")         # fallback to PID
    #                             or v.get("product_id")  # fallback to product_id
    #                             or "unknown"            # last resort
    #                         )
    #                         modules.append({
    #                             "name": entry_name.strip(),
    #                             "description": v.get("descr") or v.get("description"),
    #                             "pid": v.get("pid") or v.get("product_id"),
    #                             "part_number": v.get("pid") or v.get("part_number"),
    #                             "serial_number": v.get("sn") or v.get("serial_number"),
    #                             "hw_revision": v.get("hw_revision") or v.get("vid") or v.get("hardware_revision"),
    #                             # "type": self._classify_module_type(entry_name, v.get("descr") or v.get("description")),
    #                             # "model": v.get("pid") or v.get("product_id"),
    #                         })
    #                     else:
    #                         # Not a leaf, recurse deeper
    #                         walk_inventory(v)

    #         if isinstance(parsed, dict):
    #             walk_inventory(parsed)
    #         else:
    #             raw = result["output"].get(cmd)
    #             if isinstance(raw, str):
    #                 if self.os.lower() == "nxos":
    #                     modules.extend(self._fallback_parse_nxos_hardware(raw))
    #                 elif self.os.lower() in ["ios","iosxe","aironet","dellos10"]:
    #                     modules.extend(self._fallback_parse_inventory(raw))
    #                 elif self.os.lower() == "f5":
    #                     modules.extend(self._fallback_parse_f5_hardware(raw))

    #         return modules

    #     except Exception as e:
    #         tb = traceback.extract_tb(sys.exc_info()[2])[0]
    #         self.result["success"] = False
    #         self.result["error"] = {
    #             "message": str(e),
    #             "filename": tb.filename,
    #             "line": tb.lineno,
    #             "code": tb.line
    #         }
    #         return self.result

    def get_modules(self):
        try:
            os_cmds = {
                "ios": ["show inventory"],
                "iosxe": ["show inventory"],
                "nxos": ["show inventory", "show interface transceiver"],
                "aironet": ["show inventory"],
                "dellos10": ["show inventory"],
                "f5": ["show sys hardware"],
            }

            commands = os_cmds.get(self.os.lower())
            if not commands:
                raise ValueError(f"Unsupported OS type: {self.os}")

            original_cmdlist = self.cmdlist
            self.cmdlist = commands
            result = self._run_session(out_format="json")
            self.cmdlist = original_cmdlist

            modules = []
            if not result.get("success"):
                return modules

            # -----------------------------
            # Parse inventory output (first command)
            # -----------------------------
            inv_cmd = commands[0]
            parsed = result["output"].get(inv_cmd, {})

            def walk_inventory(inv):
                if not isinstance(inv, dict):
                    return
                for k, v in inv.items():
                    if isinstance(v, dict):
                        if any(field in v for field in (
                            "pid", "product_id", "descr", "description",
                            "sn", "serial_number", "vid", "hw_rev", "hardware_revision"
                        )):
                            entry_name = (
                                v.get("name") or k or v.get("pid") or v.get("product_id") or "unknown"
                            )
                            modules.append({
                                "name": entry_name.strip(),
                                "description": v.get("descr") or v.get("description"),
                                "pid": v.get("pid") or v.get("product_id"),
                                "part_number": v.get("pid") or v.get("part_number"),
                                "serial_number": v.get("sn") or v.get("serial_number"),
                                "hw_revision": v.get("hw_revision") or v.get("vid") or v.get("hardware_revision"),
                            })
                        else:
                            walk_inventory(v)

            if isinstance(parsed, dict):
                walk_inventory(parsed)
            else:
                raw = result["output"].get(inv_cmd)
                if isinstance(raw, str):
                    if self.os.lower() == "nxos":
                        modules.extend(self._fallback_parse_nxos_hardware(raw))
                    elif self.os.lower() in ["ios","iosxe","aironet","dellos10"]:
                        modules.extend(self._fallback_parse_inventory(raw))
                    elif self.os.lower() == "f5":
                        modules.extend(self._fallback_parse_f5_hardware(raw))

            # -----------------------------
            # Parse NXOS transceiver output (second command)
            # -----------------------------
            if self.os.lower() == "nxos" and len(commands) > 1:
                trans_cmd = commands[1]
                trans_output = result["output"].get(trans_cmd, {})

                if isinstance(trans_output, dict):
                    for intf, details in trans_output.items():
                        if not details.get("transceiver_present"):
                            continue

                        # Preserve ALL fields
                        module_entry = {
                            "transceiver_present": True,
                            "name": f"SFP-{intf}",
                            "interface": intf,
                            "description": details.get("transceiver_type") or details.get("type"),
                            "pid": details.get("part_number") or details.get("cis_product_id"),
                            "part_number": details.get("part_number") or details.get("cis_part_number"),
                            "serial_number": details.get("serial_number"),
                            "hw_revision": details.get("revision"),

                            # SFP-specific fields
                            "transceiver_type": details.get("transceiver_type"),
                            "vendor": details.get("name"),
                            "nominal_bitrate": details.get("nominal_bitrate"),
                            "product_id": details.get("cis_product_id"),
                            "revision": details.get("revision"),
                            "wavelength": details.get("wavelength"),

                            # DOM fields (if present)
                            "dom_temperature": details.get("temperature"),
                            "dom_rx_power": details.get("rx_power"),
                            "dom_tx_power": details.get("tx_power"),
                            "dom_voltage": details.get("voltage"),
                            "dom_bias_current": details.get("bias_current"),
                        }

                        modules.append(module_entry)



            # -----------------------------
            # Map IOS/IOSXE module names to interfaces
            # -----------------------------
            if self.os.lower() in ["iosxe", "ios"]:
                for m in modules:
                    name = m.get("name", "")
                    if name.startswith("subslot"):
                        # Router style: "subslot 0/0 transceiver 1"
                        parts = name.split()
                        if len(parts) >= 4 and parts[2] == "transceiver":
                            slot = parts[1]        # "0/0"
                            trans_num = parts[3]   # "1"
                            # Build full interface name. Choose GigabitEthernet by default,
                            # but you can adjust if your inventory indicates FastEthernet.
                            m["interface"] = f"{slot}/{trans_num}"
                    elif any(prefix in name for prefix in ["GigabitEthernet", "FastEthernet", "TenGigabitEthernet"]):
                        # Switch style: module name already matches interface name
                        m["interface"] = name

            return modules

        except Exception as e:
            tb = traceback.extract_tb(sys.exc_info()[2])[0]
            self.result["success"] = False
            self.result["error"] = {
                "message": str(e),
                "filename": tb.filename,
                "line": tb.lineno,
                "code": tb.line
            }
            return self.result


    def _classify_module_type(self, name, descr):
        text = f"{name} {descr}".lower()

        if "sup" in text or "supervisor" in text:
            return "supervisor"
        if "line card" in text or "ethernet module" in text:
            return "linecard"
        if "power" in text or "psu" in text:
            return "power_supply"
        if "fan" in text:
            return "fan"
        if "sfp" in text or "transceiver" in text:
            return "transceiver"
        if "chassis" in text:
            return "chassis"

        return "module"



    def _fallback_parse_inventory(self, text):
        modules = []
        current = {}

        for line in text.splitlines():
            line = line.strip()

            if line.startswith("NAME:"):
                if current:
                    modules.append(current)
                current = {
                    "name": line.split("NAME:", 1)[1].split(",", 1)[0].strip('" '),
                    "description": None,
                    "pid": None,
                    "serial": None,
                    "part_number": None,
                    "hw_revision": None,
                    "type": None,
                    "model": None,
                }

            elif "DESCR:" in line:
                current["description"] = line.split("DESCR:", 1)[1].strip('" ')

            elif "PID:" in line:
                parts = line.split()
                current["pid"] = parts[1]
                current["part_number"] = parts[3] if len(parts) > 3 else None
                current["serial"] = parts[5] if len(parts) > 5 else None
                current["model"] = current["pid"]

        if current:
            modules.append(current)

        return modules
    
    def _fallback_parse_nxos_hardware(self, text):
        modules = []
        for line in text.splitlines():
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 4:
                modules.append({
                    "name": parts[0],
                    "description": " ".join(parts[1:-2]),
                    "pid": parts[-2],
                    "serial": parts[-1],
                    "type": self._classify_module_type(parts[0], parts[1]),
                    "model": parts[-2],
                })
        return modules


    def _fallback_parse_f5_hardware(self, text):
        modules = []
        for line in text.splitlines():
            if "Chassis" in line or "Platform" in line:
                continue
            if ":" in line:
                key, val = line.split(":", 1)
                modules.append({
                    "name": key.strip(),
                    "description": val.strip(),
                    "pid": None,
                    "serial": None,
                    "part_number": None,
                    "hw_revision": None,
                    "type": "hardware",
                    "model": None,
                })
        return modules

    def get_inventory(self):
        """
        Gather complete device inventory by delegating to individual functions:
        - get_host_info()
        - get_interfaces()
        - get_modules()
        Returns a single structured dict snapshot.
        """
        try:
            inventory = {
                "host_info": self.get_host_info(),
                "interfaces": self.get_interfaces(),
                "modules": self.get_modules(),
            }
            return inventory

        except Exception as e:
            tb = traceback.extract_tb(sys.exc_info()[2])[0]
            self.result["success"] = False
            self.result["error"] = {
                "message": str(e),
                "filename": tb.filename,
                "line": tb.lineno,
                "code": tb.line
            }
            return self.result


if __name__ == "__main__":
    import argparse
    from pprint import pprint

    parser = argparse.ArgumentParser(description="Run get_modules for a device")
    parser.add_argument("--host", required=True, help="Device hostname or IP")
    parser.add_argument("--os", required=True, help="Device OS type (ios, iosxe, nxos, etc.)")
    parser.add_argument("--username", required=True, help="Login username")
    parser.add_argument("--password", required=True, help="Login password")
    args = parser.parse_args()

    # Initialize your collector
    collector = DeviceInventoryCollector(
        hostname=args.host,
        host=args.host,
        os=args.os,
        username=args.username,
        password=args.password,
        cmdlist=[],
    )

    # Run get_modules
    modules = collector.get_modules()

    print(f"\nModules collected from {args.host} ({args.os}):")
    pprint(modules)
