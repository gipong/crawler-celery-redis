import abc
import selenium
from selenium.webdriver import Chrome
from selenium.webdriver import Firefox
import time
import os
import glob
import asyncio
import aiohttp
import hashlib
import sqlite3
import urllib.parse
import psycopg2


class CrawlerBrowser(object, metaclass=abc.ABCMeta):
    BROWSER_TYPE = {'Chrome': Chrome, 'Firefox': Firefox}
    BROWSER_OPTIONS = {
        'Chrome': selenium.webdriver.ChromeOptions(),
        'Firefox': selenium.webdriver.FirefoxOptions()
    }
    SEARCH_TYPE = {
        'Chrome': {

        },
        'Firefox': {

        }
    }

    def __init__(self, browser_type: str, driver: str, sqlite_db: str) -> None:
        self.browser_type = browser_type
        self.browser = None
        self.driver = driver
        self.options = None
        self.sqlite_db = sqlite_db
        self.con = None
        self.cursor = None
        self.task_url = None
        self.download_urls = []

        self.create_browser_instance()
        self.init_connection()

    @classmethod
    def set_task_url(cls, url_template: str) -> None:
        cls.task_url = url_template

    def create_browser_instance(self) -> None:
        self.options = self.BROWSER_OPTIONS[self.browser_type]
        # self.options.headless = False
        # self.options.add_argument("start-maximized")
        self.options.add_argument("--headless")
        self.options.add_argument("--whitelisted-ips")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-extensions")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--disable-gpu")
        # self.browser = self.BROWSER_TYPE[self.browser_type](executable_path=self.driver, options=self.options)
        self.browser = Chrome(options=self.options)

    @classmethod
    @abc.abstractmethod
    def init_connection(cls) -> None:
        return NotImplemented

    @classmethod
    def create_url(cls, term: str) -> str:
        search_term = term.replace(' ', '+')
        url = cls.task_url.format(search_term)
        return url

    @staticmethod
    def create_url_by_image() -> str:
        return "https://www.bing.com/?scope=images&nr=1&FORM=NOFORM"

    def search_by_term(self, term: str) -> None:
        search_url = self.create_url(term)
        self.browser.get(search_url)
        self.fetch_all_images(term)

    def search_by_term_more(self, url: str, term: str) -> None:
        self.browser.get(url)
        self.fetch_all_images('more {}'.format(term))

    def fetch_all_images(self, term: str) -> None:
        scroll_times = 20
        scroll_height = 2000
        time_interval = 3
        i = 1

        target = self.browser.execute_script("return document.querySelector('img').className.split(' ')[1];")
        footer = None

        while i < scroll_times and footer is None:
            self.browser.execute_script("scrollTo(0, arguments[0])", scroll_height * i)
            i += 1
            time.sleep(time_interval)

        footer = self.browser.find_element_by_css_selector('.mye4qd')
        try:
            footer.click()
        except Exception as e:
            pass

        j = 1
        while j < scroll_times:
            self.browser.execute_script("scrollTo(0, arguments[0])", scroll_height * j + scroll_height * i)
            j += 1
            time.sleep(time_interval)

        images = self.browser.find_elements_by_css_selector("a.wXeWr")
        for img in images:
            more = None

            try:
                img.click()
                time.sleep(0.5)
                more = self.browser.find_element_by_css_selector("a.So4Urb")

                if img.get_attribute('href') is not None:
                    href = urllib.parse.unquote(img.get_attribute('href').split('?')[1].split('&')[0].split('=')[1])
                    self.insert_images2db(term, href, more.get_attribute('href') if more else "")

            except Exception as e:
                print(e)
                pass

    @classmethod
    @abc.abstractmethod
    def insert_images2db(cls, term: str, href: str, more_url: str) -> None:
        return NotImplemented

    def search_by_picture(self, image_path: str) -> None:
        search_url = self.create_url_by_image()
        self.browser.get(search_url)

        print(image_path, search_url)

        time.sleep(5)
        input_string = self.browser.find_element_by_css_selector('#sb_fileinput')
        input_string.send_keys(image_path)

        time.sleep(5)

        self.browser.execute_script("window.scrollTo(0, arguments[0])", 5000 * 1)

        pre_img_count = 0
        img_count = len(self.browser.find_elements_by_css_selector('a.richImgLnk'))
        i = 1

        while img_count != pre_img_count:
            self.browser.execute_script("window.scrollTo(0, arguments[0])", 5000 * (i + 1))
            i = i + 1

            time.sleep(2)
            pre_img_count = img_count
            img_count = len(self.browser.find_elements_by_css_selector('a.richImgLnk'))

        print('enter into selector panel')
        self.browser.find_element_by_css_selector('a.richImgLnk').click()

        search_end = False

        while not search_end:
            search_end = self.find_img_href(search_end)

    def find_img_href(self, search_status: bool):
        try_times = 0
        more_tab = None
        while try_times > 3 or more_tab is None:
            more_tab = self.browser.find_element_by_css_selector('li.t-pim')
            try_times = try_times + 1

        if more_tab:
            more_tab.click()

        time.sleep(1)

        try:
            self.browser.find_element_by_css_selector('div.msz').click()
        except Exception as e:
            print(e)

        time.sleep(1)

        try:
            ori_images = self.browser.find_elements_by_css_selector('div.msz_g_c')

            resolution_set = self.browser.find_elements_by_css_selector('div.msz_g_t')

            max_resolution_index = self.find_max_resolution(resolution_set)
            a = ori_images[max_resolution_index].find_element_by_css_selector('a.richImgLnk')
            a.click()

            self.browser.switch_to_window(self.browser.window_handles[1])
            target_image_url = self.browser.current_url
            self.browser.close()

            time.sleep(1)
            self.browser.switch_to_window(self.browser.window_handles[0])
            self.download_urls.append(target_image_url)
        except Exception as e:
            print('can not find the detail pictures :', e)
            pass

        try:
            self.browser.find_element_by_css_selector('div#navr').click()
        except Exception as e:
            print('no navbar element, move to next target :', e)
            search_status = True
            pass

        time.sleep(1)

        return search_status

    @staticmethod
    def find_max_resolution(resolution_list: list):
        candidate_list = []

        for resolution in resolution_list:
            target = resolution.text.split(' x ')
            candidate_list.append(int(target[0]) * int(target[1]))

        return candidate_list.index(max(candidate_list))

    @staticmethod
    async def download_image(session, url):
        try:
            async with session.get(url['src']) as response:
                replace_target = url['target']

                if response.status != 404 and not os.path.exists(
                        url['target']) and response.content_type == 'image/jpeg':
                    await asyncio.sleep(1)

                    with open(replace_target, 'wb') as f_handle:
                        while True:
                            chunk = await response.content.read(1024)
                            if not chunk:
                                break
                            f_handle.write(chunk)

                    print('download : {}'.format(replace_target))
                    return await response.release()

                else:
                    print('skip the exist image', url['target'])

        except Exception as e:
            print(e)
            pass

    async def image_downloader(self, urls):
        async with aiohttp.ClientSession() as session:
            tasks = [self.download_image(session, url) for url in urls]
            return await asyncio.gather(*tasks)

    def run_download_process(self, target_urls: list, download_folder: str):
        urls_list = []
        download_count = 500
        s = hashlib.sha1()

        for target_url in target_urls:
            try:
                s.update(str(target_url).encode('utf-8'))
                filename = s.hexdigest()
                urls_list.append({
                    "src": target_url,
                    "target": "{}/{}.jpg".format(download_folder, filename)
                })

            except Exception as e:
                print('process target url exception :', e)
                pass

        try:
            for j in range(len(urls_list) // download_count + 1):
                urls = urls_list[j * download_count: (j + 1) * download_count]
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.image_downloader(urls))
                loop.run_until_complete(asyncio.sleep(60))
        except Exception as e:
            print('download process finished :', e)
            pass

    def run_fetch_image_process(self, image_path: str, download_folder: str):
        self.search_by_picture(image_path)
        self.run_download_process(self.download_urls, download_folder)
        self.download_urls = []

    def close_browser(self):
        del self.browser


