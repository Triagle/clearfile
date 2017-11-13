import itertools
from collections import Counter
import enchant
from rake_nltk import Rake


def keywords_of(lang, text, k=5):
    ''' Return a set of at least k keywords from text written in the language lang. '''
    r = Rake()
    dictionary = enchant.Dict(lang)
    r.extract_keywords_from_text(text)
    keywords = Counter()
    phrases = r.get_ranked_phrases()

    for phrase in itertools.chain(phrases):
        word_set = set(k for k in phrase.split(' ') if dictionary.check(k) and len(k) >= 4)
        keywords.update({k: 1 for k in word_set})


    return [key for key, _ in keywords.most_common(k)]
