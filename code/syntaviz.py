# Copyright 2017 Comcast Cable Communications Management, LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import pdb

from flask import Flask, abort, render_template, url_for, request
import cluster_query
import pickle as cp
import numpy as np
import urllib
import json
import sys
import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

'''
This is a quick working prototype of a visualizer that would
facilitate the exploring of syntactic patterns of queries and
the statistical distribution of the actions currently taken for
these patterns.

Note: This server needs the following files:
1.  '../data/all-queries-raw.txt': This is a tab delimited list
    of original queries. It also contains
2.  '../data/dependency_syntaxnet_jsonified': This is a tab 
    delimited list of tokenized queries, dependency parse in
    two different formats, and the query ID (index to the original
    query list).
3.  '../data/qaction.pickle': It contains a dictionary named qaction
    which returns the actions taken (values) for the queries (keys).

'''

inpfile = sys.argv[1]
outfile = sys.argv[2]
query2actionfile = sys.argv[3]
PORT=5678
if len(sys.argv) > 4:
    PORT = int(sys.argv[4])

################## Load the pre-requisites ####################
print("Loading cluster data ...")
clust_head, queries, freq_list = cluster_query.cluster_counts_and_queries(
    original_query_file=inpfile,
    parsed_query_file=outfile,
    get_freq=True)
clust = clust_head
tot_uniq = sum([clust[akey][0] for akey in clust])
tot_nonuniq = sum([freq_list[aqid] for akey in clust for aqid in clust[akey][2]])
print("Done clustering.")

print("Loading list of actions performed for each query ...")
qaction = cp.load(open(query2actionfile))
print("Done loading actions.")

###############################################################

# The SyntaViz server
app = Flask('SyntaViz')


@app.route('/keys/<string:key>')
@app.route('/keys//<int:st_idx>/<int:en_idx>')
@app.route('/keys/<string:key>/<int:st_idx>/<int:en_idx>')
def get_keys_json(key='', st_idx=0, en_idx=50):
    '''
    Make a list of keys
    '''
    key = urllib.unquote(urllib.unquote(key))
    allkeys = []
    try:
        for i, akey, count in cluster_query.get_keys(clust, key, st_idx, en_idx):
            if key:
                akey = key + '|' + akey
            allkeys.append((i, count, akey))
    except KeyError:
        print('Key Not Found:', key)
        return abort(404)
    return json.dumps(allkeys)


@app.route('/queries/<string:key>')
@app.route('/queries/<string:key>/<int:st_idx>/<int:en_idx>')
def get_queries_json(key='', st_idx=0, en_idx=50):
    '''
    Make a list of queries
    '''
    key = urllib.unquote(urllib.unquote(key))
    clust = clust_head
    allqueries = []
    try:
        for i, qid, aquery in cluster_query.get_queries(clust, key, queries, st_idx, en_idx):
            allqueries.append((i, qid, aquery))
    except:
        print('Key Not Found:', key)
        return abort(404)
    return json.dumps(allqueries)


def get_action_hist(key, qaction):
    '''
    Returns the frequency of various actions taken (in response to
    the queries of a key) as well as the list of actions
    '''
    action_hist = {}
    clust = clust_head
    for i, qid, aquery in cluster_query.get_queries(clust, key, queries, en_idx=float('inf')):
        aquery = aquery.lower()
        if aquery in qaction:
            if qaction[aquery] in action_hist:
                action_hist[qaction[aquery]] += 1
            else:
                action_hist[qaction[aquery]] = 1
    return action_hist


def get_plot(adict):
    '''
    Plot the action dictionary
    '''
    img_format = \
        '<img src="data:image/png;base64,{0}" style="width: 100%;  height: auto;">'
    count, labels = zip(*sorted([(adict[akey], akey) for akey in adict],
                                key=lambda x: -1 * x[0]))
    # total is the number of queries having an action
    # m is the number of different actions
    m = len(count)
    total = sum(count)
    # Plot
    if m > 30:
        plt.figure(num=1, figsize=(12, 8), fontsize=24)
        plt.clf()
        plt.bar(np.arange(30), count[:30])
        plt.xticks(np.arange(30) + 0.4, labels[:30], rotation='vertical', fontsize=24)
        plt.xlabel('Name of Actions (Only top 30 among {0})'.format(m))
        plt.ylabel('Count of Actions')
        plt.title('Total unique queries containing an action (Including NA) = {0}'.format(total))
        try:
            plt.tight_layout()
        except:
            print("matplotlib error")
            pass
            # pdb.set_trace()
    else:
        plt.figure(num=1, figsize=(12, 8), fontsize=24)
        plt.clf()
        plt.bar(np.arange(m), count)
        plt.xticks(np.arange(m) + 0.4, labels, rotation='vertical', fontsize=24)
        plt.xlabel('Name of Actions (all)')
        plt.ylabel('Count of Actions')
        plt.title('Total unique queries containing an action (Including NA) = {0}'.format(total))
        try:
            plt.tight_layout()
        except:
            print("matplotlib error")
            pass
            # pdb.set_trace()
    # Convert to html
    figfile = BytesIO()
    plt.savefig(figfile, format='png')
    figfile.seek(0)
    figfile_png = base64.b64encode(figfile.getvalue())
    return img_format.format(figfile_png)


