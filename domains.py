# -*- coding: utf-8 -*-
import sys
import requests
from urlparse import parse_qsl, urlparse
import HTMLParser


base_url = 'http://www.reddit.com/'
sub_part = '/r/{sub}/hot.json'

youtube_domains = ['youtube.com', 'youtu.be', 'm.youtube.com']
vimeo_domains = ['vimeo.com']
params = {'limit': 30}
headers = {'user-agent': 'testapp/0.1'}
N = 10

#html_parser = HTMLParser.HTMLParser()


class ParsingException(Exception):
    pass


class VideoItem(object):
    __html_parser = HTMLParser.HTMLParser()

    def __init__(self, data):
        self._data = data
        self._url = None
        self._parsed_url = None
        self._parsed_qs = None

    def _get_url(self):
        if not self._url:
            self._url = self._get_media('url') or self._data['data']['url']
        return self._url

    def _in_media(self, field):
        return self._data['data']['media'] and field in self._data['data']['media']['oembed']

    def _get_media(self, field):
        return self._data['data']['media']['oembed'][field] if self._in_media(field) else None

    def _get_parsed_url(self):
        if not self._parsed_url:
            self._parsed_url = urlparse(self.__html_parser.unescape(self._get_url()))
        return self._parsed_url

    def _get_parsed_qs(self):
        if not self._parsed_url:
            self._parsed_qs = dict(parse_qsl(self._get_parsed_url().query, keep_blank_values=True))
        return self._parsed_qs

    def get_plugin_url(self): raise NotImplementedError

    def get_thumbnail_url(self): raise NotImplementedError

    def build_item(self):
        title = self._get_media('title') or self._data['data']['title']
        desc = u'Score : {score} | Author : {author}\n{reddit_title}\n{desc}'
        desc = desc.format(score=str(self._data['data']['score']),
                           author=self._data['data']['author'],
                           reddit_title=self._data['data']['title'],
                           desc=self._get_media('description') or '')
        thumb = self.get_thumbnail_url()
        path = self.get_plugin_url()

        return {
            'label': title,
            'path': path,
            'thumbnail': thumb,
            'is_playable': True,
            'info_type': 'video',
            'info': {
                'label': title,
                'title': title,
                'plot': desc,
            },
            'properties': {
                'fanart_image': thumb,
            }
        }


class YoutubeItem(VideoItem):
    __base_plugin_url = 'plugin://plugin.video.youtube/play/?'
    __vid_plugin_qs = 'video_id={vid}'
    __pl_plugin_qs = 'playlist_id={pid}'

    def _get_url(self):
        # Youtube specific handling for playlists
        # reddit cleans up the data.media.oembed.url, urls which is good
        # but they also remove playlist info. We want to keep them
        if not self._url:
            self._url = self._data['data']['url']
            if 'list=' not in self._url:
                media_url = self._get_media('url')
                if media_url:
                    self._url = media_url
        return self._url

    def _get_parsed_qs(self):
        # handling attribution links
        if 'u' in super(YoutubeItem, self)._get_parsed_qs():
            self._parsed_qs = dict(parse_qsl(urlparse(self._parsed_qs['u']).query, keep_blank_values=True))
        return self._parsed_qs

    def get_plugin_url(self):
        parsed_query = self._get_parsed_qs()
        qs = []
        if 'list' in parsed_query and parsed_query['list']:
            qs.append(self.__pl_plugin_qs.format(pid=parsed_query['list']))
        if 'v' in parsed_query:
            qs.append(self.__vid_plugin_qs.format(vid=parsed_query['v']))
        if len(qs) < 1:
            # reddit sometimes handle youtu.be weirdly
            if 'youtu.be' in self._get_parsed_url().hostname:
                # verifier si youtu.be ne peux pas contenir une playlist
                qs.append(self.__vid_plugin_qs.format(vid=self._get_url().split('/')[-1]))
            else:
                raise ParsingException('Unable tu handle URL ' + self._get_url())
        return self.__base_plugin_url + '&'.join(qs)

    def get_thumbnail_url(self):
        return self._get_media('thumbnail_url')

    # not used because it takes a lot of time to HEAD for each item (since this is not async)
    def get_best_thumb_url(self):
        thumb_url = 'http://i3.ytimg.com/vi/{id}/{size}.jpg'
        size_map = {'large': 'maxresdefault', 'normal': 'sddefault', 'small': 'hqdefault'}
        # we have to do this because python orders dict as it goddamn pleases
        # size_list = ['large', 'normal']
        # for s in size_list[size_list.index(size):]:
        #    url = thumb_url.format(id=vid, size=size_map[s])
        #    r = requests.head(url, headers=headers)
        #    if r.status_code != 404:
        #        return url
        parsed_query = self._get_parsed_qs()
        if 'v' in parsed_query:
            url = thumb_url.format(id=parsed_query['v'], size=size_map['large'])
            r = requests.head(url, headers=headers)
            if r.status_code != 404:
                return url
            return thumb_url.format(id=parsed_query['v'], size=size_map['small'])
        else:
            return self.get_thumbnail_url()


class VimeoItem(VideoItem):
    __base_plugin_url = 'plugin://plugin.video.vimeo/play/?'
    __vid_plugin_qs = 'video_id={vid}'

    def get_plugin_url(self):
        vid = self._get_url().split('/')[-1]
        return self.__base_plugin_url + self.__vid_plugin_qs.format(vid=vid)

    def get_thumbnail_url(self):
        return self._get_media('thumbnail_url')


def main():
    if len(sys.argv) < 2:
        sys.exit('You must specify a subreddit name. Aborting.')
    sub = sys.argv[1]

    full_url = base_url + sub_part.format(sub=sub)
    print 'Checking existence of sub...'
    r = requests.head(full_url, headers=headers)
    if r.status_code == 302:
        sys.exit('Sub does not exist. Aborting.')
    if r.status_code == 403:
        sys.exit('Sub is private. Aborting.')

    print 'Starting domain analysis...'
    total_count = (params['limit']) * N
    actual_count = 0
    print 'Querying {n} items...'.format(n=total_count)

    after = None
    domains = {}
    for i in xrange(N):
        payload = params
        if after:
            payload['after'] = after
        r = requests.get(full_url, params=payload, headers=headers)
        data = r.json()
        for item in data['data']['children']:
            domain = item['data']['domain']
            if domain in domains:
                domains[domain] += 1
            else:
                domains[domain] = 1
            try:
                if domain in youtube_domains:
                    print YoutubeItem(item).build_item()['path']
                    # YoutubeItem(item).build_item()
                elif domain in vimeo_domains:
                    print VimeoItem(item).build_item()['path']
                    # VimeoItem(item).build_item()
            except ParsingException as ex:
                print ex
            actual_count += 1
        after = data['data']['after']

    print '{n} items actually recieved.'.format(n=actual_count)
    print 'For sub {sub}, domains are :'.format(sub=sub)
    for k, v in sorted(domains.items(), key=lambda x: x[1], reverse=True):
        print k + ' -> ' + str(v) + ' (' + str(((v * 100) + 0.0) / actual_count) + '%)'


if __name__ == '__main__':
    main()
