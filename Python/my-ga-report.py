#!/usr/bin/env python
# Copyright (c) 2011-2013 Yu-Jie Lin
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import datetime as dt
import sys
from itertools import chain, groupby

import gdata.analytics.client
import pytz


VISITS_CHART_DAYS = 60
BLOGS = ('blogarbage', 'fedoratux', 'makeyjl', 'getctrlback', 'thebthing')
EXCLUDE_SRC = ';'.join(['ga:source!=%s.blogspot.com' % src for src in BLOGS])

# Save timezone info globally, don't want to add new argument to get_date_ago
TIMEZONE = 'America/Los_Angeles'


def get_date_ago(days):

  # Adjust to TIMEZONE
  utc = dt.datetime.utcnow() - dt.timedelta(days=days)
  return pytz.timezone(TIMEZONE).fromutc(utc).strftime('%Y-%m-%d')


# General
###########
def print_general(my_client, table_id,
                  date_start=get_date_ago(VISITS_CHART_DAYS),
                  date=get_date_ago(1),
                  date_before=get_date_ago(2)):

  data_query = gdata.analytics.client.DataFeedQuery({
      'ids': table_id,
      'start-date': date_start,
      'end-date': date,
      'dimensions': 'ga:date',
      'sort': 'ga:date',
      'metrics': 'ga:visits,ga:avgTimeOnSite'})
  feed = my_client.GetDataFeed(data_query)
  visits = [int(entry.metric[0].value) for entry in feed.entry]
  max_visits = max(visits)
  print '=== General ==='
  print
  print '%s / %s' % (feed.data_source[0].GetProperty('ga:accountName').value,
                     feed.data_source[0].table_name.text)
  print
  print '--- Visits of %s -> %s ---' % (date_start, date)
  print
  CHART_HEIGHT = 10
  VISIT_WIDTH = len(str(max_visits)) + 5
  for y in range(CHART_HEIGHT, -1, -1):
    if y == CHART_HEIGHT:
      sys.stdout.write('%s%d |' % (' ' * 5, max_visits))
    else:
      sys.stdout.write('%s |' % (' ' * VISIT_WIDTH))
    for x in range(-VISITS_CHART_DAYS, 0):
      vst = visits[x]
      # vst / max_visits >= y / CHART_HEIGHT
      if vst and vst * CHART_HEIGHT >= y * max_visits:
        sys.stdout.write('#')
      else:
        sys.stdout.write(' ')
    sys.stdout.write('\n')
    sys.stdout.flush()
  print '%s0 +%s' % (' ' * (VISIT_WIDTH - 1), '-' * VISITS_CHART_DAYS)
  print

  data_query = gdata.analytics.client.DataFeedQuery({
      'ids': table_id,
      'start-date': date_before,
      'end-date': date,
      'dimensions': 'ga:date,ga:medium',
      'sort': 'ga:date',
      'metrics': ('ga:visits,ga:pageviews,ga:avgTimeOnSite,ga:bounces,'
                  'ga:avgPageLoadTime'),
  })
  feed = my_client.GetDataFeed(data_query)
  data = [{}, {}]
  dt_date_before = dt.datetime.strptime(date_before, '%Y-%m-%d')
  for entry in feed.entry:
    i = dt.datetime.strptime(entry.dimension[0].value, '%Y%m%d')
    i = (i - dt_date_before).days
    medium_name = entry.dimension[1].value
    if medium_name not in data[i]:
      data[i][medium_name] = {}
    for idx, metric in zip(range(len(entry.metric)), entry.metric):
      data[i][medium_name][metric.name] = float(metric.value)
    data[i]['all'] = {}
    for medium_name in data[i].keys():
      if medium_name == 'all':
        continue
      for metric_name, metric_value in data[i][medium_name].items():
        if metric_name == 'ga:avgTimeOnSite':
          metric_value *= float(data[i][medium_name]['ga:visits'])
        if metric_name not in data[i]['all']:
          data[i]['all'][metric_name] = metric_value
        else:
          data[i]['all'][metric_name] += metric_value
    data[i]['all']['ga:avgTimeOnSite'] /= data[i]['all']['ga:visits']

  for i in range(2):
    for medium_name in data[i].keys():
      m = data[i][medium_name]
      if m['ga:visits'] != 0.0:
        m['ga:visitBounceRate'] = 100.0 * m['ga:bounces'] / m['ga:visits']
      else:
        m['ga:visitBounceRate'] = 0.0

  cols = ['ga:visits', 'ga:pageviews', 'ga:avgTimeOnSite',
          'ga:visitBounceRate', 'ga:avgPageLoadTime']
  diff = {}
  for medium_name in set(data[0].keys() + data[1].keys()):
    for d in data + [diff]:
      if medium_name not in d:
        d[medium_name] = dict(zip(cols, [0] * len(cols)))
    for metric_name in cols:
      m = diff[medium_name]
      m0 = data[0][medium_name]
      m1 = data[1][medium_name]
      if m0[metric_name]:
        if metric_name == 'ga:visitBounceRate':
          m[metric_name] = m1[metric_name] - m0[metric_name]
        else:
          d = (m1[metric_name] - m0[metric_name]) / m0[metric_name]
          m[metric_name] = 100 * d
      else:
        m[metric_name] = 99999.99

  print '--- values of %s (change of %s -> %s) ---' % (date, date_before, date)
  print
  print '%-10s  %-15s %-15s %-18s %-20s %-18s' % tuple(['ga:medium'] + cols)
  mediums = list(data[1].keys())
  if 'all' in mediums:
    mediums.remove('all')
    mediums.sort()
    mediums.append('all')
  for medium_name in mediums:
    medium = data[1][medium_name]
    fmt = ('%-10s: %3d (%8.2f%%) %3d (%8.2f%%) %6.2f (%8.2f%%) '
           '%6.2f%% (%8.2f%%) %6.2f (%8.2f%%)')
    dat = zip([medium[metric_name] for metric_name in cols],
              [diff[medium_name][metric_name] for metric_name in cols])
    dat = tuple([medium_name] + list(chain(*dat)))
    print fmt % dat
  print

  print '--- %% of total (%s) ---' % date
  print
  bar_size = 24
  cols = ['ga:visits', 'ga:pageviews']
  fmt = '%%-10s  %%-%ds %%-%ds' % (bar_size + 8, bar_size + 8)
  print fmt % tuple(['ga:medium'] + cols)
  for medium_name in mediums:
    if medium_name == 'all':
      continue
    print '%-10s:' % medium_name,
    for metric_name in cols:
      medium = data[1][medium_name]
      if data[1]['all'][metric_name] == 0.0:
        m_percent = 0
      else:
        m_percent = 100.0 * medium[metric_name] / data[1]['all'][metric_name]
      m_bar = int(m_percent * bar_size / 100.0)
      dat = (m_percent, '#' * m_bar, ' ' * (bar_size - m_bar))
      print '%6.2f%% %s%s' % dat,
    print
  print


