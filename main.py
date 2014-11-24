"""
Usage:
  python main.py URL [send]

Options:

  URL   some url, like http://example.com
  send  send a tweet (requires Twitter Oauth credentials)
"""
from __future__ import unicode_literals

from os import environ as env
import logging
import re
import sys

from lxml.html import document_fromstring
import project_runpy
import requests
import tweepy


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not len(logger.handlers):
    # keep me from repeatedly adding this handler in ipython
    logger.addHandler(project_runpy.ColorizingStreamHandler())


def build_headlines(url='https://news.google.com/'):
    page = requests.get(url, headers={
        'User-Agent': 'djs-everywhere/0.0.0 (c@crccheck.com)',
    })
    doc = document_fromstring(page.content)
    headlines = [x.text_content().strip() for x in
        doc.xpath('//span[@class="titletext"]')]
    return set(headlines)  # make sure they're unique


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
    logger.info(u'Sent: {}'.format(text))


def do_something():
    build_headlines()
    # cleaned = list(clean_comments(comments))

    # if len(cleaned) < 20:
    #     # if we don't have enough comments, leave
    #     logger.error('Not enough comments on {}, only got {} ({}), needed 20'
    #         .format(host, len(cleaned), len(comments)))
    #     return

    # mc = MarkovChain('/tmp/temp.db')
    # mc.db = {}  # HACK to clear any existing data, we want to stay fresh
    # mc.generateDatabase(
    #     # seems silly to join and then immediately split, but oh well
    #     '\n'.join(cleaned),
    #     sentenceSep='[\n]',
    # )
    # if 'send' in sys.argv:
    #     send_tweet(get_tweet_text(mc))
    # else:
    #     print get_tweet_text(mc)
    #     # put stuff in global for debugging
    #     globals().update({
    #         'mc': mc,
    #         'comments': comments,
    #         'cleaned': cleaned,
    #         'host': host,
    #     })


if __name__ == '__main__':
    do_something()
