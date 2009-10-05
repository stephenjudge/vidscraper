import datetime
import math
import re

import feedparser
import simplejson

from vidscraper.util import open_url_while_lying_about_agent

USERNAME_RE = re.compile('http://vimeo\.com/(\w+)/')

_cached_video_count = {}

def video_count(parsed_feed):
    if parsed_feed.feed.get('generator') != 'The Vimeo':
        return None
    username = USERNAME_RE.search(parsed_feed.feed.link).group(1)
    json_data = simplejson.load(open_url_while_lying_about_agent(
            'http://vimeo.com/api/v2/%s/info.json' % username))
    _cached_video_count[parsed_feed.feed.link] = count = \
        json_data['total_videos_uploaded']
    return count


def bulk_import(parsed_feed):
    username = USERNAME_RE.search(parsed_feed.feed.link).group(1)
    count = _cached_video_count[parsed_feed.feed.link]
    post_url = 'http://vimeo.com/api/v2/%s/videos.json?page=%%i' % username
    parsed_feed = feedparser.FeedParserDict(parsed_feed.copy())
    parsed_feed.entries = []
    for i in range(1, int(math.ceil(count / 20.0)) + 1):
        json_data = simplejson.load(open_url_while_lying_about_agent(
                post_url % i))
        for video in json_data:
            parsed_feed.entries.append(feedparser_dict(
                    _json_to_feedparser(video)))

    # clean up cache
    if parsed_feed.feed.link in _cached_video_count:
        del _cached_video_count[parsed_feed.feed.link]

    return parsed_feed

def feedparser_dict(obj):
    if isinstance(obj, dict):
        return feedparser.FeedParserDict(dict(
                [(key, feedparser_dict(value))
                 for (key, value) in obj.items()]))
    if isinstance(obj, (list, tuple)):
        return [feedparser_dict(member) for member in obj]
    return obj

def safe_decode(str_or_unicode):
    if isinstance(str_or_unicode, unicode):
        return str_or_unicode
    else:
        return str_or_unicode.decode('utf8')

def _json_to_feedparser(json):
    upload_date = datetime.datetime.strptime(
        json['upload_date'],
        '%Y-%m-%d %H:%M:%S')
    tags = [{'label': u'Tags',
             'scheme': None,
             'term': safe_decode(json['tags'])}]
    tags.extend({'label': None,
                 'scheme': u'http://vimeo/tag:%s' % tag,
                 'term': tag}
                for tag in safe_decode(json['tags']).split(', '))
    return {
        'author': safe_decode(json['user_name']),
        'enclosures': [
            {'href': u'http://vimeo.com/moogaloop.swf?clip_id=%s' % json['id'],
             'type': u'application/x-shockwave-flash'},
            {'thumbnail': {'width': u'200', 'height': u'150',
                           'url': safe_decode(json['thumbnail_medium']),
                           }}],
        'guidislink': False,
        'id': safe_decode(upload_date.strftime(
                'tag:vimeo,%%Y-%%m-%%d:clip%s' % json['id'])),
        'link': safe_decode(json['url']),
        'links': [{'href': safe_decode(json['url']),
                   'rel': 'alternate',
                   'type': 'text/html'}],
        'media:thumbnail': u'',
        'media_credit': safe_decode(json['user_name']),
        'media_player': u'',
        'summary': (u'<p><a href="%(url)s" title="%(title)s">'
                    u'<img src="%(thumbnail_medium)s" alt="%(title)s" /></a>'
                    u'</p><p>%(description)s</p>' % json),
        'summary_detail': {
            'base': u'%s/videos/rss' % safe_decode(json['user_url']),
            'language': None,
            'type': 'text/html',
            'value': (u'<p><a href="%(url)s" title="%(title)s">'
                      u'<img src="%(thumbnail_medium)s" alt="%(title)s" /></a>'
                      u'</p><p>%(description)s</p>' % json),
            },
        'tags': tags,
        'title': safe_decode(json['title']),
        'title_detail': {
            'base': u'%s/videos/rss' % safe_decode(json['user_url']),
            'language': None,
            'type': 'text/plain',
            'value': safe_decode(json['title'])},
        'updated': safe_decode(
            upload_date.strftime('%a, %d %b %Y %H:%M:%S %z')),
        'updated_parsed': upload_date.timetuple()}