# Copyright 2018 Comcast Cable Communications Management, LLC
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

import re
import json
import nltk
import cPickle as cp
import numpy as np
from collections import OrderedDict

__author__ = 'mtanve200'


def filter_by_re(inp='../data/vrex_1week.queries',
                 outp='../data/vrex_1week_long_text_filter_by_re.queries',
                 minlen=4):
    """
    Filter the queries by regular expression.
    This method extracts all the queries that starts with wh/h words (what, how, why etc.)
    It puts an additional constraint that the query must be of length $minlen
    """
    with open(inp) as f:
        with open(outp, 'wb') as fout:
            for i, aline in enumerate(f):
                txt = aline.decode('utf8')
                jdat = json.loads(txt)
                q = jdat['text'].lower()
                test = re.match( \
                    "who|who's|what|what's|where|where's|when|when's|why|why's|how|how's|define|definition of", q)
                if i % 10000 == 0:
                    print(i), 'queries processed'
                if test and len(test.string.split()) >= minlen:
                    fout.write(test.string.encode('utf8') + '\n')
                    fout.flush()


def filter_unique(inp='../data/vrex_1week_long_text_filter_by_re.queries',
                  outp='../data/vrex_1week_long_text_filter_unique.queries'):
    """
    Filters the queries to keep only the unique ones and associates 
    a count. It reads from $inp and writes in $outp
    """
    with open(inp) as f:
        with open(outp, 'wb') as fout:
            uniq_lines = OrderedDict()
            for i, aline in enumerate(f):
                txt = aline.decode('utf8')
                if i % 10000 == 0:
                    print(i)
                if not uniq_lines.get(txt):
                    uniq_lines[txt] = 1
                else:
                    uniq_lines[txt] += 1
            for i, uqlines in enumerate(uniq_lines):
                fout.write(str(i) + '\t' + uqlines.strip().encode('utf8') + '\t' + str(uniq_lines[uqlines]) + '\n')
                fout.flush()


def filter_titles(inp='../data/vrex_1week_with_probability_plus_logfrequency_sorted.query',
                  outp='../data/non_titles.queries', query_col=1):
    """
    Filter out queries that are just the titles of some movie or tv series. This operation
    is not case or punctuation sensitive. Everything other than alphaneumeric characters
    are ignored from both.
    """
    print('Loading Titles ...')
    alltitles = cp.load(open('../data/alltitles.pickle'))['alltitles']
    print('done')
    with open(outp, 'wb') as fout:
        with open(inp) as f:
            for i, aline in enumerate(f):
                title = aline.split('\t')[query_col]
                title = re.sub('[^a-z0-9\s]+', '', title.lower())
                title = ' '.join(title.split())
                if not alltitles.get(title):
                    fout.write(aline)
                if i % 100000 == 0:
                    print(i)


def trigram_freqdist(inp='../data/combined_corpus', outp='../data/fdist_kn.pickle'):
    """
    It calculates the trigram frequency distributions for the 
    parliament speech dataset. This distribution is important
    for calculating the trigram probabilities with kneser-ney 
    smoothing. The distribution is saved in a pickle file.
    """
    with open(inp) as f:
        alltrigrams = []
        for i, aline in enumerate(f):
            aline = aline.strip().decode('utf8')
            aline = aline.encode('ascii', 'ignore')
            aline = aline.lower()
            tokens = ['<s>'] + aline.split() + ['<e>']
            alltrigrams += [(x, y, z) for x, y, z in nltk.trigrams(tokens)]
            if i % 10000 == 0:
                print(i)
        fdist = nltk.FreqDist(alltrigrams)
        cp.dump({'fdist': fdist}, open(outp, 'wb'))


