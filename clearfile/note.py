# from clearfile import keywords, ocr
import json
import pathlib
import os
from collections import namedtuple
from clearfile import ocr, keywords
try:
    import Image
except ImportError:
    from PIL import Image
import tempfile

# Buffer size for reading in image files to hash
HASH_BUF_SIZE = 65536
# Paper must be within 0.8x and 1.2x the normal ratio.
# See preprocess.warp_to_page

Tag = namedtuple('Tag', ['id', 'uuid', 'tag'])


def node_path_for_filepath(path, relativeto):
    ''' Return the node path in the note tree from a given filepath.
    >>> node_path_for_filepath(Path('/home/test/image.png'), Path('/'))
    (('home', 'test'), 'image.png') '''
    path = pathlib.Path(path)
    relpath = path.relative_to(relativeto).parent
    return relpath.parts, path.name


def ellipize(string, limit):
    ''' Ellipize a string, i.e truncate it at limit and append "..."
    >>> ellipize("long string", 5)
    "long ..." '''
    if len(string) > limit:
        return string[:limit] + '...'
    return string


class Note(object):
    ''' Represents a single note (image). Holds information like ocr
    recovered text, the fullpath, tags, etc. '''

    def __init__(self, uuid, name, ocr_text=None, tags=None):
        ''' Initialize note object. '''
        self.uuid = uuid
        self.name = name
        self.tags = tags or []
        self.ocr_text = ocr_text or ''

    def __repr__(self):
        ''' Return the representation of the note. '''
        description = ellipize(self.ocr_text, 50)
        class_name = self.__class__.__name__
        return f"{class_name}('{self.name}', '{description}', {self.tags})"

    def __str__(self):
        return self.ocr_text



def scan_note(note, image, **tesseract_opts):
    ''' Scan note using tesseract-ocr. '''
    note.ocr_text = ocr.scan(image)
    note.tags = [
        Tag(note.uuid, keyword)
        for keyword in keywords.keywords_of('en_NZ', note.ocr_text)
    ]


class NoteEncoder(json.JSONEncoder):
    ''' Encode Note into JSON. '''
    def default(self, obj):
        ''' overridden default to encode Nte into JSON. '''
        if isinstance(obj, Note):
            tags = [{"id": tag.id, "tag": tag.tag} for tag in obj.tags]
            return {'uuid': obj.uuid,
                    'name': obj.name,
                    'tags': tags,
                    'ocr_text': obj.ocr_text}
        elif isinstance(obj, pathlib.PurePath):
            return str(obj)
        return json.JSONEncoder.default(self, obj)
