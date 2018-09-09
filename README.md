SyntaViz is a visualization interface specifically designed for analyzing a large number of natural-language queries. SyntaViz provides a platform for browsing the ontology of user queries from a syntax-driven perspective, providing quick access to high-impact failure points of the existing intent understanding system and evidence for data-driven decisions in the development cycle.

For more details, see our demo paper "SyntaViz: Visualizing Voice Queries through a Syntax-Driven Hierarchical Ontology" at EMNLP 2018: http://emnlp2018.org/program/accepted/demos

Outline of the code
===================

- filter_query.py:         Implements all the necessary functions for processing the raw data to smaller and more manageable files. It has functions for filtering and sorting the queries based on language model-based scores.
- parse_query.py:          Parses a list of queries and outputs a list of dependency parse trees. It assumes tensorflow/syntaxnet environment.
- cluster_query.py:        Builds hierarchical clusters from the (dependency) parsed queries. It has functionalities to navigate into the clusters and show the contents.
- syntaviz.py:             Reads the hierarchical clusters from file and displays them dynamically in a web interface. 
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
CODEDIR=/code/SyntaViz
PORT=5678
```

### Running SyntaViz on a corpus of queries

#### 0. Set up environment
Start container with SyntaxNet:
`docker run --rm --name syntaviz-parser -it -e CODEDIR=$CODEDIR -e DATADIR=$DATADIR -v $CODEDIR:$CODEDIR -v $DATADIR:$DATADIR -p 9030:8888 tensorflow/syntaxnet /bin/bash`

Install Syntaviz:
```
pip install --upgrade setuptools
python setup.py install
```

#### 1. Prepare data in the following format
 - queries: A text file with each line representing one query in following format: `ID\tquery\tlogProb\tlogFreq\tCount`

e.g.,

```
0       i wanna change my plans its to high     1.0     1.0     1
1       please email me an alarm certificate showing that our services are current and active. 1.0     1.0     1
2       cant send outgoing email        1.0     1.0     1
```
 - actions.pkl: A pkl file that contains a single mapping (dict object) with `key=query value=action`

#### 2. Parse queries
```
cd /opt/tensorflow/syntaxnet
mkdir $DATADIR/parsed
python -m syntaviz.parse_query $DATADIR/queries $DATADIR/parsed/part >& parse-queries.log 2>&1 &
cat $DATADIR/parsed/part* > $DATADIR/parsed.txt
```
At this point, `$DATADIR/parsed.txt` should have the same number of lines as `$DATADIR/queries`.

#### 3. Start SyntaViz server
```
python -m syntaviz.syntaviz $DATADIR/queries $DATADIR/parsed.txt $DATADIR/actions.pkl $PORT
```