def kn_logprob(inp='../data/vrex_1week_long_text.queries',
               outp='../data/vrex_1week_with_probability.queries',
               fdfile='../data/fdist_kn.pickle',
               minlen=4,
               length_normalized=True):
    """
    Calculates the log probability of every query from the input file according 
    to the trigram distributions. It uses Kneser Ney smoothing.
    It produces a tab delimited file with the queries and the logprobabilities.
    :params fdfile: Trigram frequency distribution file (pickled)
    """
    print('Loading Trigram Distribution')
    fdist = cp.load(open(fdfile))['fdist']
    print('Trigram Distribution Loaded')
    kn_pd = nltk.probability.KneserNeyProbDist(fdist)
    print('Kneser Ney Loaded')
    with open(inp) as f:
        with open(outp, 'wb') as fout:
            for i, aline in enumerate(f):
                jdat = json.loads(aline.strip())
                q = jdat['text'].lower().encode('ascii', 'ignore')
                tokens = ['<s>'] + nltk.word_tokenize(q) + ['<e>']
                if len(tokens) < minlen + 2:
                    continue
                logplist = []
                for x, y, z in nltk.trigrams(tokens):
                    lgp = kn_pd.logprob((x, y, z))
                    # OOV cases
                    if lgp == -1e300:
                        logplist.append(-50)
                    else:
                        logplist.append(lgp)
                # Length Normalization: Add points for longer sentences
                if length_normalized:
                    len_score = len(set(tokens)) * 8.5
                else:
                    len_score = 0

                logpsum = sum(logplist) + len_score
                fout.write(q + '\t' + str(logpsum) + '\n')
                fout.flush()
                if i % 100000 == 0:
                    print(i)


def sort_by_logprob(inp='../data/vrex_1week_with_probability.queries',
                    outp='../data/vrex_1week_with_probability_sorted.queries',
                    sort_column=-1, query_column=0, tag_columns=[], ascending=False):
    """
    Sorts the queries by logprobability. It assumes that the input
    is a tab-delimited file where the last column is logprobability.
    You may change the default parameter values for customized behavior.
    :params sort_column: Index of the column upon which the sorting will be done.
    :params query_column: Index of the column where the queries are located.
    :params tag_columns: A list of indices of columns which we want to augment 
                         into the output file.
    :params ascending: Sort in an ascending order instead of descending.
    """
    with open(inp) as f:
        allqueries = []
        allprob = []
        tagcols = []
        for i, aline in enumerate(f):
            cols = aline.strip().split('\t')
            logprob = float(cols[sort_column])
            allqueries.append(cols[query_column])
            allprob.append(logprob)
            if tag_columns:
                tagcols.append('\t'.join([cols[m] for m in tag_columns]))
    with open(outp, 'wb') as fout:
        if not ascending:
            idx = np.argsort(allprob)[::-1]
        else:
            idx = np.argsort(allprob)
        for m, i in enumerate(idx):
            if tagcols:
                fout.write(str(m) + '\t' + allqueries[i] + '\t' + str(allprob[i]) + '\t' + tagcols[i] + '\n')
            else:
                fout.write(str(m) + '\t' + allqueries[i] + '\t' + str(allprob[i]) + '\n')
            fout.flush()


def add_logfrequency(inp='../data/vrex_1week_with_probability_unique.queries',
                     outp='../data/vrex_1week_with_probability_plus_logfrequency.query'):
    """
    Adds the log of query-frequency with the (normalized) logprobability
    values and creates a new column with this score. This score might be
    a better query ranking metric than the normalized logprobability.
    It assumes the last column is the query frequency and the column before
    the last one is the normalized logprobability.
    """
    with open(inp) as f:
        with open(outp, 'wb') as fout:
            for i, aline in enumerate(f):
                if i % 100000 == 0:
                    print(i)
                aline = aline.strip()
                cols = aline.split('\t')
                logprob = float(cols[-2])
                logfreq = np.log(float(cols[-1]))
                fout.write(aline + '\t' + str(logprob + logfreq) + '\n')
                fout.flush()


def get_natural_queries(filename='../data/non_titles.queries'):
    """
    get a hash of all the natural queries from our natural
    query dataset.
    """
    natqueries = {}
    with open(filename) as f:
        for aline in f:
            spltaline = aline.strip().split('\t')
            natqueries[spltaline[1].lower()] = int(spltaline[0])
    return natqueries


