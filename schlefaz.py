#!/usr/bin/python3
# coding=utf-8
from datetime import datetime
import string

from bs4 import BeautifulSoup
import requests
import urllib, json
import youtube_dl
import glob

from concurrent.futures import ThreadPoolExecutor

SAVE_JSON = True
DOWNLOAD_COVER = True
SKIP_EXISTING_MOVIES = True
YDL_QUIET_MODE = True
MAX_WORKERS = 3
OUTPUT_DIRECTORY = "output"


def get_movie_urls():
    schlefaz_mediathek_url = "https://www.tele5.de/schlefaz/mediathek/"

    page = requests.get(schlefaz_mediathek_url)

    soup = BeautifulSoup(page.content, 'html.parser')
    links = soup.findAll("a", {"class": "movie-video__link"})

    movie_urls = []
    for link in links:
        movie_urls.append("https://www.tele5.de{0}".format(link['href']))

    return movie_urls


def get_video_id(movie_url):
    page = requests.get(movie_url)

    soup = BeautifulSoup(page.content, 'html.parser')
    links = soup.findAll("div", {"class": ["list--video", "playlist-type"]})

    return links[0]['data-id']


def get_video_data(video_id):
    api_url = "https://cdn.jwplayer.com/v2/media/{0}".format(video_id)

    with urllib.request.urlopen(api_url) as response:
        data = json.loads(response.read())

    return data


def sanitize_filename(s):
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    filename = ''.join(c for c in s if c in valid_chars)
    filename = filename.replace(' ', '_')
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
        "outtmpl": '{}/{}.%(ext)s'.format(path, file_name),
        "logger": YoutubeDlLogger(),
        "quiet": YDL_QUIET_MODE
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([download_link])


def save_json(data, file_name, path):
    if not SAVE_JSON:
        return

    with open('{}/{}.json'.format(path, file_name), 'w') as outfile:
        json.dump(data, outfile, indent=4)


def download_cover(video_data, file_name, path):
    if not DOWNLOAD_COVER:
        return

    try:
        cover_url = video_data['playlist'][0]['thumb_alt']
    except:
        print("Failed finding cover link for {}".format(file_name))
        return

    urllib.request.urlretrieve(cover_url, "{}/{}.jpg".format(path, file_name))


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
        print("Couldn't retrieve or parse information for id {0}".format(video_id))
        return

    file_name = sanitize_filename(
        "{}_{}".format(datetime.utcfromtimestamp(pubdate).strftime('%Y-%m-%d'), movie_name))
    path = "{}/{}".format(OUTPUT_DIRECTORY, file_name)

    if not glob.glob("{}/{}.*".format(path, file_name)) or not SKIP_EXISTING_MOVIES:
        print("Downloading movie '{}'...".format(file_name))
        download_video(download_link, file_name, path)
        save_json(video_data, file_name, path)
        download_cover(video_data, file_name, path)
    else:
        print("Skipping already existing movie '{}'".format(file_name))


def main():
    movie_urls = get_movie_urls()

    print("Found {} movies. Starting download with {} parallel workers...".format(len(movie_urls), MAX_WORKERS))

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for movie_url in movie_urls:
            executor.submit(download_worker, movie_url)


if __name__ == '__main__':
    main()
