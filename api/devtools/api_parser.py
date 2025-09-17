from pathlib import Path
from prance import ResolvingParser

api_path = Path(__file__).parent / "openapi.yaml"

spec = None
if api_path.exists:
    print(f"parsing {api_path}")
    parser = ResolvingParser(str(api_path))
    spec = parser.specification

if spec:
    for path, methods in spec["paths"].items():
        for method, info in methods.items():
            print("Path:", path, "Methode:", method, "operationId:", info.get("operationId"))
