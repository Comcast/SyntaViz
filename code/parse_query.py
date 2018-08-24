import os
import sys
import stat
import numpy as np
import json
import time
from itertools import izip
from multiprocessing import Process
from os import path

__author__ = 'mtanve200'


def parse_query_with_syntaxnet(query_generator,
                               start_index=0,
                               end_index=np.inf,
                               shellname='syntaxnet/demo.sh'):
    '''
    Parses a query using syntaxnet. It breaks the input stream into mini batches of 1000
    queries and passes through the syntaxnet. It extracts two different styles of the parse
    tree. It reads the whole input and returns the trees as a list. Do do not feed an
    infinitely long stream because that will overflow the memory.
    It requires to be called from the /root/models/syntaxnet/
    folder of the syntaxnet docker
    :param query_generator: An iterator of (index, query) tuples
    :param start_index: From which item it will start parsing. Note, it does not consider the index
                        of the data in the query file. It considers the idex of the data as they arrive
    :param end_index: Where it will stop reading. Same convention to start_index applies.

    Note: It is utmost important to remove the last element (a blank line)
    from the output of parse_query_with_syntaxnet function, before passing
    it to the segment_gen function. Otherwise, it will create an invalid 
    tree for the last element of the batch due to the blank line.
    '''
    assert start_index < end_index, 'Start index cannot be greater than end index'
    allparsetreelist = []
    orig_idx_list = []
    container = []
    idx_container = []

    def process_single(idx_container, container, orig_idx, aquery):
        container.append(aquery)
        idx_container.append(orig_idx)

    def write_to_disk(idx_container, container):
        argtxt_ = '\n'.join(container)
        output = os.popen('echo ' + '"' + argtxt_ + '"' + ' | ' + shellname).read().split('\n')
        allparsetreelist.extend(output)
        orig_idx_list.extend(idx_container)

    # Iterate over the queries and the save the parsed tree
    for i, (orig_idx, aquery) in enumerate(query_generator):
        if i < start_index:
            continue
        elif start_index <= i <= end_index:
            # put the first query in a container
            process_single(idx_container, container, orig_idx, aquery)
            if len(container) % 1000 == 999:
                # The container is full. Process the queries within the container
                write_to_disk(idx_container, container)
                container = []
                idx_container = []
        elif i > end_index:
            break
    if len(container) > 0:
        write_to_disk(idx_container, container)
    return allparsetreelist, orig_idx_list


def make_new_shell():
    # Prepare a shell for conll style dependency tree
    # This function must run within the docker image of syntaxnet
    st = os.stat('syntaxnet/demo.sh')
    os.chmod('syntaxnet/demo.sh', 0o777)
    with open('syntaxnet/demo.sh') as f:
        txt = f.read()
    with open('syntaxnet/demo_conll.sh', 'wb') as f:
        f.write(txt[:-107] + '\n')
    st = os.stat('syntaxnet/demo_conll.sh')
    os.chmod('syntaxnet/demo_conll.sh', st.st_mode | stat.S_IEXEC)


def query_gen(inpfile):
    '''
    Construct an iterator to feed the queries from the inpfile
    '''
    # Start reading and yieling the queries
    with open(inpfile) as f:
        for aline in f:
            spltline = aline.strip().split('\t')
            yield int(spltline[0]), spltline[1]


def abstract_query_gen(inpfile):
    '''
    It is similar to query_gen. The only difference is, it reads from the abstract query file,
    thus processes and transmits the abstract queries accordingly.
    '''
    # Start reading and yieling the queries
    with open(inpfile) as f:
        for aline in f:
            spltline = aline.strip().split('\t')
            yield int(spltline[0]), spltline[2]


def input_gen(filename):
    '''
    Makes an iterator from the file. This is useful when the output
    of the syntaxnet is saved as a file and you take that file to
    pass through the segment_gen function as an iterator.
    '''
    with open(filename) as f:
        for aline in f:
            if aline[0] == ' ':
                yield aline[1:].rstrip()
            else:
                yield aline.rstrip()


