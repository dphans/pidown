import os
import importlib
import urllib3
from argparse import ArgumentParser
from . import services
from .bases import ConsoleColor, PiDownPref, SongItem


class PiDown:
    
    def __init__(self):
        self.__version = '0.0.1'
        self.__appname = 'PiDown'
        self.__appdesc = '{}Search, Download over million songs from your Terminal!{}'.format(ConsoleColor.OKGREEN + ConsoleColor.BOLD, ConsoleColor.ENDC)
        self.__args = {}
        self.__pref = PiDownPref()

        # Register services
        self.__services = { module.split('.')[1]: importlib.import_module('.{}'.format(module.split('.')[0]), package=services.__package__) for module in services.__ALL__ }
        for service_name in self.__services:
            self.__services[service_name] = getattr(self.__services[service_name], service_name)()

        # handle user's arguments
        self.__arg_parser = ArgumentParser(usage=None, description=self.__appdesc)
        self.__sub_parsers = self.__arg_parser.add_subparsers(dest='subparser')
        self.__arg_parser.add_argument('-gl', '--get-link', nargs='*', help='get download links by songs urls, detect service automatically')
        self.__arg_parser.add_argument('-gp', '--get-playlist', nargs='*', help='get download links by playlists urls, detect service automatically')
        
        # list available services
        list_parser = self.__sub_parsers.add_parser('list', help='list all available services')

        # find songs
        search_parser = self.__sub_parsers.add_parser('search', help='search songs with keyword')
        search_parser.add_argument('keyword', nargs='*', help='song name, artist, album,...')
        search_parser.add_argument('-s', '--service', nargs='?', help='specific service for searching')

        # settings
        settings_parser = self.__sub_parsers.add_parser('settings', help='setup default settings')
        settings_parser.add_argument('-d', '--destination', type=str, help='default download location')

    def initial(self):
        try:
            self.__args = self.__arg_parser.parse_args()
            if self.__args.subparser == 'list':
                self.__handle_list()
            elif self.__args.subparser == 'search':
                self.__handle_search()
            elif self.__args.subparser == 'settings':
                self.__handle_settings()
            elif self.__args.get_link:
                self.__handle_get_link()
            elif self.__args.get_playlist:
                self.__handle_get_playlist()
            else:
                self.__arg_parser.print_help()
        except Exception as exception:
            print('{}{}{}'.format(
                ConsoleColor.FAIL,
                str(exception),
                ConsoleColor.ENDC
            ))
            pass
    
    def __handle_list(self):
        print('{}CURRENT AVAILABLE SERVICES:{}'.format(
            ConsoleColor.BOLD + ConsoleColor.OKBLUE,
            ConsoleColor.ENDC
        ))
        for index, service_class_name in enumerate(self.__services):
            service_meta = self.__services[service_class_name].Meta
            print('{}{}. {}: {}{}{}'.format(
                ConsoleColor.OKGREEN + ConsoleColor.BOLD,
                index + 1,
                service_meta.name,
                ConsoleColor.ENDC + ConsoleColor.OKGREEN,
                service_meta.description,
                ConsoleColor.ENDC
            ))
    
    def __handle_search(self):
        if len(self.__services) == 0:
            raise Exception('No services available, task stopped!')
        
        search_service = list(self.__services.keys())[0].lower()
        search_keyword = ' '.join(self.__args.keyword)

        if self.__args.service:
            search_service = self.__args.service.lower()
        if search_service not in [service_name.lower() for service_name in self.__services.keys()]:
            raise Exception('No service found for `{}`'.format(search_service))

        service_class = [service_item for service_item in self.__services.values() if service_item.Meta.name == search_service][0]
        search_results = service_class.search(search_keyword)
        if len(search_results):
            print('{}{}{}'.format(
                ConsoleColor.BOLD,
                '\nFound {} result{} for `{}{}{}`:'.format(
                    len(search_results),
                    's' if len(search_results) > 1 else '',
                    ConsoleColor.WARNING,
                    search_keyword,
                    ConsoleColor.ENDC
                ),
                ConsoleColor.ENDC
            ))

            # List search results then prompt user to select index
            [print('{}.\t{}'.format(index + 1, song_item)) for index, song_item in enumerate(search_results)]
            item_index = input('\n{}Select index of song to generate download links (Enter without selection to cancel):{} '.format(
                ConsoleColor.BOLD + ConsoleColor.OKBLUE,
                ConsoleColor.ENDC
            ))

            if not item_index:
                raise Exception('Cancelled by user')
            item_index = (int(item_index) if item_index.isdigit() else 1) - 1
            if item_index < 0 or item_index >= len(search_results):
                raise Exception('{}Invalid index of song!{}'.format(
                    ConsoleColor.FAIL,
                    ConsoleColor.ENDC
                ))
            
            # Confirm to user selected song
            selected_song_item = search_results[item_index]
            print('{0} -> Selected `{1}`, {0}getting links...{2}'.format(
                ConsoleColor.WARNING,
                str(selected_song_item),
                ConsoleColor.ENDC
            ))

            download_links = service_class.get_link(selected_song_item)
            if len(download_links):
                print('{}{}{}'.format(
                    ConsoleColor.BOLD,
                    '\nFound {} download link{} for `{}{}{}`:'.format(
                        len(download_links),
                        's' if len(download_links) > 1 else '',
                        ConsoleColor.WARNING,
                        search_keyword,
                        ConsoleColor.ENDC
                    ),
                    ConsoleColor.ENDC
                ))
                
                # Print list of links
                [print('{}.\t{}'.format(index + 1, link)) for index, link in enumerate(download_links)]
                item_index = input('\n{}Select index of link to download (Enter without selection to cancel):{} '.format(
                    ConsoleColor.BOLD + ConsoleColor.OKBLUE,
                    ConsoleColor.ENDC
                ))
                
                # Confirm download from user
                if not item_index:
                    raise Exception('Cancelled by user')
                item_index = (int(item_index) if item_index.isdigit() else 1) - 1
                if item_index < 0 or item_index >= len(download_links):
                    raise Exception('{}Invalid index of link!{}'.format(
                        ConsoleColor.FAIL,
                        ConsoleColor.ENDC
                    ))
                
                download_item = download_links[item_index]
                service_class.download(download_item)
            else:
                print('{}{}{}'.format(
                    ConsoleColor.WARNING,
                    '\nNo any download links for `{}{}{}`, please retry...'.format(
                        ConsoleColor.FAIL,
                        search_keyword,
                        ConsoleColor.ENDC
                    ),
                    ConsoleColor.ENDC
                ))
        else:
            print('{}{}{}'.format(
                ConsoleColor.WARNING,
                '\nNo result for `{}{}{}`...'.format(
                    ConsoleColor.FAIL,
                    search_keyword,
                    ConsoleColor.ENDC
                ),
                ConsoleColor.ENDC
            ))
    
    def __handle_settings(self):
        if self.__args.destination:
            if os.path.exists(self.__args.destination) and os.path.isdir(self.__args.destination):
                abs_path = os.path.abspath(self.__args.destination)
                self.__pref.setPref('destination', abs_path)
                print('{}All songs will be saved into `{}{}{}`.{}'.format(
                    ConsoleColor.OKGREEN,
                    ConsoleColor.BOLD,
                    abs_path,
                    ConsoleColor.ENDC + ConsoleColor.OKGREEN,
                    ConsoleColor.ENDC
                ))
            else:
                raise Exception('Destination `{}` is invalid! It must be directory and exist!'.format(self.__args.destination))
        else:
            print('{}Use `{}settings --help{}` for more information about download settings{}'.format(
                ConsoleColor.WARNING,
                ConsoleColor.BOLD,
                ConsoleColor.ENDC + ConsoleColor.WARNING,
                ConsoleColor.ENDC
            ))
        pass
    
    def __handle_get_link(self):
        for link_item in self.__args.get_link:
            link_url = urllib3.util.parse_url(link_item)
            try:
                if not link_url.hostname:
                    raise Exception('Invalid URL!')
                available_services = [service for service in self.__services.values() if link_url.hostname in service.Meta.hostnames]
                if len(available_services) == 0:
                    raise Exception('Sorry, not service found for url `{}`'.format(link_url))
                
                service_class = available_services[0]
                print('{2}Detected service `{3}{0}{4}{2}` for url `{3}{1}{4}{2}`...\nGetting link information...{4}'.format(
                    service_class.Meta.name,
                    link_url,
                    ConsoleColor.OKGREEN,
                    ConsoleColor.BOLD,
                    ConsoleColor.ENDC
                ))

                selected_song_item = service_class.get_song_item(str(link_url))
                if not selected_song_item:
                    raise Exception('Sorry, cannot get song information. May be link is incorrect or not found!')

                selected_song_item.url = str(link_url)
                download_links = service_class.get_link(selected_song_item)
                if len(download_links):
                    print('{}{}{}'.format(
                        ConsoleColor.BOLD,
                        '\nFound {} download link{} for `{}{}{}`:'.format(
                            len(download_links),
                            's' if len(download_links) > 1 else '',
                            ConsoleColor.WARNING,
                            selected_song_item.title,
                            ConsoleColor.ENDC
                        ),
                        ConsoleColor.ENDC
                    ))
                    
                    # Print list of links
                    [print('{}.\t{}'.format(index + 1, link)) for index, link in enumerate(download_links)]
                    item_index = input('\n{}Select index of link to download (Enter without selection to cancel):{} '.format(
                        ConsoleColor.BOLD + ConsoleColor.OKBLUE,
                        ConsoleColor.ENDC
                    ))
                    
                    # Confirm download from user
                    if not item_index:
                        raise Exception('Cancelled by user')
                    item_index = (int(item_index) if item_index.isdigit() else 1) - 1
                    if item_index < 0 or item_index >= len(download_links):
                        raise Exception('{}Invalid index of link!{}'.format(
                            ConsoleColor.FAIL,
                            ConsoleColor.ENDC
                        ))
                    
                    download_item = download_links[item_index]
                    service_class.download(download_item)
                else:
                    print('{}{}{}'.format(
                        ConsoleColor.WARNING,
                        '\nNo any download links for `{}{}{}`, please retry...'.format(
                            ConsoleColor.FAIL,
                            link_url,
                            ConsoleColor.ENDC
                        ),
                        ConsoleColor.ENDC
                    ))
            except Exception as exception:
                print('{}{}{}'.format(
                    ConsoleColor.FAIL,
                    str(exception),
                    ConsoleColor.ENDC
                ))
                pass

    def __handle_get_playlist(self):
        for link_item in self.__args.get_playlist:
            link_url = urllib3.util.parse_url(link_item)
            try:
                if not link_url.hostname:
                    raise Exception('Invalid URL!')
                available_services = [service for service in self.__services.values() if link_url.hostname in service.Meta.hostnames]
                if len(available_services) == 0:
                    raise Exception('Sorry, not service found for url `{}`'.format(link_url))
                
                service_class = available_services[0]
                print('{2}Detected service `{3}{0}{4}{2}` for url `{3}{1}{4}{2}`...\nGetting link information...{4}'.format(
                    service_class.Meta.name,
                    link_url,
                    ConsoleColor.OKGREEN,
                    ConsoleColor.BOLD,
                    ConsoleColor.ENDC
                ))

                song_items = service_class.get_song_items_from_playlist(str(link_url))
                if len(song_items) == 0:
                    raise Exception('No songs inside playlist, may be playlist url is not found!')
                
                print('\n{}Songs list:{}'.format(ConsoleColor.BOLD, ConsoleColor.ENDC))
                [print('{}{}.\t{}'.format(ConsoleColor.OKGREEN, index + 1, song_item)) for index, song_item in enumerate(song_items)]

                user_confirm = input('{}Confirm get download links? [Y/n]: {}'.format(
                    ConsoleColor.BOLD,
                    ConsoleColor.ENDC
                ))
                if user_confirm and user_confirm.lower() == 'n':
                    raise Exception('Cancelled by user')
                self.__args.get_link = [song_item.url for song_item in song_items]
                self.__handle_get_link()
            except Exception as exception:
                print('{}{}{}'.format(
                    ConsoleColor.FAIL,
                    str(exception),
                    ConsoleColor.ENDC
                ))
                pass