def save_na_queries(natqueries, allqfilename='../data/vrex_log.queries',
                    outfilename='../data/NAqueries.query'):
    """
    Search for na queries in natural query database and save it
    vrex_log.queries is the dump of the following hdfs file to local filesystem:
    /user/fture/vrex/sessions/201702.22-28/vrex-log-201702_22-28.queries
    """
    with open(outfilename, 'wb') as fout:
        with open(allqfilename) as f:
            for i, aline in enumerate(f):
                if i % 10000 == 0:
                    print(i)
                jsonx = json.loads(aline.strip().lower())
                if jsonx['action'] == 'na' and \
                                len(jsonx['text'].split()) > 4 and \
                        natqueries.get(jsonx['text']):
                    fout.write(str(natqueries[jsonx['text']]) + '\t' + jsonx['text'] + '\n')


def save_uniq_sorted_na_queries(inp='../data/NAqueries.query',
                                outp='../data/NAqueries_uniq_sorted.query'):
    """
    Saves the unique queries that got an action "NA" and saves in a sorted order.
    You may get the input by running save_na_queries.
    The output file preserves the original indices in the 3rd column
    """
    filter_unique(inp, outp='../data/NAqueries_uniq.query')
    sort_by_logprob(inp='../data/NAqueries_uniq.query', outp=outp, sort_column=1,
                    query_column=2, tag_columns=[3], ascending=True)


def combine_corpus(inp1='../data/imdb_corpus_processed',
                   inp2='../data/eng_voc.txt',
                   outp='../data/combined_corpus'):
    """
    The trigram frequencies were calculated from two corpuses:
    imdb movie comment dataset and parliament speech dataset.
    This function combines the two corpuses for calcualting trigram probabilities.
    This combining process involves some preprocessing of the data.
    """
    with open(inp1) as f1:
        with open(inp2) as f2:
            with open(outp, 'wb') as fout:
                # Parliament Speech corpus
                txt2 = f2.read().decode('unicode_escape')
                fout.write(txt2.encode('utf8'))
                fout.flush()
                # IMDB corpus. It needs sentence tokenization and word tokenization.
                txt1 = f1.read()
                txt1 = txt1.decode('utf8')
                txt1 = '\n'.join([' '.join(nltk.word_tokenize(asent)) \
                                  for asent in nltk.sent_tokenize(txt1)]) + '\n'
                fout.write(txt1.encode('utf8'))
                fout.flush()


def pipeline_query_ranking(initialize=False):
    """
    The full pipeline of loading and calculating the trigram frequencies to
    ranking the queries based on our naturalness score. Please note that the
    trigram_freqdist() needs to be done only the first time.
    Output of this pipeline is saved in the following file:
    non_titles.queries
    """
    if initialize:
        # Building the language model
        trigram_freqdist()
    # Get probability
    kn_logprob()
    # Get unique queries and compute frequencies
    filter_unique(inp='../data/vrex_1week_with_probability.queries',
                  outp='../data/vrex_1week_with_probability_unique.queries')
    # Add the logfrequency with the logprobability to calculate the query ranking
    add_logfrequency()
    # Sort the queries based on rankings
    sort_by_logprob(inp='../data/vrex_1week_with_probability_plus_logfrequency.query',
                    outp='../data/vrex_1week_with_probability_plus_logfrequency_sorted.query', query_column=1,
                    tag_columns=[2, 3])
    filter_titles()


def pipeline_sort_by_frequency():
    """
    This pipeline sorts the queries based on frequency (not log-frequency).
    Output file is: vrex_1week_long_unique_sorted.queries
    """
    filter_unique(inp='../data/vrex_1week_with_probability.queries',
                  outp='../data/vrex_1week_long_unique.queries')
    sort_by_logprob(inp='../data/vrex_1week_long_unique.queries',
                    outp='../data/vrex_1week_long_unique_sorted.queries', query_column=1)
    filter_titles(inp='../data/vrex_1week_long_unique_sorted.queries',
                  outp='../data/non_titles_sorted_by_freq.queries', query_col=0)
