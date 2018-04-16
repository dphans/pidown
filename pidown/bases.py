import urllib3
import cgi
import os
import shelve
from requests.utils import requote_uri, unquote


class ConsoleColor:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class SongItem:
    title = None
    meta = None
    url = None

    def __str__(self):
        return '{}{}{} ({}){}'.format(
            ConsoleColor.BOLD + ConsoleColor.OKGREEN,
            self.title if type(self.title) is str else 'unknown',
            ConsoleColor.ENDC + ConsoleColor.OKGREEN,
            self.meta if type(self.meta) is str else '',
            ConsoleColor.ENDC
        )


class DownloadItem:
    song_item = None
    meta = None
    url = None

    def __str__(self):
        return '{}{}{}{}{}'.format(
            ConsoleColor.BOLD + ConsoleColor.OKGREEN,
            self.song_item.title if self.song_item and self.song_item.title else '',
            ConsoleColor.ENDC + ConsoleColor.OKGREEN,
            ' [{}]'.format(self.meta) if self.meta else '',
            ConsoleColor.ENDC
        )


class PiDownPref:
    
    def __init__(self):
        self.__settings_file = 'settings.ini'
    
    def getPref(self, key, replacement=None):
        pref = shelve.open(self.__settings_file)
        result = replacement
        if key in pref:
            result = pref[key]
        pref.close()
        return result
    
    def setPref(self, key, value=None):
        pref = shelve.open(self.__settings_file)
        pref[key] = value
        pref.close()


class BaseService:

    class Meta:
        name = None
        description = None
        hostnames = []
    
    def __init__(self):
        self.__http = urllib3.PoolManager()
        self.__pref = PiDownPref()
    
    def search_url_datasource(self):
        return None
    
    def search_results_datasource(self, contents):
        return None

    def search(self, keyword):
        if type(keyword) is not str:
            raise Exception('Error while processing search keyword, keyword must be str type!')
        search_url = self.search_url_datasource()
        if not search_url:
            raise Exception('Error while building search query, unknown URL returned!')
        html_contents = self.helper_get_contents(search_url.format(requote_uri(keyword)))
        parsed_object = self.search_results_datasource(html_contents)
        return parsed_object if type(parsed_object) is list else []
    
    def get_song_item(self, link):
        return None
    
    def get_song_items_from_playlist(self, link):
        return []
    
    def get_link_url_datasource(self, song_item):
        return None
    
    def get_link_results_datasource(self, contents, song_item):
        return None

    def get_link(self, song_item):
        if not song_item:
            raise Exception('Error while processing song item, song item is None!')
        if not isinstance(song_item, SongItem):
            raise Exception('Error while processing song item, song item is invalid!')
        getlink_url = self.get_link_url_datasource(song_item)
        if not getlink_url:
            raise Exception('Error while getting links, unknown URL returned!')
        html_contents = self.helper_get_contents(getlink_url)
        parsed_object = self.get_link_results_datasource(html_contents, song_item)
        return parsed_object if type(parsed_object) is list else []

    def download(self, download_item):
        if not download_item:
            raise Exception('Error while downloading, download data is missing!')
        if not isinstance(download_item, DownloadItem):
            raise Exception('Error while downloading, data is invalid!')
        if not download_item.url or type(download_item.url) is not str:
            raise Exception('Error while download, missing URL!')

        file_name = "{}.{}".format(
            download_item.song_item.title if download_item.song_item and download_item.song_item.title else unquote(download_item.url.split('/')[-1]),
            download_item.url.split('.')[-1]
        )
        
        destination_directory = self.__pref.getPref('destination', os.path.abspath('.'))
        if not os.path.isdir(destination_directory) or not os.path.exists(destination_directory):
            raise Exception('Download location `{}` is not exist, please recheck directory in settings and try again!'.format(destination_directory))

        file_name = os.path.join(destination_directory, file_name)

        try:
            if os.path.exists(file_name) and os.path.isfile(file_name):
                os.remove(file_name)
        except:
            pass

        u = self.__http.request('GET', download_item.url, preload_content=False)
        f = open(file_name, 'wb')
        
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        print("{}Downloading {}`{}` ({} bytes){}".format(
            ConsoleColor.BOLD + ConsoleColor.WARNING,
            ConsoleColor.ENDC + ConsoleColor.WARNING,
            file_name,
            file_size,
            ConsoleColor.ENDC
        ))
        
        file_size_dl = 0
        block_sz = 8192

        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break
            file_size_dl += len(buffer)
            f.write(buffer)
            status = r"%10d bytes  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
            status = status + chr(8)*(len(status)+1)
            print(status, end='')
        f.close()
        print("\n\033[92m\033[1m -> Done!\033[0m")

    def helper_get_contents(self, link):
        if not link or type(link) is not str:
            return None
        urllib_request = self.__http.request('GET', link)
        _, params = cgi.parse_header(urllib_request.headers.get('Content-Type', ''))
        encoding = params.get('charset', 'utf-8')
        html_contents = urllib_request.data.decode(encoding)
        urllib_request.close()
        return html_contents