@app.route('/')
@app.route('/both')
def both():
    '''
    Show the page
    '''
    # Parsing arguments
    key_k = urllib.unquote(urllib.unquote(request.args.get('key_k', '')))
    st_idx_k = int(request.args.get('st_idx_k', 0))
    en_idx_k = int(request.args.get('en_idx_k', 500))
    st_idx_q = int(request.args.get('st_idx_q', 0))
    en_idx_q = int(request.args.get('en_idx_q', 1000))
    sort_key_by = int(request.args.get('sort_key_by', 0))  # sort by unique count(0), total count(1)
    sort_query_by = int(request.args.get('sort_query_by', 0))  # sort by query frequency(0), or qid(1)

    try:
        # Build the list of keys
        clust = clust_head
        allkeys = []
        for i, akey, count, nucount in cluster_query.get_keys( \
                clust,
                key_k,
                st_idx_k,
                en_idx_k,
                freq_list=freq_list,
                sortby=sort_key_by):
            if key_k:
                fullkey = key_k + '|' + akey
            else:
                fullkey = akey
            encodedkey = urllib.quote(fullkey)
            # Link to go to a specific cluster
            keylink = url_for('both',
                              key_k=encodedkey,
                              st_idx_k=st_idx_k,
                              en_idx_k=en_idx_k,
                              st_idx_q=st_idx_q,
                              en_idx_q=en_idx_q,
                              sort_key_by=sort_key_by,
                              sort_query_by=sort_query_by)
            allkeys.append((i, count, akey, keylink, nucount,
                            '{0:0.2f}'.format(float(count) / float(tot_uniq) * 100.),
                            '{0:0.2f}'.format(float(nucount) / float(tot_nonuniq) * 100.)))
    except KeyError:
        print('Key Not Found:', key_k)
        return abort(404)

    # Build the left pane navigations
    navformat = '<a href="{0}">{1}</a>'
    diff = en_idx_k - st_idx_k
    if st_idx_k > 0:
        left_prev_code = navformat.format(url_for('both',
                                                  key_k=key_k,
                                                  st_idx_k=max(0, st_idx_k - diff),
                                                  en_idx_k=st_idx_k,
                                                  st_idx_q=st_idx_q,
                                                  en_idx_q=en_idx_q,
                                                  sort_key_by=sort_key_by,
                                                  sort_query_by=sort_query_by), '&#60&#60')
    else:
        left_prev_code = '<<'
    left_next_code = navformat.format(url_for('both',
                                              key_k=key_k,
                                              st_idx_k=en_idx_k,
                                              en_idx_k=en_idx_k + diff,
                                              st_idx_q=st_idx_q,
                                              en_idx_q=en_idx_q,
                                              sort_key_by=sort_key_by,
                                              sort_query_by=sort_query_by), '&#62&#62')

    # Build the breadcrumb
    if not key_k:
        currentkey = '&#60 None &#62'
    else:
        if '|' in key_k:
            currentkey = ''
            spltkey = key_k.split('|')
            for i in range(len(spltkey)):
                encodedkey = urllib.quote('|'.join(spltkey[:i + 1]))
                currentkey += '<a href="{1}">{0}|</a>'.format(spltkey[i], url_for('both',
                                                                                  key_k=encodedkey,
                                                                                  st_idx_k=0,
                                                                                  en_idx_k=en_idx_k - st_idx_k,
                                                                                  st_idx_q=0,
                                                                                  en_idx_q=en_idx_q - st_idx_q,
                                                                                  sort_key_by=sort_key_by,
                                                                                  sort_query_by=sort_query_by))
            if currentkey[-1] == '|':
                currentkey = currentkey[:-1]
        else:
            currentkey = key_k

    # Build the links for sorting the keys
    unique_link = url_for('both',
                          key_k=key_k,
                          st_idx_k=st_idx_k,
                          en_idx_k=en_idx_k,
                          st_idx_q=st_idx_q,
                          en_idx_q=en_idx_q,
                          sort_key_by=0,
                          sort_query_by=sort_query_by)
    total_link = url_for('both',
                         key_k=key_k,
                         st_idx_k=st_idx_k,
                         en_idx_k=en_idx_k,
                         st_idx_q=st_idx_q,
                         en_idx_q=en_idx_q,
                         sort_key_by=1,
                         sort_query_by=sort_query_by)

    # If no key is selected, just send out the root keys
    if not key_k:
        return render_template('fullpage.html',
                               total_count=tot_nonuniq,
                               uniq_count=tot_uniq,
                               left_prev_code=left_prev_code,
                               left_next_code=left_next_code,
                               allkeys=allkeys,
                               currentkey=currentkey,
                               header_unique_link=unique_link,
                               header_total_link=total_link)

    try:
        # Build the list of queries
        allqueries = []
        clust = clust_head
        if sort_query_by == 0:
            # sort by query frequency
            frequency_list = freq_list
        else:
            # sort by qid
            frequency_list = None
        # Accumulate the queries
        for i, qid, aquery in cluster_query.get_queries(clust,
                                                        key_k,
                                                        queries,
                                                        st_idx_q,
                                                        en_idx_q,
                                                        freq_list=frequency_list):
            if aquery.lower() in qaction:
                query_action = qaction[aquery.lower()]
            else:
                query_action = '[Not Found]'
            allqueries.append((i,
                               qid,
                               aquery,
                               query_action,
                               freq_list[qid],
                               '{0:0.3f}'.format(float(freq_list[qid]) / tot_nonuniq * 100.)))

    except KeyError:
        print('Key Not Found:', key_k)
        return abort(404)

    # Build the right pane navigations
    diff = en_idx_q - st_idx_q
    if st_idx_q > 0:
        right_prev_code = navformat.format(url_for('both',
                                                   key_k=key_k,
                                                   st_idx_k=st_idx_k,
                                                   en_idx_k=en_idx_k,
                                                   st_idx_q=max(0, st_idx_q - diff),
                                                   en_idx_q=st_idx_q,
                                                   sort_key_by=sort_key_by,
                                                   sort_query_by=sort_query_by), '&#60&#60')
    else:
        right_prev_code = '&#60&#60'
    right_next_code = navformat.format(url_for('both',
                                               key_k=key_k,
                                               st_idx_k=st_idx_k,
                                               en_idx_k=en_idx_k,
                                               st_idx_q=en_idx_q,
                                               en_idx_q=en_idx_q + diff,
                                               sort_key_by=sort_key_by,
                                               sort_query_by=sort_query_by), '&#62&#62')

    # Build the links for sorting the queries
    # By frequency
    header_freq_link = url_for('both',
                               key_k=key_k,
                               st_idx_k=st_idx_k,
                               en_idx_k=en_idx_k,
                               st_idx_q=st_idx_q,
                               en_idx_q=en_idx_q,
                               sort_key_by=sort_key_by,
                               sort_query_by=0)
    # By QID
    header_qid_link = url_for('both',
                              key_k=key_k,
                              st_idx_k=st_idx_k,
                              en_idx_k=en_idx_k,
                              st_idx_q=st_idx_q,
                              en_idx_q=en_idx_q,
                              sort_key_by=sort_key_by,
                              sort_query_by=1)

    # Calculate the cluster statistics
    clust_stats = cluster_query.get_statistics(clust, key_k, freq_list)

    # Build the visualization on the right pane
    action_freq = get_action_hist(key_k, qaction)
    image_src = get_plot(action_freq)

    # Send all the data with visualization if there are queries
    if len(action_freq.keys()) > 0:
        # When the plot exists
        return render_template('fullpage.html',
                               total_count=tot_nonuniq,
                               uniq_count=tot_uniq,
                               left_prev_code=left_prev_code,
                               left_next_code=left_next_code,
                               allkeys=allkeys,
                               currentkey=currentkey,
                               header_unique_link=unique_link,
                               header_total_link=total_link,
                               right_prev_code=right_prev_code,
                               right_next_code=right_next_code,
                               allqueries=allqueries,
                               clust_stats=clust_stats,
                               image_src=image_src,
                               header_freq_link=header_freq_link,
                               header_qid_link=header_qid_link)
    else:
        # When the plot does not exist
        return render_template('fullpage.html',
                               total_count=tot_nonuniq,
                               uniq_count=tot_uniq,
                               left_prev_code=left_prev_code,
                               left_next_code=left_next_code,
                               allkeys=allkeys,
                               currentkey=currentkey,
                               header_unique_link=unique_link,
                               header_total_link=total_link,
                               right_prev_code=right_prev_code,
                               right_next_code=right_next_code,
                               allqueries=allqueries,
                               clust_stats=clust_stats,
                               header_freq_link=header_freq_link,
                               header_qid_link=header_qid_link)


# Run the server
if __name__ == '__main__':
    app.debug = False
    app.run(host='0.0.0.0', port=PORT)
