import os
import time
import tarfile
import glob
from celery import Celery
import psycopg2
from CrawlerBrowser import RemoteCrawler


CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379'),
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379')

celery = Celery('tasks', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)


@celery.task(name='tasks.add')
def add(x: int, y: int) -> int:
    time.sleep(5)
    return x + y


@celery.task(name='tasks.fetch_image_folder')
def fetch_image_folder(task_name: str, filename: str) -> str:
    print(task_name)
    return "{} : {} uploaded.".format(task_name, filename)


@celery.task(name='tasks.start_to_search_image')
def start_to_search_image(tar_name: str, ori_filename: str) -> str:
    print(tar_name)

    folder_name = tar_name.split('.tar')[0]
    ori_name = ori_filename.split('.tar')[0]

    if os.path.isdir("/opts/download-data/tmp/{}".format(folder_name)) is None:
        os.mkdir("/opts/download-data/tmp/{}".format(folder_name))

    with tarfile.open("/opts/download-data/{}".format(tar_name)) as opened_tarfile:
        opened_tarfile.extractall("/opts/download-data/tmp/{}".format(folder_name))

    count = 0

    for i, pic in enumerate(glob.iglob("/opts/download-data/tmp/{}/{}/*g".format(folder_name, ori_name))):
        remote_crawler = RemoteCrawler('Chrome', '/usr/local/bin/chromedriver', 'None')
        remote_crawler.run_fetch_image_process(pic, "/opts/download-data/data")
        count = count + 1
        remote_crawler.close_browser()

    print(remote_crawler)
    return "{}: {}, {}, {}".format('start to search image', count, folder_name, ori_filename)