def segment_gen(inp_gen):
    '''
    Segments the stream from the output of syntaxnet into
    one input and one parse tree at a time. The parse tree
    is given in a json format.
    :param inp_gen: input iterator 
    '''
    retval = ''
    parsetree = ''
    currlevel = -1
    count = 0
    for inp in inp_gen:
        # Transforming the tree with states "Input", "Parse", and
        # the normal tree parsing.
        if inp.startswith('Input'):
            # if there is something in retval from previous iterations
            if retval:
                # Close off the tree 
                retval += parsetree + ']' * (currlevel + 2)
                yield retval
                # Reset the value
                retval = ''
            # There is nothing from previous iterations, so start making
            retval += inp[6:].strip() + '\t'
        elif inp.startswith('Parse'):
            # start of the parse tree
            parsetree = ''
        elif not inp:
            # if the input is empty, just skip it
            continue
        else:
            parse_out, currlevel = jsonify_tree(inp, currlevel)
            # Debug
            # print inp,parse_out,currlevel
            parsetree += parse_out
    if retval and parsetree:
        # Close off the last tree
        retval += parsetree + ']' * (currlevel + 2)
        yield retval


def segment_gen_conll(inp_gen):
    '''
    similar to segment_gen, but works on conll style parse tree
    '''
    aparse = []
    for inp in inp_gen:
        if not inp:
            yield json.dumps(aparse)
            aparse = []
        else:
            aparse.append(inp.split('\t')[1:])


def jsonify_tree(inp, currlevel):
    '''
    Converts from syntaxnet tree structure to json tree structure.
    '''
    nxtlevel = inp.find('+--') / 4
    if nxtlevel == -1:
        # Root Node
        return '[ ' + '"' + inp + '"', -1
    elif nxtlevel == currlevel + 1:
        # Subtree of previous node
        return ', [ ' + '"' + inp[nxtlevel * 4 + 4:].strip() + '"', nxtlevel
    elif nxtlevel == currlevel:
        # Another node in the same level of the tree
        return ', ' + '"' + inp[nxtlevel * 4 + 4:].strip() + '"', nxtlevel
    elif nxtlevel < currlevel:
        # At least one subtree finished
        leveljump = currlevel - nxtlevel
        return ']' * leveljump + ',' + '"' + inp[nxtlevel * 4 + 4:].strip() + '"', nxtlevel
    else:
        # nxtlevel>currlevel+1 
        # Impossible situation. Something is wrong
        raise IOError('More than one level jump forward. At least one tree node must be missing.')


def pipeline(inpfile, outfile,
             start_idx=0,
             end_idx=np.inf,
             stream_generator_function=query_gen):
    '''
    This is the complete pipeline for parsing the (raw or abstract) queries from the queryfile
    (query_analysis/data/non_titles.queries) using syntaxnet and producing the outfile.
    :param outfile: The name (with path) of the file where the output will be written
    :param start_idx: Element in the stream where the parsing should start
    :param end_idx: Element in the stream where the parsing should stop
    :param stream_generator_function: Determines whether the queries or the abstract queries
    would be processed for parsing. As the formats of the query and abstract files are different,
    the generator functions automatically reads the corresponding file formats.
    This argument takes only the following two generator functions:
    a) query_gen
    b) abstract_query_gen
    '''
    # Normal parse tree
    qgen1 = stream_generator_function(inpfile)
    output_tree, orig_idx_list = parse_query_with_syntaxnet(qgen1, start_index=start_idx, end_index=end_idx)
    tree_gen = segment_gen(output_tree)

    # Conll style parse tree
    qgen2 = stream_generator_function(inpfile)
    output_conll, orig_idx_list = parse_query_with_syntaxnet(qgen2, start_index=start_idx, end_index=end_idx,
                                                             shellname='syntaxnet/demo_conll.sh')
    conll_gen = segment_gen_conll(output_conll)

    # Save to file
    with open(outfile, 'wb') as f:
        for (i, tree, conll) in izip(orig_idx_list, tree_gen, conll_gen):
            f.write(tree + '\t' + conll + '\t' + str(i) + '\n')
            f.flush()


if __name__ == '__main__':
    make_new_shell()

    abstract = False

    inpfile = sys.argv[1]
    outfile = sys.argv[2]

    outdir = path.dirname(os.path.abspath(outfile))
    if not os.path.exists(outdir):
        raise OSError("Output directory does not exist: %s" % outdir)

    def file_len(fname):
        i = -1
        with open(fname) as f:
            for i, l in enumerate(f):
                pass
        return i + 1


    line_cnt = file_len(inpfile)

    print(sys.argv)
    print(line_cnt)

    if abstract:
        for i in range(0, line_cnt, 1000):
            p = Process(target=pipeline, args=(inpfile, outfile + str(i), i, i + 999, abstract_query_gen))
            p.start()
            time.sleep(5)
    else:
        for i in range(0, line_cnt, 1000):
            p = Process(target=pipeline, args=(inpfile, outfile + str(i), i, i + 999))
            p.start()
            time.sleep(5)
