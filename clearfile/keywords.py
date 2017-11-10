import itertools

import enchant
from rake_nltk import Rake


def keywords_of(lang, text, k=10):
    ''' Return a set of at least k keywords from text written in the language lang. '''
    r = Rake()
    dictionary = enchant.Dict(lang)
    r.extract_keywords_from_text(text)
    keywords = set()
    phrases = r.get_ranked_phrases()
    for phrase in itertools.chain(phrases):
        if len(keywords) > k:
            break
        word_set = set(k for k in phrase.split(' ') if dictionary.check(k) and len(k) >= 4)
        keywords.update(word_set)

    return keywords
