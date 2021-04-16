#!/usr/bin/python3
# coding=utf-8
from datetime import datetime
import string

from bs4 import BeautifulSoup
import requests
import urllib, json
import youtube_dl
import glob
import environ

from concurrent.futures import ThreadPoolExecutor

env = environ.Env(DEBUG=(bool, True))

def get_movie_urls():
    schlefaz_mediathek_url = "https://www.tele5.de/schlefaz/mediathek/"

    page = requests.get(schlefaz_mediathek_url)

    soup = BeautifulSoup(page.content, 'html.parser')
    links = soup.findAll("a", {"class": "movie-video__link"})

    movie_urls = []
    for link in links:
        movie_urls.append(f"https://www.tele5.de{link['href']}")

    return movie_urls


def get_video_id(movie_url):
    page = requests.get(movie_url)

    soup = BeautifulSoup(page.content, 'html.parser')
    links = soup.findAll("div", {"class": ["list--video", "playlist-type"]})

    return links[0]['data-id']


def get_video_data(video_id):
    api_url = f"https://cdn.jwplayer.com/v2/media/{video_id}"

    with urllib.request.urlopen(api_url) as response:
        data = json.loads(response.read())

    return data


def sanitize_filename(s):
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    filename = ''.join(c for c in s if c in valid_chars)
    filename = filename.replace(' ', '_')

    # Special case: Make sure the last character is not a dot. Windows will not be able to handle it
    if filename[-1] == '.':
        filename += "_"

    return filename


class YoutubeDlLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)


def download_video(download_link, file_name, path):
    ydl_opts = {
        "outtmpl": f"{path}/{file_name}.%(ext)s",
        "logger": YoutubeDlLogger(),
        "quiet": env.bool("YDL_QUIET_MODE", True),
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([download_link])


def save_json(data, file_name, path):
    if not env.bool("SAVE_JSON", True):
        return

    with open(f'{path}/{file_name}.json', 'w') as outfile:
        json.dump(data, outfile, indent=4)


def download_cover(video_data, file_name, path):
    if not env.bool("DOWNLOAD_COVER", True):
        return

    try:
        cover_url = video_data['playlist'][0]['thumb_alt']
    except:
        print(f"Failed finding cover link for {file_name}")
        return

    urllib.request.urlretrieve(cover_url, f"{path}/{file_name}.jpg")


def replace_umlaut(string):
    string = string.encode()
    for umlaut, replacer in {'ü': b"ue", 'Ü': b"UE", 'ä': b"ae", 'Ä': b"AE", 'ö': b"oe", 'Ö': b"OE",
                             'ß': b"sz"}.items():
        umlaut = umlaut.encode()
        string = string.replace(umlaut, replacer)

    string = string.decode('utf-8')
    return string


def download_worker(movie_url):
    video_id = get_video_id(movie_url)
    video_data = get_video_data(video_id)

    try:
        download_link = video_data['playlist'][0]['sources'][0]['file']
        movie_name = replace_umlaut(video_data['title'])
        pubdate = int(video_data['playlist'][0]['pubdate'])
    except:
        print(f"Couldn't retrieve or parse information for id {video_id}")
        return

    formatted_date = datetime.utcfromtimestamp(pubdate).strftime('%Y-%m-%d')
    file_name = sanitize_filename(f"{formatted_date}_{movie_name}")
    path = f"{env.str('OUTPUT_DIRECTORY', 'SchleFaZ')}/{file_name}"

    if env.bool("SKIP_EXISTING_MOVIES", True) and glob.glob(f"{path}/{file_name}.*"):
        print(f"Skipping already existing movie '{file_name}'")
        return

    print(f"Downloading movie '{file_name}'...")
    download_video(download_link, file_name, path)
    save_json(video_data, file_name, path)
    download_cover(video_data, file_name, path)


def main():
    # Load environment variables
    environ.Env.read_env()

    max_workers = env.int('MAX_WORKERS', 1)
    movie_urls = get_movie_urls()

    print(f"Found {len(movie_urls)} movies. Starting download with {max_workers} parallel workers...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for movie_url in movie_urls:
            executor.submit(download_worker, movie_url)


if __name__ == '__main__':
    main()
