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
import xbmc
import xbmcgui
import os
import json
import urllib
import urllib2


plugin = Plugin()

storage = plugin.get_storage('KodditStorage', file_format='json')
try:
    len(storage['subreddits'])
except:
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
vimeo_domains   = ['vimeo.com']
known_domains   = youtube_domains + vimeo_domains
video_sub_threshold = 0.65


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
    keyboard = xbmc.Keyboard('', plugin.get_string(30009))
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():
        subreddit = keyboard.getText()
        if subreddit.lower() not in [sub.lower() for sub in storage['subreddits']]:
            test_url = sub_json.format(sub=subreddit, cat='hot')
            r = requests.head(test_url, headers=headers)
            # 302 = sub does not exist | 403 = sub is private
            if r.status_code == 302 or r.status_code == 403:
                dialog = xbmcgui.Dialog()
                dialog.ok('Error', 'This subreddit does not exist or is private.')
            else:
                save = True
                r = requests.get(test_url, params={'limit': 100}, headers=headers)
                data = r.json()

                subreddit = data['data']['children'][0]['data']['subreddit']
                total_count = 0.0
                video_count = 0.0
                for item in data['data']['children']:
                    if item['data']['domain'] in known_domains:
                        video_count = video_count + 1
                    total_count = total_count + 1
                if video_count / total_count < video_sub_threshold:
                    dialog = xbmcgui.Dialog()
                    save = dialog.yesno('Warning',
                                        'It appears /r/{sub} may not be a video subreddit.'.format(sub=subreddit),
                                        'Add it anyway ?')
                if save:
                    storage['subreddits'].append(subreddit)


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
def show_cat(sub, cat, after='start', params={}):
    plugin.set_content('tvshows')
    url = sub_json.format(sub=sub, cat=cat)
    # python magic to concatenate 2 dicts
    payload = dict(default_params, **params);
    if after != 'start':
        payload['after'] = after

    r = requests.get(url, params=payload, headers=headers)
    data = r.json()

    items = []
    for video in data['data']['children']:
        if video['data']['domain'] in youtube_domains:
            if video['data']['media'] and 'playlist' not in video['data']['url']:
                items.append(create_item(video, youtube_plugin_url, youtube_thumb_url))
    if data['data']['after']:
        items.append({
            'label': plugin.get_string(30010),
            'path': plugin.url_for(plugin.request.path.split('/')[1], sub=sub, after=data['data']['after'])
        })
    return plugin.finish(items)

# path_func = function (url) that returns internal url to play media
# thumb_func = function(url, size=normal) that return the thumbnail url for specified item
def create_item(video, path_func, thumb_func):
    #thumb_url = thumb_func(video['data']['media']['oembed']['url'], 'large')
    thumb_url = video['data']['media']['oembed']['thumbnail_url']
    title = video['data']['media']['oembed']['title']
    desc = u'Score : {score} | {reddit_title}\n{desc}'
    desc = desc.format(score=str(video['data']['score']),
                       reddit_title=video['data']['title'],
                       desc=video['data']['media']['oembed']['description'])
    return {
        'label': title,
        'path': path_func(video['data']['media']['oembed']['url']),
        'thumbnail': thumb_url,
        'is_playable': True,
        'info_type': 'video',
        'info': {
            'label': title,
            'title': title,
            'plot': desc,
        },
        'properties': {
            'fanart_image': thumb_url,
        },
        #'context_menu': [
        #    (plugin.get_string(30021), actions.background(plugin.url_for('download', id=str(video['em'])))),
        #],
    }


def youtube_plugin_url(video_url):
    vid = video_url.split('=')[1]
    return 'plugin://plugin.video.youtube/play/?video_id=' + vid


def youtube_thumb_url(video_url, size='normal'):
    thumb_url = 'http://i3.ytimg.com//vi/{id}/{size}.jpg'
    size_map = {'large': 'maxresdefault', 'normal': 'sddefault', 'small': 'hqdefault'}
    # we have to do this because python orders dict as it goddamn pleases
    #size_list = ['large', 'normal']
    vid = video_url.split('=')[1]
    #for s in size_list[size_list.index(size):]:
    #    url = thumb_url.format(id=vid, size=size_map[s])
    #    r = requests.head(url, headers=headers)
    #    if r.status_code != 404:
    #        return url
    url = thumb_url.format(id=vid, size=size_map['large'])
    r = requests.head(url, headers=headers)
    if r.status_code != 404:
        return url
    return thumb_url.format(id=vid, size=size_map['small'])


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

if __name__ == '__main__':
    plugin.run()
