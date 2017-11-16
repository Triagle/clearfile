from setuptools import setup, find_packages

setup(
    name="clearfile",
    version='0.1',
    py_modules=['clearfile'],
    packages=find_packages(),
    install_requires=[
        'pytesseract',
        'numpy',
        # Comment out if your opencv came from elsewhere.
        'opencv-python',
        'flask',
        'fuzzywuzzy',
        'rake_nltk',
        'pillow',
        'pyenchant',
        'dataset'
    ],
    entry_points='''
        [console_scripts]
        clearfile = clearfile.clearfile:cli
    ''',
)