class LocalCrawler(CrawlerBrowser):
    def __init__(self, browser_type: str, driver: str, sqlite_db: str):
        super().__init__(browser_type, driver, sqlite_db)
        self.set_task_url("""
            https://www.google.com/search?as_st=y&tbm=isch&hl=en-US&as_q={}
            &as_epq=&as_oq=&as_eq=&cr=&as_sitesearch=&safe=images&tbs=isz:l,itp:photo,ift:jpg#imgrc=UlZDdA5mjGuSLM
        """)

    def init_connection(self) -> None:
        self.con = sqlite3.connect(self.sqlite_db)
        self.cursor = self.con.cursor()

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS face (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term TEXT,
                url TEXT,
                moreUrl TEXT
            );
        """)
        self.con.commit()

    def insert_images2db(self, term: str, href: str, more_url: str) -> None:
        self.cursor.execute("""
           insert into face (term, url, moreUrl)
           select ?, ?, ?
           where not exists (
               select * from face where url = ?
           )
        """, (term, href, more_url, href))
        self.con.commit()


class RemoteCrawler(CrawlerBrowser):
    def __init__(self, browser_type: str, driver: str, sqlite_db: str):
        super().__init__(browser_type, driver, sqlite_db)
        self.set_task_url("""
            https://www.google.com/search?as_st=y&tbm=isch&as_q={}
            &as_epq=&as_oq=&as_eq=&cr=&as_sitesearch=&safe=images&tbs=itp:face
        """)

    def init_connection(self) -> None:
        try:
            self.con = psycopg2.connect(
                user='postgres',
                password='postgres',
                host='192.168.6.58',
                port='5432',
                database='wiki'
            )

            self.cursor = self.con.cursor()
        except Exception as e:
            print('can not init connection', e)

    def insert_images2db(self, term: str, href: str, more_url: str) -> None:
        print(more_url)
        self.cursor.execute("""
           insert into name_list_urls (term, url, more_url)
           select '{}', '{}', '{}'
           where not exists (
               select 1 from name_list_urls where url = '{}'
           )
        """.format(term, href, more_url, href))
        self.con.commit()

    def lock_fetch_row(self, id: int) -> None:
        self.cursor.execute("""
            update name_list
            set status = 'working'
            where id = {}
        """.format(id))
        self.con.commit()

    def unlock_fetch_row(self, id: int, finished: bool) -> None:
        self.cursor.execute("""
            update name_list
            set status = null, finished = {}
            where id = {}
        """.format(True if finished else 'NULL', id))
        self.con.commit()

    def search(self, search_list: list) -> None:
        self.lock_fetch_row(search_list[0])
        self.search_by_term(search_list[1])
        self.unlock_fetch_row(search_list[0], True)
