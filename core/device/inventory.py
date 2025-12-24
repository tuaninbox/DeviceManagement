from .session import DeviceSession
import sys, traceback
class DeviceInventoryCollector(DeviceSession):
    def get_host_info(self):
        try:
            """
            Updated workflow:
            1. Run show version
            2. Run show ip interface brief (IOS/IOSXE)
            Run show ip interface brief vrf all (NXOS)
            3. Determine which interface has the management IP
            4. Query VRF for that interface using:
            - IOS/IOSXE: show run interface <intf>
            - NXOS:      show run interface <intf>
            """

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
            }

            if not result.get("success"):
                return host_info

            output = result["output"]

            # -----------------------------
            # 1. Parse show version
            # -----------------------------
            show_ver = output.get("show version", {})
            version_info = show_ver.get("version", {})

            host_info["version"] = version_info.get("version")
            host_info["uptime"] = version_info.get("uptime")
            host_info["serial"] = version_info.get("chassis_sn") or version_info.get("processor_board_id")
            host_info["model"] = version_info.get("chassis") or version_info.get("platform")
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

        if self.os.lower() in ["ios", "iosxe"]:
            # Genie structure: vrf -> interfaces list
            for vrf_name, data in vrf_output.items():
                interfaces = data.get("interfaces", [])
                for intf in interfaces:
                    vrf_map[intf] = vrf_name

        elif self.os.lower() == "nxos":
            # Genie structure: dict of interfaces
            for intf, data in vrf_output.items():
                vrf_map[intf] = data.get("vrf", "default")

        return vrf_map

    def _parse_interface_details(self, parsed, vrf_map):
        interfaces = []

        if not isinstance(parsed, dict):
            return interfaces

        for name, data in parsed.items():
            if data.get("is_deleted", False):
                continue

            iface = {
                "name": name,
                "status": data.get("oper_status"),
                "line_protocol": data.get("line_protocol"),
                "description": data.get("description"),
                "mac_address": data.get("mac_address"),
                "mtu": data.get("mtu"),
                "speed": data.get("speed"),
                "duplex": data.get("duplex"),
                "type": data.get("type"),
                "auto_mdix": data.get("auto_mdix"),
                "negotiation": data.get("negotiation"),
                "ip_address": None,
                "subnet_mask": None,
                "vrf": vrf_map.get(name),
            }

            # IPv4 block
            ipv4 = data.get("ipv4")
            if isinstance(ipv4, dict):
                for ip, ipinfo in ipv4.items():
                    iface["ip_address"] = ip
                    iface["subnet_mask"] = ipinfo.get("prefix_length")
                    break

            interfaces.append(iface)

        return interfaces

    
    def get_modules(self):
        try:
            os_cmds = {
                "ios": ["show inventory"],
                "iosxe": ["show inventory"],
                "nxos": ["show inventory"],   # use show inventory for consistency
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
            cmd = commands[0]

            if not result.get("success"):
                return modules

            parsed = result["output"].get(cmd, {})

            def walk_inventory(inv):
                if not isinstance(inv, dict):
                    return

                for k, v in inv.items():
                    if isinstance(v, dict):
                        # Leaf entry: has inventory fields
                        if any(field in v for field in (
                            "pid", "product_id", "descr", "description",
                            "sn", "serial_number", "vid", "hw_rev", "hardware_revision"
                        )):
                            entry_name = (
                                v.get("name")           # Genie often provides a proper name here
                                or k                    # fallback to dict key
                                or v.get("pid")         # fallback to PID
                                or v.get("product_id")  # fallback to product_id
                                or "unknown"            # last resort
                            )
                            modules.append({
                                "name": entry_name.strip(),
                                "description": v.get("descr") or v.get("description"),
                                "pid": v.get("pid") or v.get("product_id"),
                                "part_number": v.get("pid") or v.get("part_number"),
                                "serial_number": v.get("sn") or v.get("serial_number"),
                                "hw_revision": v.get("hw_revision") or v.get("vid") or v.get("hardware_revision"),
                                # "type": self._classify_module_type(entry_name, v.get("descr") or v.get("description")),
                                # "model": v.get("pid") or v.get("product_id"),
                            })
                        else:
                            # Not a leaf, recurse deeper
                            walk_inventory(v)

            if isinstance(parsed, dict):
                walk_inventory(parsed)
            else:
                raw = result["output"].get(cmd)
                if isinstance(raw, str):
                    if self.os.lower() == "nxos":
                        modules.extend(self._fallback_parse_nxos_hardware(raw))
                    elif self.os.lower() in ["ios","iosxe","aironet","dellos10"]:
                        modules.extend(self._fallback_parse_inventory(raw))
                    elif self.os.lower() == "f5":
                        modules.extend(self._fallback_parse_f5_hardware(raw))

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


if __name__=="__main__":
    pass