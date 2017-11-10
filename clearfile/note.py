from clearfile import keywords, preprocess
import json
import pathlib
from collections import namedtuple
import cv2
try:
    import Image
except ImportError:
    from PIL import Image
import pytesseract
# Buffer size for reading in image files to hash
HASH_BUF_SIZE = 65536
# Paper must be within 0.8x and 1.2x the normal ratio.
# See preprocess.warp_to_page
WARPING_THRESHOLD_MIN = 0.8
WARPING_THRESHOLD_MAX = 1.2

Tag = namedtuple('Tag', ['id', 'tag'])


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

    def __init__(self, uuid, name, mime, ocr_text=None, tags=None):
        ''' Initialize note object. '''
        self.uuid = uuid
        self.name = name
        self.mime = mime
        self.tags = tags or []
        self.ocr_text = ocr_text or ''

    def __repr__(self):
        ''' Return the representation of the note. '''
        description = ellipize(self.ocr_text, 50)
        class_name = self.__class__.__name__
        return f"{class_name}('{self.name}', '{description}', {self.tags})"

    def __str__(self):
        return self.ocr_text



def scan_note(filename, note, **tesseract_opts):
    ''' Scan note using tesseract-ocr. '''
    image = cv2.imread(str(filename))
    likeness, result = preprocess.warp_to_page(image)
    likely_paper = WARPING_THRESHOLD_MIN < likeness < WARPING_THRESHOLD_MAX
    if result is None or not likely_paper:
        result = image
    image = Image.fromarray(result)
    note.ocr_text = pytesseract.image_to_string(image, **tesseract_opts)
    note.tags = keywords.keywords_of('en_NZ', note.ocr_text)


class NoteEncoder(json.JSONEncoder):
    ''' Encode Note into JSON. '''
    def default(self, obj):
        ''' overridden default to encode Nte into JSON. '''
        if isinstance(obj, Note):
            tags = [{"id": tag.id, "tag": tag.tag} for tag in obj.tags]
            return {'uuid': obj.uuid,
                    'name': obj.name,
                    'mime': obj.mime,
                    'tags': tags,
                    'ocr_text': obj.ocr_text}
        elif isinstance(obj, pathlib.PurePath):
            return str(obj)
        return json.JSONEncoder.default(self, obj)
