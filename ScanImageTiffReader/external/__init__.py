""" Defines paths to binary resource derived with provenance external to this
code.  This is also used in `setup.py`.
"""

_registry={
    'Windows': {'location':'ScanImageTiffReader-1.4.1-win64',  'name':"ScanImageTiffReaderAPI.dll"},      
    'Darwin' : {'location':'ScanImageTiffReader-1.4.1-Darwin', 'name':"libScanImageTiffReaderAPI.so"},         
    'Linux'  : {'location':'ScanImageTiffReader-1.4.1-Linux',  'name':"libScanImageTiffReaderAPI.so"},     
}

def resource_path():
    """ Returns an absolute path to a shared library with the ScanImageTiffReaderAPI.
    """
    from os.path import (abspath,join,dirname)
    import platform
    # Lookup based on platform string.
    # If the platform string isn't matched, we'll use Linux as a fallback.
    info=_registry.get(platform.system(),_registry['Linux'])
    return join(dirname(abspath(__file__)),info["location"],'lib',info["name"])