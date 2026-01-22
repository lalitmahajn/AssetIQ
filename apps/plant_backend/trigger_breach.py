import json
import urllib.request


def trigger():
    try:
        req = urllib.request.Request(
            "http://localhost:8000/master/simulate/sla_breach",
            data=json.dumps({}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as response:
            print(response.read().decode("utf-8"))
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    trigger()
