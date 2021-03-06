#!/usr/bin/python


import datetime
import os
import re
import readline
import time

import twitter_client as tc
import twitter_client.service


# TODO Load from file
BLACKLIST_AUTHOR_NAME = ['freelancejobz', 'culinaryprep', 'wahm_job_leads', 'arkansasBNN', 'fark', 'JustinRyan', 'JustinBot', 'Web_Design_Jobs', 'eBillme_offer', 'adviseme', 'tweetscreen']


def unescape(s):
  s = s.replace("&lt;", "<")
  s = s.replace("&gt;", ">")
  s = s.replace("&quot;", '"')
  s = s.replace("&amp;", "&")
  return s


username_re = re.compile('([^ ]+) .*')
link_re = re.compile('(.*?)<a href="(.*?)">(.*?)</a>(.*)', re.DOTALL)


def cleanup_links(s):
  m = link_re.match(s)
  while m:
    if m.group(2) == str(m.group(3)).replace('<b>', '').replace('</b>', '') or \
        m.group(2).find(m.group(3)) >= 0:
      s = "%s\033[1:33m%s\033[0m%s" % (m.group(1), m.group(2), m.group(4))
    else:
      if m.group(2)[0] == '/':
        # A hashtag has uri /search?q=%23... 
        s = "%s\033[1:32m%s\033[0m%s" % (m.group(1), m.group(3), m.group(4))
      else:
        s = "%s%s[\033[1:34m%s\033[0m]%s" % (m.group(1), m.group(3), m.group(2), m.group(4))
    m = link_re.match(s)
  return s


histfile = os.path.join(os.environ['HOME'], '.tthist')
try:
    readline.read_history_file(histfile)
except IOError:
    pass
import atexit
atexit.register(readline.write_history_file, histfile)
del os, histfile

query =  raw_input('Please input query: ')

client = twitter_client.service.TwitterService(application_name='TwitterClientSampleTracker/0')
search = client.NewSearch()
# TODO Use _ParseQueryString
search.keywords = query.split(' ')
search.show_user = True
search.rpp = 30

print
print 'Tracking...'

feed = search.Search()
try:
  while True:
    if feed:
      if feed.entry:
        feed.entry.reverse()
        print
      for entry in feed.entry:
#        print entry.author[0].name.text
        if username_re.match(entry.author[0].name.text).group(1) in BLACKLIST_AUTHOR_NAME:
          continue
#        if not entry.published:
#          print entry
#          continue
#        print entry.published.text + ':', #entry.title.text
        print entry.updated.text + ':', #entry.title.text
        print cleanup_links(unescape(entry.content.text)).replace('<b>', '\033[1;31m').replace('</b>', '\033[0m').replace('\n', ' ')
        time.sleep(0.1)
      time.sleep(60)
      feed = search.Refresh()
    else:
      print datetime.datetime.now(), "Unable to get feed."
      time.sleep(60)
      feed = search.Search()
except KeyboardInterrupt:
  print
  print
  print "Seems that you have read enough, bye!"
  print
