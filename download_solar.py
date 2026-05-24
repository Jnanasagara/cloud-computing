import os
import urllib.request

def download_solar_data():
    url = "https://raw.githubusercontent.com/xdhao/solarRadPredict/main/SolarPrediction.csv"
    dest = os.path.join(os.path.dirname(__file__), "SolarPrediction.csv")
    
    print(f"Downloading solar dataset from: {url}")
    print(f"Destination: {dest}")
    
    try:
        # Use urllib.request from standard library to avoid external dependency issues
        urllib.request.urlretrieve(url, dest)
        print("Download completed successfully!")
        
        # Simple size check
        size_bytes = os.path.getsize(dest)
        print(f"Downloaded file size: {size_bytes / (1024 * 1024):.2f} MB")
    except Exception as e:
        print(f"Error downloading dataset: {e}")
        raise e

if __name__ == "__main__":
    download_solar_data()
