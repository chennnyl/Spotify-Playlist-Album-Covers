from PIL import Image                       # guess
import re                                   # snatch url from input
import sys                                  # exit gracefully
import os                                   # check for duplicates
import subprocess                           # open file
import urllib                               # download images
from requests.exceptions import RetryError  # raised when you have too many requests at once
import threading                            # asynchronous downloads
import time                                 # measure execution length
from math import ceil, sqrt, log10            # image size/batch size
from dotenv import load_dotenv              # client id/secret as env variables

import spotipy                              # guess
from spotipy.oauth2 import SpotifyClientCredentials  # authenticate api requests

load_dotenv()

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials())

url_regex = r"(https:\/\/open.spotify.com\/playlist\/(.+)\?.+)|(spotify:playlist:(.+))"

# get the url for the playlist
input_url = input("Playlist URL or Spotify URI: ")
try:
    uri = "spotify:playlist:" + [a for a in set(re.findall(url_regex, input_url)[0][1::2]) if a != ""][0]
except IndexError:
    print("Invalid URL format")
    sys.exit(-1)

# set download mode
mode = input("Download mode {sequential|threaded}; threaded is shorter but much more prone to errors (threaded): ").upper()
if mode == "": 
    mode = "THREADED"
if mode.upper() not in ["SEQUENTIAL", "THREADED"]:
    print("Invalid mode")
    sys.exit(-1)

# set image resolution
res = input("Output size {0|1|2}; 64px, 320px, and 640px per cover respectively (0): ")
if res not in ["", "0", "1", "2"]:
    print("Invalid output size")
    sys.exit(-1)

if res == "" or res == "0": 
    res = [0, 64]
if res == "1": 
    res = [1, 320]
if res == "2": 
    res = [2, 640]

# get filename (allow more than 1 per playlist)
count = 0
title = sp.playlist(uri, fields="name")["name"]
for i in os.listdir(os.getcwd()):
    if(i.find(title) != -1):
        count += 1
title = f"{title}{f'({count})' if count > 0 else ''}.png"

# get all tracks, MORE than 100!!!11111!11!1!
tracks = []
offset = 0
while uri:
    try:
        r = sp.playlist_tracks(uri, offset=offset, fields="next, items(track(artists, album(href)))")
        tracks.extend(r["items"])
        offset += 100
        if r["next"] is None: 
            uri = None

    except spotipy.SpotifyException:
        print("Error retrieving playlist tracks; is it public?")
        sys.exit(-1)
# filter out tracks with no album/link info (local files/podcast episodes mostly i guess)
tracks = [a for a in tracks if "track" in a and a["track"] is not None]
tracks = [a for a in tracks if "album" in a["track"] and a["track"]["album"] is not None]
tracks = [a for a in tracks if "href" in a["track"]["album"] and a["track"]["album"]["href"] is not None]
# sort by artist
tracks = sorted(tracks, key=lambda a: a["track"]["artists"][0]["name"].upper())

# get all album urls + filter out duplicates
album_urls_first = []
for a in tracks:
    href = a["track"]["album"]["href"]
    album_urls_first.append(href)

album_urls = []
[album_urls.append(x) for x in album_urls_first if x not in album_urls]
# can't be having TOO many threads
if len(album_urls[0::10*ceil(log10(len(album_urls)))]) > 4096 and mode == "THREADED":
    print("Jesus Christ, how many songs do you have?? Thread limit exceeded")
    sys.exit(-1)


# i put this in a function because i wanted to be able to exit arbitrarily but that's not important anymore, oh well
def main_loop():
    start = time.time()
    images = []

    def add_image(i, url):
        # get url
        try:
            image_url = sorted(sp.album(url.split("albums/")[1])["images"], key=lambda a: a["height"])[res[0]]["url"]
        except IndexError:
            album = sp.album(url.split("albums/")[1]) 
            print(album["images"])
        response = None
        attempts = 0
        # try up to 3 times to get the image data
        while response is None and attempts < 3:
            try:
                response = urllib.request.urlopen(image_url, timeout=5)
            except (UnboundLocalError):
                print(f"Failed to download an image ({i+1}/{len(album_urls)}") 
            except RetryError:
                response = None
                attempts = 3
            except OSError: # sometimes the connection is fucky so try again
                add_image(i, url)
            
            attempts += 1
        # add data and info on positioning to image list
        images.append((response, i))

        # status info
        if response is not None:
            rawpercent = len(images)/len(album_urls)
            print(f"[{'■'*(int(50*rawpercent))}{' '*(int(50*(1.0-rawpercent)))}] - {int(100*rawpercent)}%")
    
    # batch multiple download jobs into 1 thread so it doesn't break
    def add_multiple(num1, num2, urls):
        for i in range(num1, num2):
            end = i-num1 if (i-num1) <= len(urls) else len(urls)
            add_image(i, urls[end])

    # asynchronous downloads
    if mode == "THREADED":
        threads = []
        # number of downloads per thread; magic number i stole from god
        offset = 15*ceil(log10(len(album_urls)))
        for i, url in enumerate(album_urls[0::offset]):
            t = threading.Thread(target=add_multiple, args=(i*offset, offset*(i+1), album_urls[offset*i:offset*(i+1)]))
            t.start()
            threads.append(t)

    # synchronous downloads
    else:
        for i, url in enumerate(album_urls):
            add_image(i, url)

    try:
        # collect batch jobs
        if mode == "THREADED":
            [a.join() for a in threads]
        # filter duplicate images that show up somehow????
        cp = sorted(images.copy(), key=lambda a: a[1])
        copy = []
        copy_images = []
        for a in cp:
        	if a[0] not in copy_images:
        		copy_images.append(a[0])
        		copy.append(a)

        successful = len([a for a in copy if a[0] is not None])

        size = ceil(sqrt(successful))

        macro_image = Image.new("RGB", (res[1]*size, res[1]*size))

        print(f"Downloaded {successful} images; {len(album_urls) - successful} failed to download")
        # copy non-blank images over to master image
        for i, image in enumerate([a for a in copy if a[0] is not None]):
            im = Image.open(image[0])
            macro_image.paste(im, box=(res[1]*(i % size), res[1]*(i//size)))
        macro_image.save(title)
        end = time.time()
        print(f"Done in {end-start} sec.")
        subprocess.Popen(["xdg-open", title])
    except KeyboardInterrupt:
        return -1


# do it!! do the thing!! i believe in you!!
main_loop()
