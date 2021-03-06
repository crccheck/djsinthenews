"""
Usage:
  python main.py [send]
  python main.py only-send

Options:

  send       send a tweet (requires Twitter auth credentials)
  only-send  send a tweet and don't look for headlines. Useful for cron jobs.
"""
from __future__ import unicode_literals

from hashlib import md5
import logging
import re
import sys

from lxml.html import document_fromstring
from project_runpy import env
import project_runpy
import redis
import requests
import tweepy


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not len(logger.handlers):
    # keep me from repeatedly adding this handler in ipython
    logger.addHandler(project_runpy.ColorizingStreamHandler())


# copied from https://github.com/crccheck/dj.js/blob/master/Source/content_script.js
DJ_SEARCH = re.compile(r'\b([Aa]uthor|[Dd]octor|[Ee]xpert|[Ff]armer|[Ll]awyer|[Mm]ayor|[Pp]resident|[Ss]cientist|[Ss]enator|[Vv]eteran|Pope)(|s)\b')
EXPIRES = 3600 * 24 * 7  # remember things for a week
QUEUE_KEY = 'tweets'


def build_headlines(url='https://news.google.com/'):
    # with open('index.html') as f:
    #     doc = document_fromstring(f.read())
    page = requests.get(url, headers={
        'User-Agent': 'djs-everywhere/0.0.0 (c@crccheck.com)',
    })
    if not page.ok:
        print page
        logger.warning("That's not good")
        raise Exception('TODO page did not load error')
    doc = document_fromstring(page.content)
    headlines = {}
    for headline in doc.xpath('//a/span[@class="titletext"]'):
        # lxml returns byte string
        key = unicode(headline.text_content().strip())
        # WISHLIST strip google news get params
        # * ?google_editors_picks=true
        url = headline.getparent().attrib['href']
        headlines[key] = url
    return headlines


def get_tweet_text(mc):
    text = mc.generateString()
    for __ in range(10):  # only try 10 times
        # TODO yeah, this logic is stupid. I know.
        is_valid = True
        if text[0] == u'-':
            logger.warn('Starts with a hyphen: {}'.format(text))
            is_valid = False
        elif not re.search(r'\w', text):
            logger.warn('Not a real tweet: {}'.format(text))
            is_valid = False
        elif len(text) > 140:
            logger.warn(u'Too Long: {}'.format(text))
            is_valid = False
        if not is_valid:
            text = mc.generateString()
    # FIXME if it can't find one, it'll return one too long anyways :(
    return text


def send_tweet(text):
    auth = tweepy.OAuthHandler(
        env.get('CONSUMER_KEY'), env.get('CONSUMER_SECRET'))
    auth.set_access_token(
        env.get('ACCESS_KEY'), env.get('ACCESS_SECRET'))
    api = tweepy.API(auth)
    api.update_status(text)
    logger.info(u'Sent: {} ({})'.format(text.encode('ascii', errors='ignore'), len(text)))


def queue(rdb, text):
    """Queue the text to tweet out."""
    print 'Queueing: {}'.format(text)
    rdb.rpush(QUEUE_KEY, text)


def send(rdb):
    """Send a tweet from the queue."""
    n_queue = rdb.llen(QUEUE_KEY)
    if n_queue:
        text = rdb.lpop(QUEUE_KEY)
        try:
            send_tweet(text)
        except tweepy.TweepError:
            # code 226 - this request looks like it might be automated
            rdb.lpush(text)
        print 'Tweets in the queue: {}'.format(n_queue - 1)


def do_something():
    headlines = build_headlines()
    maybe_better_headlines = {}

    r_url = env.require('REDISCLOUD_URL')
    rdb = redis.StrictRedis.from_url(r_url)

    for text, url in headlines.items():
        new_text, count = DJ_SEARCH.subn('DJ\\2', text)
        if count:
            maybe_better_headlines[new_text] = url

    # see which of these headlines are new
    possible_tweets = []
    for text, url in maybe_better_headlines.items():
        key = 'headline:{}'.format(md5(text.encode('utf8')).hexdigest())
        if not rdb.get(key):
            possible_tweets.append('{} {}'.format(text, url))
            rdb.set(key, url)
            rdb.expire(key, EXPIRES)

    # have a human pick a tweet
    if possible_tweets:
        print 'Which headlines are worth tweeting?'
        print '-' * 80
        for idx, text in enumerate(possible_tweets, start=1):
            print '\t', idx, text
        print '-' * 80
        while True:
            out = raw_input('> (return to exit) ')
            if out:
                try:
                    queue(rdb, possible_tweets[int(out) - 1])
                except (IndexError, ValueError):
                    out = 'foo'
            else:
                break

    if 'send' in sys.argv[1:]:
        try:
            send(rdb)
        except tweepy.TweepError as e:
            # TODO figure out error code, need json?
            import ipdb; ipdb.set_trace()

    # DELETEME below, just for debuggin
    print 'queue:'
    from pprint import pprint
    pprint(list(rdb.lrange(QUEUE_KEY, 0, -1)))  # DELETEME


def only_send():
    """Hack to give a way to only send from the queue"""
    r_url = env.require('REDISCLOUD_URL')
    rdb = redis.StrictRedis.from_url(r_url)
    send(rdb)


if __name__ == '__main__':
    if 'only-send' in sys.argv[1:]:
        only_send()
    else:
        do_something()