# Referrals
###########
def print_referrals(my_client, table_id, date=get_date_ago(1)):

  data_query = gdata.analytics.client.DataFeedQuery({
      'ids': table_id,
      'start-date': date,
      'end-date': date,
      'dimensions': 'ga:source,ga:referralPath,ga:landingPagePath',
      'metrics': 'ga:visits',
      'sort': '-ga:visits',
      'filters': 'ga:medium==referral;' + EXCLUDE_SRC,
      'max-results': '100'})
  feed = my_client.GetDataFeed(data_query)
  print '=== Referrals ==='
  print
  keyfunc = lambda entry: entry.dimension[2].value
  for k, g in groupby(sorted(feed.entry, key=keyfunc), key=keyfunc):
    print k
    for entry in g:
      values = tuple(dim.value for dim in entry.dimension)
      referrer = 'http://%s%s' % (values[0], values[1])
      print "%3s" % entry.metric[0].value, referrer.encode('utf-8')
    print
  print


# Keywords
##########
def print_keywords(my_client, table_id, date=get_date_ago(1)):

  data_query = gdata.analytics.client.DataFeedQuery({
      'ids': table_id,
      'start-date': date,
      'end-date': date,
      'dimensions': 'ga:keyword,ga:landingPagePath',
      'metrics': 'ga:visits',
      'sort': '-ga:visits',
      'filters': 'ga:medium==organic;ga:keyword!=(not provided)',
      'max-results': '100'})
  feed = my_client.GetDataFeed(data_query)
  print '=== Keywords ==='
  print
  keyfunc = lambda entry: entry.dimension[1].value
  for k, g in groupby(sorted(feed.entry, key=keyfunc), key=keyfunc):
    print k
    for entry in g:
      values = tuple(dim.value for dim in entry.dimension)
      print "%3s" % entry.metric[0].value, values[0].encode('utf-8')
    print
  print


