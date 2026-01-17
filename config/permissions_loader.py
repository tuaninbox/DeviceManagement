import yaml
from pathlib import Path

def load_permissions():
    yaml_path = Path(__file__).parent / "permissions.yaml"
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)["permissions"]

PERMISSIONS = load_permissions()
