"""Module that handles the generation of thumbnails for non-image files."""
import subprocess


def pdf_thumbnail(pdf, output):
    """Generate a pdf thumbnail in the output folder using ImageMagick."""
    subprocess.run([
        'convert', '-thumbnail', 'x600', '-background', 'white', '-alpha',
        'remove', f'{pdf}[0]', output
    ])


THUMBNAIL_MAP = {'application/pdf': pdf_thumbnail}


def create_thumbnail(path, mime, thumb_path):
    """Creating a thumbnail for a generic file by looking up it's mimetype."""
    THUMBNAIL_MAP[mime](path, thumb_path)
