import logging
import os
from pprint import pformat
import glob
from itertools import chain
import argparse
import csv
import sys
from random import shuffle
import pickle

# TODO: Fix "signing doctor" in PHI

"""
if bool(re.search("signing doctor", line.lower())):
    continue 
if bool(re.search("has reviewed", line.lower())): 
    continue 
if bool(re.search("findings discussed", line.lower())):
    continue
"""

# Link to standard libraries from Splunk's python for NLTK
# sys.path=sys.path + ['/usr/lib/python2.7', '/usr/lib/python2.7/plat-x86_64-linux-gnu', '/usr/lib/python2.7/lib-tk', '/usr/lib/python2.7/lib-old', '/usr/lib/python2.7/lib-dynload', '/usr/local/lib/python2.7/dist-packages', '/usr/lib/python2.7/dist-packages', '/usr/lib/pymodules/python2.7']

import nltk
from nltk.corpus import stopwords
from nltk.probability import FreqDist
from nltk.classify import NaiveBayesClassifier as nbc
from nltk import word_tokenize


__version__ = "1.0.0"
__description__ = "RADCAT corpus builder and classifier"

"""
## Fixes for adding dependencies to Splunk's python

Similar approach to <https://answers.splunk.com/answers/474207/python-for-scientific-computing-and-the-sdk.html>

1. Copy script and pkl's over from host
```
$ docker cp RADclf.py splunk:/opt/splunk/etc/system/bin
$ docker cp report_stops.txt splunk:/opt/splunk/etc/system/bin
$ docker cp ident.pkl splunk:/opt/splunk/etc/system/bin
$ docker cp wfs.pkl splunk:/opt/splunk/etc/system/bin
$ docker cp usr_bin_python splunk:/opt/splunk/etc/system/bin
```

2. Need to install `nltk` for system Python in Splunk instance
```
> apt-get update
> apt-get install python-pip
> pip install nltk
```

3. Within python, download required modules
```
> python
>>> import nltk
>>> nltk.download('stopwords')
>>> nltk.download('punkt')
```

4. Invoke system python with:
`$ my/dumb/python usr_bin_python.py RADclf.py -w retrobulbar pizza -pd /opt/splunk/etc/system/bin`
"""

class Caching(object):

    @classmethod
    def pkl(cls, o, fn):
        logging.debug("Saving object")
        with open(fn, 'wb') as f:
            pickle.dump(o, f, -1)

    @classmethod
    def unpkl(cls, fn):
        logging.debug("Loading object")
        with open(fn, 'rb') as f:
            o = pickle.load(f)
            return o

    PICKLE_DIR = '.'

    def __init__(self, pkl, init_func=None, *init_args):
        self._init_func = init_func
        self._pkl = os.path.join(Caching.PICKLE_DIR, "{}.pkl".format(pkl))
        self._data = None
        self._init_args = init_args

    @property
    def data(self):
        if not self._data:
            try:
                self._data = self.unpkl(self._pkl)
            except:
                self._data = self._init_func(*self._init_args)
                self.pkl(self._data, self._pkl)
        return self._data


def create_corpus_from_query(montage):
    pass

    # Create worklist from all studies with "RADCAT\d"
    # Need to do this every 2 weeks or so, or you run into the
    # 25k study limit!

    # qdict = { "q":          "RADCAT",
    #           "start_date": "2017-11-01",
    #           "end_date":   "2018-01-29"}
    #
    # worklist = Montage.make_worklist(qdict)

def create_corpus_from_csv(source_dir, output_dir):

    from DixelKit import DixelTools

    files = glob.glob('{}/*.csv'.format(source_dir))

    logging.debug(files)

    worklist = set()

    for fn in files:
        w, fieldnames = DixelTools.load_csv(fn)
        worklist = worklist.union(w)

    logging.debug("Found {} dixels".format(len(worklist)))

    # Default category values for this data
    for d in worklist:
        d = DixelTools.report_extractions(d)
        if not d.meta.get('radcat'):
            logging.warn("Couldn't find radcat in {}".format(d.meta['AccessionNumber']))
            logging.warn(d.meta['Report Text'])
            # raise Exception("Couldn't find radcat in {}".format(d.meta['AccessionNumber']))
        else:
            # logging.info("Found radcat {} in {}".format(d.meta['radcat'], d.meta['AccessionNumber']))
            d.meta['categories'] = [d.meta['radcat']]

    DixelTools.save_text_corpus(output_dir, worklist, num_subdirs=1)

# ps = PorterStemmer()
stopset = set(stopwords.words('english'))
with open('report_stops.txt') as f:
    lines = f.readlines()
    words = [x.strip() for x in lines]
    for w in words:
        stopset.add(w)

def tokenize(words):
    # logging.debug('Tokenizing words')
    tokens = [w.lower() for w in words
              if w.lower() not in stopset and
                 w.isalpha()]
    # tokens = [ps.stem(t) for t in tokens]
    return tokens


