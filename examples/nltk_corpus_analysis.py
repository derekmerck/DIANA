"""
Example of reading a report corpus and generating a concordance and bi-grams

Create a NLTK plaintext corpus using `examples/nltk_create_report_corpus.py`
"""

from pprint import pprint
import nltk
from nltk.corpus import CategorizedPlaintextCorpusReader, stopwords
import logging

CORPUS_ROOT = "/Users/derek/Data/RADCAT/corpus"

if __name__ == "__main__":
    # For reports with category in the f/n abc_def+3.txt
    reports = CategorizedPlaintextCorpusReader(CORPUS_ROOT, '.*',
                             cat_pattern=r'.*\+(.+)\.txt')

    logging.basicConfig(level=logging.DEBUG)
    logging.debug(reports.categories())

    toks = [w.lower() for w in reports.words() if w.isalpha() and w not in stopwords.words('english')]

    all = nltk.Text(toks)
    print all.concordance('hemodynamically')

    # Create your bi-grams and n-grams
    # bgs = nltk.bigrams(toks)
    tgs = nltk.ngrams(toks, 3)

    fdist = nltk.FreqDist(tgs)
    pprint(fdist.most_common(20))