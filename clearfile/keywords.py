from rake_nltk import Rake
import itertools
import enchant


def keywords_of(lang, text, k=10):
    ''' Return a set of at least k keywords from text written in the language lang. '''
    r = Rake()
    dictionary = enchant.Dict(lang)
    r.extract_keywords_from_text(text)
    keywords = set()
    phrases = r.get_ranked_phrases()
    for index, keyword in enumerate(itertools.chain(phrases)):
        if len(keywords) > k:
            break
        word_set = set(k for k in keyword.split(' ') if dictionary.check(k))
        keywords.update(word_set)

    return keywords