def build_classifiers(corpus_dir, f_re=r'.*\.txt'):

    from nltk.corpus import CategorizedPlaintextCorpusReader

    def init_documents(f_re, cat_re):
        logging.debug("Reading corpus")
        reports = CategorizedPlaintextCorpusReader(corpus_dir,
                                                   f_re,
                                                   cat_pattern=cat_re,
                                                   encoding='utf8')
        logging.debug("Found {} fileids".format(len(reports.fileids())))
        logging.debug("Found categories: {}".format(reports.categories()))
        logging.debug("Building docs")

        documents = [
            (tokenize(reports.words(i)), reports.categories(i)[0])
              for i in reports.fileids()]
        return documents

    documents = Caching('docs', init_documents, f_re, r'.*\+(\d)\.txt')

    def init_word_features(tokens):
        logging.debug('Creating word features')
        word_features = FreqDist(tokens)
        word_features = word_features.keys()[:200]
        return word_features

    all_tokens = chain(*[i for i, j in documents.data])
    word_features = Caching('wfs', init_word_features, all_tokens)
    # word_features = Caching(init_word_features, 'wfs', all_tokens.data)
    logging.debug(pformat(word_features.data))

    def init_classifier(tag_func):
        logging.debug("Creating classifier")
        numtrain = int(len(documents.data) * 90 / 100)
        shuffle(documents.data)
        train_set = [({i: (i in tokens) for i in word_features.data}, tag_func(tag))
                     for tokens, tag in documents.data[:numtrain]]
        test_set  = [({i: (i in tokens) for i in word_features.data}, tag_func(tag))
                     for tokens, tag in documents.data[numtrain:]]

        logging.debug('Starting training')
        classifier = nbc.train(train_set)
        logging.debug('Trained')
        test_accuracy = nltk.classify.accuracy(classifier, test_set)
        setattr(classifier, 'test_accuracy', test_accuracy)
        logging.info("Overall Accuracy: {}".format(classifier.test_accuracy))
        classifier.show_most_informative_features(20)
        return classifier

    def eq1(tag):
        return int(tag)==1
    classifier_eq1 = Caching('eq1', init_classifier, eq1)

    def eq2(tag):
        return int(tag)==2
    classifier_eq2 = Caching('eq2', init_classifier, eq2)

    def eq3(tag):
        return int(tag)==3
    classifier_eq3 = Caching('eq3', init_classifier, eq3)

    def eq4(tag):
        return int(tag)==4
    classifier_eq4 = Caching('eq4', init_classifier, eq4)

    def eq5(tag):
        return int(tag)==5
    classifier_eq5 = Caching('eq5', init_classifier, eq5)

    def ident(tag):
        return int(tag)
    classifier_ident = Caching('ident', init_classifier, ident)

    # Force build for classifiers
    classifier_eq1.data
    classifier_eq2.data
    classifier_eq3.data
    classifier_eq4.data
    classifier_eq5.data
    classifier_ident.data


def concordance(w, documents):

    all_tokens = chain(*[i for i, j in documents.data])
    text = nltk.Text(all_tokens)
    logging.debug("Building concordances")
    logging.info(text.concordance(w))


def classify(clf, wfs, report_str):

    words = word_tokenize(report_str)
    tokens = tokenize(words)

    f_dict = {i: (i in tokens) for i in wfs.data}

    ident = clf.data.classify(f_dict)
    logging.debug('ident: {}'.format(ident))

    return ident


def streaming_clf(infile, outfile, text_field, class_field, clf, wfs):

    logging.debug('Streaming classify')

    r = csv.DictReader(infile)
    # logging.debug(r.fieldnames)
    w = csv.DictWriter(outfile, fieldnames=r.fieldnames, lineterminator="\n")
    w.writeheader()

    for result in r:
        if result[text_field] and result[class_field]:
            # both fields were provided, just pass it along
            w.writerow(result)

        elif result[text_field]:
            # only the report was provided, classify it
            guess = classify(clf, wfs, result[text_field])
            result[class_field] = guess
            w.writerow(result)

        else:
            # Can't create text from a radcat score!
            logging.warn('No reverse lookups allowed!')
            w.writerow(result)


def make_arg_parser():

    parser = argparse.ArgumentParser(prog='RADclf', description=__description__)
    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s (version ' + __version__ + ')')

    pkl_prs = argparse.ArgumentParser(add_help=False)
    pkl_prs.add_argument('-pd', '--pickle_dir',
                        help="Directory for temporary cache (pickle) files",
                        default='.')

    sub_prs = parser.add_subparsers(dest='command')

    clf_prs = sub_prs.add_parser("classify", parents=[pkl_prs])
    clf_prs.add_argument('-f', '--file', nargs='+',
                        help="Path to files with text to classify")
    clf_prs.add_argument('-s', '--stream', nargs=2,
                         metavar=('TEXT_FIELD', 'CLASS_FIELD'),
                         help="Splunk-style passthru CSV format")
    clf_prs.add_argument('-w', '--words', nargs="+",
                         help="Phrase to classify")

    gen_prs = sub_prs.add_parser("generate", parents=[pkl_prs])
    gen_prs.add_argument('--corpus',
                action="store_true",
                help="Create a corpus from RAW_DIR and save in CORPUS_DIR")
    gen_prs.add_argument('--classifier',
                action="store_true",
                help="Create classifier from CORPUS_DIR")
    gen_prs.add_argument('-rd', '--raw_dir')
    gen_prs.add_argument('-cd', '--corpus_dir',
                        help="Directory where NLTK formatted CategorizedPlainTextCorpus resides")

    con_prs = sub_prs.add_parser("concordance", parents=[pkl_prs])
    con_prs.add_argument('words',
                         nargs='+',
                         metavar='WORD',
                         help="Display WORD(s) context in corpus")

    return parser


