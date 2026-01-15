import urllib.request
import json
import sys

def main():
    url = "http://localhost:8000/auth/login"
    payload = {
        "username": "admin@assetiq.com",
        "pin": "121212"
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req) as response:
            print(f"Status: {response.getcode()}")
            print(f"Response: {response.read().decode('utf-8')}")
            if response.getcode() == 200:
                print("Login SUCCESS")
            else:
                print("Login FAILED")
                sys.exit(1)
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code}")
        print(f"Response: {e.read().decode('utf-8')}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
