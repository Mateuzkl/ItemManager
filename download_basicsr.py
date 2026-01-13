import urllib.request
import tarfile
import os

# Use GitHub archive link for reliable download
url = "https://github.com/XPixelGroup/BasicSR/archive/refs/tags/v1.4.2.tar.gz"
filename = "basicsr-1.4.2.tar.gz"

print(f"Downloading {filename}...")
opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0')]
urllib.request.install_opener(opener)
urllib.request.urlretrieve(url, filename)

print(f"Extracting {filename}...")
with tarfile.open(filename, "r:gz") as tar:
    tar.extractall()

print("Done.") 