# Social
########
def print_social(my_client, table_id, date=get_date_ago(1)):

  data_query = gdata.analytics.client.DataFeedQuery({
      'ids': table_id,
      'start-date': date,
      'end-date': date,
      'dimensions': ('ga:socialActivityContentUrl,'
                     'ga:socialActivityEndorsingUrl'),
      'metrics': 'ga:socialActivities',
      'sort': '-ga:socialActivities',
      'filters': 'ga:socialActivityEndorsingUrl!=(not set)',
      'max-results': '100'})
  feed = my_client.GetDataFeed(data_query)
  print '=== Social ==='
  print
  keyfunc = lambda entry: entry.dimension[0].value
  for k, g in groupby(sorted(feed.entry, key=keyfunc), key=keyfunc):
    print k
    for entry in g:
      values = tuple(dim.value for dim in entry.dimension)
      print "%3s" % entry.metric[0].value, values[1]
    print
  print


# Top content
##########
def print_top_content(my_client, table_id, date=get_date_ago(1)):

  data_query = gdata.analytics.client.DataFeedQuery({
      'ids': table_id,
      'start-date': date,
      'end-date': date,
      'dimensions': 'ga:pagePath,ga:source',
      'metrics': 'ga:visits',
      'sort': '-ga:visits',
      'filters': 'ga:pageviews>=5;' + EXCLUDE_SRC,
      'max-results': '100'})
  feed = my_client.GetDataFeed(data_query)
  print '=== Top content ==='
  print
  keyfunc = lambda entry: entry.dimension[0].value
  for k, g in groupby(sorted(feed.entry, key=keyfunc), key=keyfunc):
    print k
    for entry in g:
      values = tuple(dim.value for dim in entry.dimension)
      print "%3s" % entry.metric[0].value, values[1]
    print
  print


def main():

  SOURCE_APP_NAME = ''
  my_client = gdata.analytics.client.AnalyticsClient(source=SOURCE_APP_NAME)
  username = sys.argv[1]
  password = sys.argv[2]
  table_id = sys.argv[3]
  my_client.ClientLogin(username, password, source=SOURCE_APP_NAME)

  # FIXME Will break if there is more than 1000 profiles, don't seem to be able
  # to query by table_id directly.
  query = {'max-results': '1000'}
  profile_query = gdata.analytics.client.ProfileQuery(query=query)
  for profile in my_client.GetManagementFeed(profile_query).entry:
    if 'ga:' + profile.GetProperty('ga:profileId').value == table_id:
      TIMEZONE = profile.GetProperty('ga:timezone').value
      break

  print_general(my_client, table_id)
  print_referrals(my_client, table_id)
  print_keywords(my_client, table_id)
  print_social(my_client, table_id)
  print_top_content(my_client, table_id)


if __name__ == '__main__':
  main()
