import json
import numpy as np


def cluster_by_root(parsed_query_file='../data/dependency_syntaxnet_jsonified'):
    '''
    This function clusters the queries based on the roots of dependency parse tree.
    '''
    clusthash = {}
    with open(parsed_query_file) as f:
        for aline in f:
            spltline = aline.strip().split('\t')
            # Get the root
            root = '_'.join(json.loads(spltline[1])[0].split()[:-1])
            query = spltline[0]
            if root in clusthash:
                clusthash[root].append(query)
            else:
                clusthash[root] = [query]
    return clusthash


def cluster_counts(parsed_query_file='../data/dependency_syntaxnet_jsonified'):
    '''
    This function creates a dictionary of counts of various patterns in
    the dependency parse trees.
    '''
    clust = {}
    with open(parsed_query_file) as f:
        for aline in f:
            spltline = aline.strip().split('\t')
            query = spltline[0]
            jtree = json.loads(spltline[1])
            update_count(clust, jtree)
    return clust


def get_queries_and_freq(original_query_file='../data/all-queries-raw.txt'):
    '''
    Returns the query list and the frequency list read from the files.
    '''
    original_query_list = []
    original_freq_list = []
    with open(original_query_file) as f:
        for aline in f:
            spltline = aline.strip().split('\t')
            original_query_list.append(spltline[1])
            original_freq_list.append(int(spltline[-1]))
    return original_query_list, original_freq_list


def cluster_counts_and_queries(parsed_query_file='../data/dependency_syntaxnet_jsonified',
                               original_query_file='../data/all-queries-raw.txt', get_freq=False):
    '''
    This function creates a dictionary of counts of various patterns and
    associates the corresponding query IDs.
    If get_freq is True, it returns the cluster, the list of original queries, and the list
    of query frequencies
    If get_freq is false, it returns only the first two.
    '''
    clust = {}
    if get_freq:
        original_query_list, original_freq_list = get_queries_and_freq(original_query_file)
    else:
        original_query_list, _ = get_queries_and_freq(original_query_file)
    with open(parsed_query_file) as f:
        # i is the position of the query in parsed_query_file
        # qid is the position in original_query_file
        # These two positions donot match
        for i, aline in enumerate(f):
            spltline = aline.strip().split('\t')
            # Original Query Index
            qid = int(spltline[3])
            # parsed tree in json format
            try:
                jtree = json.loads(spltline[1])
            except:
                print("Skipping corrupt line %d" % i)
                continue
            update_count_and_query(clust, jtree, qid)
    if not get_freq:
        return clust, original_query_list
    else:
        return clust, original_query_list, original_freq_list


def update_count(clust, jtree):
    '''
    This function captures the counts of all the dependency grammer
    starting from the root of the dependency tree.
    '''
    for anode in jtree:
        if type(anode) is unicode:
            if anode in clust:
                clust[anode][0] += 1
            else:
                clust[anode] = [1, {}]
            last_named_node = anode
        elif type(anode) is list:
            update_count(clust[last_named_node][1], anode)


def update_count_and_query(clust, jtree, qID, currlevel=0, maxlevel=np.inf):
    '''
    This function captures the counts of all the dependency grammer
    starting from the root of the dependency tree. In addition, it
    stores the indices of the corresponding queries. Note that it needs
    a lot of memories to store the qID's.
    '''
    if currlevel > maxlevel:
        return
    for anode in jtree:
        if type(anode) is unicode:
            if anode in clust:
                clust[anode][0] += 1
                clust[anode][2].append(qID)
            else:
                # Position#0 = Number of unique queries in this cluster (redundant)
                # Position#1 = Dictionary representing the subclusters
                # Position#2 = List of all the unique queries falling in this cluster
                clust[anode] = [1, {}, [qID]]
            last_named_node = anode
        elif type(anode) is list:
            # Recursively parse the subtrees
            update_count_and_query(clust[last_named_node][1], anode, qID, currlevel + 1, maxlevel)


def cd(clust, key):
    '''
    If the key is given in a nested format, this function changes the clust to the
    level before the last key and returns the last key.
    '''
    if '|' in key:
        keys = key.split('|')
        for akey in keys[:-1]:
            clust = clust[akey][1]
        key = keys[-1]
    return clust, key


def show_keys(clust, key='', st_idx=0, en_idx=100):
    '''
    This is similar to get_keys but it prints the results
    '''
    for i, akey, count in get_keys(clust, key, st_idx, en_idx):
        print str(i) + ': ' + akey + '(' + str(count) + ')'


