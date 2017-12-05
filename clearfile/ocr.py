import tempfile
import subprocess
import pytesseract
import os
import io
from PIL import Image, ExifTags
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract-ocr'

# A table mapping EXIF oreintation tags to rotations/reflections.
# EXIF oreintation tags describe the camera's oreintation relative to the captured image.
# See http://jpegclub.org/exif_orientation.html for oreintation details.
FLIP_METHOD = {
    2: [Image.FLIP_LEFT_RIGHT],
    3: [Image.ROTATE_180],
    4: [Image.FLIP_TOP_BOTTOM],
    5: [Image.FLIP_LEFT_RIGHT, Image.ROTATE_90],
    6: [Image.ROTATE_270],
    7: [Image.FLIP_LEFT_RIGHT, Image.ROTATE_270],
    8: [Image.ROTATE_90]
}


def restore_rotation(img):
    """Restore correct rotation of the image by inspecting the EXIF data of the image."""
    exifdict = img._getexif()
    orientation = 1

    for k, v in exifdict.items():
        if ExifTags.TAGS[k] == 'Orientation':
            orientation = v
            break

    if orientation > 1:
        for method in FLIP_METHOD[orientation]:
            img = img.transpose(method)

    return img


def scan_img(img, **tesseract_opts):
    """Scan an image and return the text on that image."""
    img = Image.open(img)

    grey = img.convert('L')
    ocr_text = pytesseract.image_to_string(grey, **tesseract_opts)
    return ocr_text


def pdf_as_images(pdf, directory):
    """Convert pdf to a series of pages as images and return the paths to those
    pages."""
    # convert -density 600 foo.pdf foo-%02d.jpg
    subprocess.run([
        'convert', '-density', '600', pdf,
        os.path.join(directory, 'page-%02d.jpg')
    ])
    return (os.path.join(directory, f) for f in os.listdir(directory)
            if f.startswith('page-'))


def scan_pdf(pdf, **tesseract_opts):
    """Scan a pdf by breaking the file into component pages and scanning each
    page individually."""
    ocr_text = ''

    with tempfile.TemporaryDirectory() as directory:
        for page in pdf_as_images(pdf, directory):
            ocr_text += scan_img(page)

    return ocr_text


SCAN_TABLE = {'image/jpeg': scan_img, 'application/pdf': scan_pdf}


def scan(f, mimetype, **tesseract_opts):
    """Scan a file, using it's mimetype to determine the appropriate scanning routines."""
    return SCAN_TABLE[mimetype](f, **tesseract_opts)
