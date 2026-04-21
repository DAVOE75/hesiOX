import urllib.request
import os

url = "https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/spain-provinces.geojson"
path = "static/js/maps/spain-provinces.geojson"

os.makedirs(os.path.dirname(path), exist_ok=True)

print(f"Downloading {url} to {path}...")
try:
    urllib.request.urlretrieve(url, path)
    print("Download successful!")
except Exception as e:
    print(f"Error: {e}")