def test_arg_parser(parser, _which=None):
    raw_dir    = '/Users/derek/Desktop/radcat_source'
    corpus_dir = '/Users/derek/Desktop/radcat_corpus'
    pickle_dir = 'pkl'
    test_file  = '00/00a0cfda-40f2bddb-be5740be-b37ce4cb-a1ec2843+1.txt'

    def get_cmd(which):
        if which == 'gen_corpus':
            cmd = 'generate --corpus -rd {} -cd {} -pd {}'.format(raw_dir, corpus_dir, pickle_dir)
        elif which == 'gen_clf':
            cmd = "generate --classifier -cd {} -pd {}".format(corpus_dir, pickle_dir)
        elif which == 'concordance':
            cmd = 'concordance retrobulbar hanging yellow pizza -pd {}'.format(pickle_dir)
        elif which == 'clf_file':
            cmd = "classify -f {}/{} -pd {}".format(corpus_dir, test_file, pickle_dir)
        elif which == 'clf_stream':
            cmd = "classify -s report radcat -pd {}".format(pickle_dir)
        elif which == 'clf_words':
            cmd = "classify -w He ate a yellow pizza with putamen. -pd {}".format(pickle_dir)
        else:
            cmd = "-h"
        return cmd

    if _which:
        cmd = get_cmd(_which)
        opts = parser.parse_args(cmd.split())
        return opts

    if not _which:
        for which in ['gen_corpus', 'gen_clf', 'concord', 'clf_file', 'clf_stream', 'clf_words']:
            cmd = get_cmd(which)
            opts = parser.parse_args(cmd.split())
            # Handle test...


def test_streaming():
    import StringIO
    Caching.PICKLE_DIR = "pkl"
    wfs = Caching('wfs')
    ident = Caching('ident')
    infile = StringIO.StringIO("report,radcat\nCocaine causes contractility,\nHe ate a yellow pizza with putamen.,")
    outfile = StringIO.StringIO()

    streaming_clf(infile, outfile, 'report', 'radcat', ident, wfs)

    # logging.debug('[' + outfile.getvalue() + ']')

    assert( outfile.getvalue() == "report,radcat\nCocaine causes contractility,1\nHe ate a yellow pizza with putamen.,5\n" )


def test_scoring():
    Caching.PICKLE_DIR = 'pkl'
    wfs = Caching('wfs')
    ident = Caching('ident')
    phrases = [
        ("Cocaine causes contractility",              1),
        ("A round bucket of fish",                    2),  # Seems to default to 2 w/o more info
        ("I love symmetrical etiology.",              3),
        ("The circumstances were easily reversible.", 4),
        ("Pronators occupying the pneumomediastinum", 4),
        ("He ate a yellow pizza with putamen.",       5)
    ]

    for phrase, score in phrases:
        c = classify(ident, wfs, phrase)
        assert( c == score )


if __name__ == "__main__":

    logging.basicConfig(level=logging.WARNING)
    arg_parser = make_arg_parser()

    # test_scoring()
    # test_streaming()
    opts = test_arg_parser(arg_parser, 'concordance')

    # opts = arg_parser.parse_args()
    # Setup global cache directory
    Caching.PICKLE_DIR = opts.pickle_dir

    if opts.command == 'generate' and opts.corpus:
        create_corpus_from_csv(opts.raw_dir, opts.corpus_dir)

    if opts.command == 'generate' and opts.classifier:
        build_classifiers(opts.corpus_dir, r'.*\.txt')

    if opts.command == 'classify' and opts.file:
        wfs = Caching('wfs')
        ident = Caching('ident')
        for fp in opts.file:
            with open(fp, 'r') as f:
                content = f.read()
                classify(ident, wfs, content)

    if opts.command == 'classify' and opts.words:
        wfs = Caching('wfs')
        ident = Caching('ident')
        classify(ident, wfs, " ".join(opts.words))

    if opts.command == 'classify' and opts.stream:
        report_field = opts.stream[0]
        class_field = opts.stream[1]

        infile = sys.stdin
        outfile = sys.stdout

        wfs = Caching('wfs')
        ident = Caching('ident')

        streaming_clf(infile, outfile, report_field, class_field, ident, wfs)

    if opts.command == 'concordance':
        documents = Caching('docs')  # This can be a _large_ file
        for w in opts.words:
            concordance(w, documents)