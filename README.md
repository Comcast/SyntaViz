This repository contains the code of SyntaViz that Md. Iftekhar Tanveer worked on in Summer 2017.

Outline of the code
===================

- cluster_query.py:        Called by main program to build the hierarchical clusters from the (dependency) parsed queries. It has functionalities to navigate into the clusters and show the contents.
- filter_query.py:         This is one of the earliest module implementing all the necessary functions for processing the data from the production pipeline (vrex_log.queries) to smaller and more manageable files (e.g. non_titles.queries). It has functions for filtering and sorting the queries based on the language-model based scores.
- parse_query.py:          Self running module to read the list of queries and create the dependency parse trees (dependency_syntaxnet_jsonified). It assumes tensorflow/syntaxnet environment.
- syntaviz.py:             Self running module to read the hierarchical clusters from file and show in an web interface. 
- session_handler.py:     It contains the code to extract the "actions" (i.e. how the intent resolution system responded to a certain query) for the queries and to save in non_titles_actionlist.queries file. It also contains some other experimental codes with the voice_watch_pair and flat_sessions data.
- templates/              Contains the html skeleton for the SyntaViz server.

Logical sequence of the codes
=============================

        filter_query.py
	[for preparing data]                      
             |
             |
             |
             v
        parse_query.py
	[for parsing queries] 
             |
             |
             |
             v
       cluster_query.py
	[for creating clusters]
             |
             |
             |
             v
       syntaviz.py    
	[for creating server]

Running SyntaViz
================

Define variables:
```
DATADIR=/data/syntaviz
CODEDIR=/code/SyntaViz/code
PORT=5678
```

### Running SyntaViz on a corpus of queries

#### 0. Start a container with syntaxnet:
`docker run --rm --name syntaviz-parser -it -e CODEDIR=$CODEDIR -e DATADIR=$DATADIR -v $CODEDIR:$CODEDIR -v $DATADIR:$DATADIR -p 9030:8888 tensorflow/syntaxnet /bin/bash`

#### 1. Prepare data in the following format
 - cx.queries: A text file with each line representing one query in following format: `ID\tquery\tlogProb\tlogFreq\tCount`

e.g.,

```
0       i wanna change my plans its to high     1.0     1.0     1
1       please email me an alarm certificate showing that our services are current and active. 1.0     1.0     1
2       cant send outgoing email        1.0     1.0     1
```
 - cx-actions.pkl: A pkl file that contains a single mapping (dict object) with `key=query value=action`

#### 2. Parse queries
```
cd /opt/tensorflow/syntaxnet
mkdir $DATADIR/cx-parsed
python -u $CODEDIR/parse_query.py $DATADIR/cx.queries $DATADIR/cx-parsed/part >& a.log 2>&1 &
cat $DATADIR/cx-parsed/part* > $DATADIR/cx-parsed.txt
exit
```

#### 3. Start SyntaViz server
```
cd $CODEDIR
python ./syntaviz.py $DATADIR/cx.queries $DATADIR/cx-parsed.txt $DATADIR/cx-actions.pkl $PORT
```