def get_keys(clust, key='', st_idx=0, en_idx=100, freq_list=None, sortby=0):
    '''
    This function shows the keys (of the dictionary created by cluster_counts_and_queries
    function) sorted in descending order of unique counts.
    :param clust: The dictionary for which we want to see the keys
    :param key: Optional key. If a key is provided, the dictionary is changed to that
                specific sub-dictionary before showing the keys.
    :param st_idx: start index. The keys will be skipped upto the start index.
    :param en_idx: end index. All the keys after end index will be skipped.
    :param freq_list: if the frequency list is provided (get it from cluster_counts_and_queries
                      by setting the get_freq flag to True), this function will also return
                      the total non-unique counts of the queries under each cluster
    :param sortby:  If it is set to 0, the clusters will be sorted by unique counts. If set to
                    1, then the clusters will be sorted by total non-unique counts. This
                    parameter will be ignored if freq_list is set to None.
    '''
    if key:
        clust, key = cd(clust, key)
        clust = clust[key][1]
    if not freq_list:
        # Sort the keys based on unique counts
        allkeys = sorted([(clust[akey][0], akey) for akey in clust], key=lambda x: -1 * x[0])
        # No need to send the total non-unique counts
        for i, (unique_count, akey) in enumerate(allkeys):
            if i > en_idx:
                break
            if i < st_idx:
                continue
            yield i, akey, unique_count
    else:
        # Since we did not store the non-unique counts in the cluster, we need
        # to calculate that for every cluster and subclusters. This process
        # would make it slower than the other option.
        # Sort the keys based on either unique counts or non-unique counts
        allkeys = sorted([(clust[akey][0], \
                           sum([freq_list[aqid] for aqid in clust[akey][2]]), \
                           akey) for akey in clust], key=lambda x: -1 * x[sortby])
        # providing the frequency list implies that the user
        # wants the total non-unique counts.        
        for i, (unique_count, non_unique_count, akey) in enumerate(allkeys):
            if i > en_idx:
                break
            if i < st_idx:
                continue
            yield i, akey, unique_count, non_unique_count


def show_queries(clust, key, query_list, st_idx=0, en_idx=100):
    '''
    Similar to get_queries, but prints the data instead of yielding
    '''
    for i, qid, akey in get_queries(clust, key, query_list, st_idx, en_idx):
        print str(i) + ': ' + str(qid) + ' -- ' + akey


def get_queries(clust, key, query_list, st_idx=0, en_idx=100, freq_list=None):
    '''
    This function prints the first n queries for a specific key.
    :param clust: The cluster obtained from the function cluster_counts_and_queries
    :param key: The key of the cluster for which we are looking for the queries. It is possible
                to nest the keys by seperating them with a slash (/).
    :param query_list: The query list obtained from the function cluster_counts_and_queries
    :param freq_list: if the frequency list is provided (get it from cluster_counts_and_queries
                      by setting the get_freq flag to True), the queries will be sorted by frequency
    '''
    clust, key = cd(clust, key)
    qid_list = clust[key][2]
    if freq_list:
        rank, qid_list = zip(*sorted([(freq_list[aqid], aqid) for aqid in qid_list], key=lambda x: -1 * x[0]))
    else:
        qid_list = sorted(qid_list)
    for i, qid in enumerate(qid_list):
        if i > en_idx:
            break
        if i < st_idx:
            continue
        yield i, qid, query_list[qid]


def get_statistics(clust, key, freq_list):
    '''
    Returns the following counts for a cluster
    1. Count of all the unique queries in the current cluster
    2. Count of the total queries (non-unique) in the current cluster    
    3. Unique count of "non-dependent" queries. That is, the unique queries in the current
       cluster, which are not available in any of the sub-clusters.
    4. Total (Non-Unique) count of "non-dependent" queries.
    5. a dictionary, mapping qids (key) to a list of all the immediate subclusters
       where that qid is available

    '''
    clust, key = cd(clust, key)
    queries = {aqid: True for aqid in clust[key][2]}
    qid_to_subclust = {}
    for a_sub_clust in clust[key][1]:
        for aqid in clust[key][1][a_sub_clust][2]:
            # Delete the qid from queries to trace out the
            # queries having no dependencies
            if aqid in queries:
                del queries[aqid]
            # Add the subcluster name in qid_to_subclust
            if not aqid in qid_to_subclust:
                qid_to_subclust[aqid] = [a_sub_clust]
            else:
                qid_to_subclust[aqid].append(a_sub_clust)
    return clust[key][0], sum([freq_list[aquery] for aquery in clust[key][2]]), \
           len(queries), sum([freq_list[aquery] for aquery in queries]), qid_to_subclust


# def show_query_actions(clust,key,session_map,session_list,st_idx=0,en_idx=100,actualcount=False):
#     '''
#     Shows a probability distribution of the actions taken for the 
#     '''
#     pass

#################### Logical Operations over clusters ##########################
def get_all_queries(clust):
    '''
    Get a list of all the query id's
    '''
    allqid = []
    for akey in clust:
        allqid.extend(clust[akey][2])
    return allqid


def get_query_IDs(clust, key):
    '''
    Similar to show_queries, but instead of printing the queries, it returns all the query ID's.
    '''
    clust, key = cd(clust, key)
    return clust[key][2]


def query_or(key1, key2, clust):
    '''
    Returns a union of queries
    '''
    qid1 = set(get_query_IDs(clust, key1))
    qid2 = set(get_query_IDs(clust, key2))
    return list(qid1.union(qid2))


def query_and(key1, key2, clust):
    '''
    Returns an intersection of queries
    '''
    qid1 = set(get_query_IDs(clust, key1))
    qid2 = set(get_query_IDs(clust, key2))
    return list(qid1.intersection(qid2))


def query_subtract(key1, key2, clust):
    '''
    Returns the queries which are present in the first cluster
    but not present in the second
    '''
    qid1 = set(get_query_IDs(clust, key1))
    qid2 = set(get_query_IDs(clust, key2))
    return list(qid1 - qid2)


def show_roots(clusthash, n=100):
    '''
    This function shows the keys of the dictionary constructed by "cluster_by_root" function.
    '''
    allkeys = sorted([(len(clusthash[akey]), akey) for akey in clusthash], key=lambda x: -1 * x[0])
    for (i, (count, akeys)) in enumerate(allkeys):
        if i > n:
            break
        print '(' + str(count) + ') ' + akeys
