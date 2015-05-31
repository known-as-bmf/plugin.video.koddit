import sys
import operator
import requests


base_url = 'http://www.reddit.com/'
sub_part = '/r/{sub}/hot.json'

youtube_domains = ['youtube.com', 'youtu.be', 'm.youtube.com']
params = {'limit': 29}
headers = {'user-agent': 'testapp/0.1'}
N = 1


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
  total_count = (params['limit'] + 1) * N
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
        domains[domain] = domains[domain] + 1
      else:
        domains[domain] = 1
      if domain in youtube_domains:
        if item['data']['media'] is not None and 'playlist' not in item['data']['url']:
          #print 'given : ' + item['data']['media']['oembed']['thumbnail_url']
          print 'found : ' + youtube_thumb_url(item['data']['media']['oembed']['url'])
      actual_count = actual_count + 1
    after = data['data']['after']

  print '{n} items actually recieved.'.format(n=actual_count)
  print 'For sub {sub}, domains are :'.format(sub=sub)
  for k, v in sorted(domains.items(), key=lambda x: x[1], reverse=True):
    print k + ' -> ' + str(v) + ' (' + str(((v * 100) + 0.0) / actual_count) + '%)'


def youtube_thumb_url(video_url, size='normal'):
  thumb_url = 'http://i3.ytimg.com/vi/{id}/{size}.jpg'
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
  r = requests.get(url, headers=headers)
  if r.status_code != 404:
    return url
  return thumb_url.format(id=vid, size=size_map['small'])


if __name__ == '__main__':
    main()