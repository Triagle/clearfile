from setuptools import setup, find_packages

setup(
    name="clearfile",
    version='0.1',
    py_modules=['clearfile'],
    packages=find_packages(),
    install_requires=[
        'pytesseract',
        'watchdog',
        'numpy',
        'opencv-python'
        'click'
    ],
    entry_points='''
        [console_scripts]
        clearfile = clearfile.clearfile:cli
    ''',
)
