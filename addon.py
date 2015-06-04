#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2015 known-as-bmf
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

from xbmcswift2 import Plugin
from xbmcswift2 import actions
import requests
from urlparse import parse_qsl, urlparse
import HTMLParser
import xbmc
import xbmcgui


plugin = Plugin()

storage = plugin.get_storage('KodditStorage', file_format='json')
if 'subreddits' not in storage:
    storage['subreddits'] = []

base_url = 'http://www.reddit.com'
sub_json = base_url + '/r/{sub}/{cat}.json'

categories = [('new',   30001),
              ('hot',   30002),
              ('top_h', 30003),
              ('top_d', 30004),
              ('top_w', 30005),
              ('top_m', 30006),
              ('top_y', 30007),
              ('top_a', 30008)]

headers = {'user-agent': plugin.name + '/' + plugin.addon.getAddonInfo('version')}
default_params = {'limit': 30}

youtube_domains = ['youtube.com', 'youtu.be', 'm.youtube.com']
vimeo_domains = ['vimeo.com']
known_domains = youtube_domains + vimeo_domains
video_sub_threshold = 0.65


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

    def get_plugin_url(self):
        raise NotImplementedError

    def get_thumbnail_url(self):
        raise NotImplementedError

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


@plugin.route('/')
def index():
    items = [{
        'label': sub,
        'path': plugin.url_for('show_sub', sub=sub),

        'context_menu': [
            (plugin.get_string(30020), actions.background(plugin.url_for('del_sub', sub=sub)))
        ]
    } for sub in storage['subreddits']]
    items.append({
        'label': plugin.get_string(30009),
        'path': plugin.url_for('add_sub')
    })
    return items


@plugin.route('/add_sub', name='add_sub')
def add_sub():
    input = plugin.keyboard('', plugin.get_string(30009))
    # you can input multiple subreddit names at once separated by a +
    input_subs = input.split('+')
    # inexistant subs (http code 302) or private subs (http code 403)
    excluded_subs = {}
    # probably not video subs
    questionable_subs = []
    # to memorize the correctly cased name of the subs (this is purely aesthetic)
    correct_names = {}
    for subreddit in input_subs:
        if subreddit:
            if subreddit.lower() not in [sub.lower() for sub in storage['subreddits']]:
                url = sub_json.format(sub=subreddit, cat='hot')
                r = requests.head(url, headers=headers)
                # 302 = sub does not exist | 403 = sub is private
                if r.status_code == 302 or r.status_code == 403:
                    excluded_subs[subreddit] = r.status_code

                    #dialog = xbmcgui.Dialog()
                    #dialog.ok('Error', 'This subreddit does not exist or is private.')
                else:
                    #save = True

                    data = load_json(url, {'limit': 100})

                    correct_names[subreddit] = data['data']['children'][0]['data']['subreddit']
                    total_count = 0.0
                    video_count = 0.0
                    for item in data['data']['children']:
                        if item['data']['domain'] in known_domains:
                            video_count += 1
                        total_count += 1
                    if video_count / total_count < video_sub_threshold:
                        questionable_subs.append(subreddit)
                        #dialog = xbmcgui.Dialog()
                        #save = dialog.yesno('Warning',
                        #                    '/r/{sub} may not be a video subreddit.'.format(sub=subreddit),
                        #                    'Add it anyway ?')
                    #if save:
                    #    storage['subreddits'].append(subreddit)
    if len(excluded_subs) > 0:
        for sub, _ in excluded_subs.iteritems():
            input_subs.remove(sub)
        nf = ', '.join([not_found for not_found, code in excluded_subs.iteritems() if code == 302])
        p = ', '.join([private for private, code in excluded_subs.iteritems() if code == 403])
        dialog = xbmcgui.Dialog()
        dialog.ok('Error', 'Some subs couldn\'t be added:',
                           nf + ' were not found.',
                           p + ' are private.')
    if len(questionable_subs) > 0:
        for sub in questionable_subs:
            dialog = xbmcgui.Dialog()
            save = dialog.yesno('Warning',
                                '/r/{sub} may not be a video subreddit.'.format(sub=correct_names[sub]),
                                'Add it anyway ?')
            if not save:
                input_subs.remove(sub)
    if len(input_subs) > 0:
        storage['subreddits'].append('+'.join([correct_names[name] for name in input_subs]))
        xbmc.executebuiltin("Container.Refresh")

@plugin.route('/del_sub/<sub>', name='del_sub')
def del_sub(sub):
    storage['subreddits'].remove(sub)
    xbmc.executebuiltin("Container.Refresh")


@plugin.route('/show_sub/<sub>', name='show_sub')
def show_sub(sub):
    return [{
        'label': plugin.get_string(value),
        'path': plugin.url_for('show_' + key, sub=sub, after='start')
    } for key, value in categories]


@plugin.route('/show_new/<sub>/<after>',
              name='show_new', options={'cat': 'new'})
@plugin.route('/show_hot/<sub>/<after>',
              name='show_hot', options={'cat': 'hot'})
@plugin.route('/show_top_h/<sub>/<after>',
              name='show_top_h', options={'cat': 'top', 'params': {'t': 'hour'}})
@plugin.route('/show_top_d/<sub>/<after>',
              name='show_top_d', options={'cat': 'top', 'params': {'t': 'day'}})
@plugin.route('/show_top_w/<sub>/<after>',
              name='show_top_w', options={'cat': 'top', 'params': {'t': 'week'}})
@plugin.route('/show_top_m/<sub>/<after>',
              name='show_top_m', options={'cat': 'top', 'params': {'t': 'month'}})
@plugin.route('/show_top_y/<sub>/<after>',
              name='show_top_y', options={'cat': 'top', 'params': {'t': 'year'}})
@plugin.route('/show_top_a/<sub>/<after>',
              name='show_top_a', options={'cat': 'top', 'params': {'t': 'all'}})
def show_cat(sub, cat, after='start', params=None):
    plugin.set_content('tvshows')
    url = sub_json.format(sub=sub, cat=cat)
    # python magic to concatenate 2 dicts
    payload = dict(default_params, **params) if params else dict(default_params)
    if after != 'start':
        payload['after'] = after

    data = load_json(url, payload)

    items = []
    for video in data['data']['children']:
        if video['data']['media']:
            if video['data']['domain'] in youtube_domains:
                items.append(YoutubeItem(video).build_item())
            elif video['data']['domain'] in vimeo_domains:
                items.append(VimeoItem(video).build_item())
    if data['data']['after']:
        items.append({
            'label': plugin.get_string(30010),
            'path': plugin.url_for(plugin.request.path.split('/')[1], sub=sub, after=data['data']['after'])
        })
    return plugin.finish(items)


# payload :
#   after   fullname of a thing
#   before  fullname of a thing
#   count   a positive integer (default: 0)
#   include_facets  boolean value
#   limit   the maximum number of items desired (default: 25, maximum: 100)
#   q   a string no longer than 512 characters
#   restrict_sr boolean value
#   show    (optional) the string all
#   sort    one of (relevance, hot, top, new, comments)
#   sr_detail   (optional) expand subreddits
#   syntax  one of (cloudsearch, lucene, plain)
#   t   one of (hour, day, week, month, year, all)
def load_json(url, params=None):
    r = requests.get(url, params=params, headers=headers)
    return r.json()


if __name__ == '__main__':
    plugin.run()
