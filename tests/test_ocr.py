import requests
import io
from PIL import Image

def test_ocr_endpoint():
    url = 'http://127.0.0.1:5000/api/ocr/advanced'
    
    # 1. Test with no file
    print("Testing with no file...")
    try:
        r = requests.post(url)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.json()}")
    except Exception as e:
        print(f"Request failed: {e}")

    # 2. Test with invalid file extension
    print("\nTesting with invalid file extension...")
    try:
        files = {'file': ('test.txt', 'This is a text file', 'text/plain')}
        r = requests.post(url, files=files)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.json()}")
    except Exception as e:
        print(f"Request failed: {e}")

    # 3. Test with valid image (requires server to be running and supporting Tesseract)
    print("\nTesting with valid image...")
    img = Image.new('RGB', (100, 30), color = (73, 109, 137))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    try:
        files = {'file': ('test_image.png', img_byte_arr, 'image/png')}
        r = requests.post(url, files=files)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}") # Raw text in case of 500 html error
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == '__main__':
    test_ocr_endpoint()
