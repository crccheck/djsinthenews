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


# copied from https://github.com/crccheck/dj.js/blob/master/Source/content_script.js
DJ_SEARCH = re.compile(r'\b([Aa]uthor|[Dd]octor|[Ee]xpert|[Ff]armer|[Ll]awyer|[Mm]ayor|[Pp]resident|[Ss]cientist|[Ss]enator|[Vv]eteran|Pope)(|s)\b')


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
    headlines = build_headlines()
    maybe_better_headlines = []
    for text in headlines:
        new_text, count = DJ_SEARCH.subn('DJ\\2', text)
        print count, new_text
        if count:
            maybe_better_headlines.append(new_text)
    print maybe_better_headlines


if __name__ == '__main__':
    do_something()
