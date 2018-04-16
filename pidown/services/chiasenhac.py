from bs4 import BeautifulSoup
from requests.utils import requote_uri, urlparse, unquote
from pidown.bases import BaseService, DownloadItem, SongItem


class ChiaSeNhac(BaseService):

    class Meta:
        name = __name__.split('.')[-1]
        description = 'Cộng đồng chia sẻ nhạc chất lượng cao và xếp hạng âm nhạc trực tuyến.'
        hostnames = ['chiasenhac.vn']
    
    def search_url_datasource(self):
        return 'http://search.chiasenhac.vn/search.php?s={}'
    
    def search_results_datasource(self, contents):
        results = []
        self.__html_parser = BeautifulSoup(contents, 'html.parser')
        for tr_item in self.__html_parser.find_all(name='tr'):
            song_title = None
            song_url = None
            song_meta = None
            song_lyric = tr_item.get('title')
            if type(song_lyric) is str:
                song_lyric = '{}...'.format(song_lyric[:20])
            if tr_item.get('title'):
                for a_item in tr_item.find_all(name='a'):
                    if type(a_item.get('class')) is list and 'musictitle' in a_item.get('class'):
                        song_title = a_item.get_text()
                        song_url = a_item.get('href')
                for span_item in tr_item.find_all(name='span'):
                    if type(span_item.get('class')) is list and 'gen' in span_item.get('class'):
                        song_meta = span_item.get_text(" | ", strip=True)
            if song_title and song_url:
                result = SongItem()
                result.title = song_title
                result.url = song_url
                result.meta = '[{}] ({})'.format(
                    song_meta if song_meta else '-',
                    song_lyric if song_lyric else '-'
                )
                results.append(result)
        return results
    
    def get_song_item(self, link):
        contents = self.helper_get_contents(link)
        if not contents or type(contents) is not str:
            return None
        self.__html_parser = BeautifulSoup(contents, 'html.parser')
        song_item = SongItem()
        song_item.url = link
        try:
            song_item.title = unquote(link.split('/')[-1])
            song_item.title = song_item.title.replace('_download.html', '')
        except:
            pass
        for meta in self.__html_parser.find_all(name='meta'):
            if meta.get('name') == 'title' and not song_item.title:
                song_item.title = meta.get('content')
            if meta.get('property') == 'og:description':
                song_item.meta = meta.get('content')
        return song_item
    
    def get_song_items_from_playlist(self, link):
        results = []
        contents = self.helper_get_contents(link)
        if not contents or type(contents) is not str:
            return None
        self.__html_parser = BeautifulSoup(contents, 'html.parser')
        playlist_divs = self.__html_parser.find_all(name='div', attrs={ 'class': ['playlist_prv'], 'id': 'playlist' })
        if len(playlist_divs) == 0:
            return results
        playlist_div = playlist_divs[0]
        for tr_item in playlist_div.find_all(name='tr'):
            if tr_item.get('title'):
                song_item = SongItem()
                song_item.meta = tr_item.get('title')
                if type(song_item.meta) is str:
                    song_item.meta = '{}...'.format(song_item.meta[:20].replace('\n', ''))
                for song_link in tr_item.find_all(name='a'):
                    if song_link.get('class') and 'musictitle' in song_link.get('class'):
                        song_item.title = song_link.get_text()
                    elif not song_item.url:
                        song_item.url = song_link.get('href')
                results.append(song_item)
        return results
    
    def get_link_url_datasource(self, song_item):
        if not isinstance(song_item, SongItem):
            raise Exception('Error while getting download links, song data is incorrect!')
        if not song_item.url or type(song_item.url) is not str:
            raise Exception('Error while getting download links, song URL is invalid!')
        if not song_item.url.endswith('_download.html'):
            song_item.url = song_item.url.replace('.html', '_download.html')
        return song_item.url
    
    def get_link_results_datasource(self, contents, song_item):
        results = []
        self.__html_parser = BeautifulSoup(contents, 'html.parser')
        download_container = self.__html_parser.find(id='downloadlink2')
        if download_container:
            for a_item in download_container.find_all(name='a'):
                link_title = a_item.get_text(' | ', strip=True)
                download_url = a_item.get('href')
                if download_url and link_title:
                    download_item = DownloadItem()
                    url_component = urlparse(download_url)
                    download_item.url = '{}://{}{}'.format(
                        url_component.scheme,
                        url_component.netloc,
                        requote_uri(url_component.path)
                    )
                    download_item.meta = link_title if link_title else 'unknown'
                    download_item.song_item = song_item
                    results.append(download_item)
        return results
