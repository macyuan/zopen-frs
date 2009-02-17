import time
import os
import shutil
import socket
from random import random
from md5 import md5
from config import FS_CHARSET
from types import UnicodeType

def timetag(the_time=None):
    if the_time is None:
        # use gmt time
        the_time = time.gmtime()
        return time.strftime('%Y-%m-%d-%H-%M-%S', the_time)
    else:
        return the_time.strftime('%Y-%m-%d-%H-%M-%S')

def ucopy2(ossrc, osdst):
    # ucopy2 dosn't work with unicode filename yet
    if type(osdst) is UnicodeType and \
           not os.path.supports_unicode_filenames:
        ossrc = ossrc.encode(FS_CHARSET)
        osdst = osdst.encode(FS_CHARSET)
    shutil.copy2(ossrc, osdst)

def ucopytree(ossrc, osdst, symlinks=False):
    # ucopy2 dosn't work with unicode filename yet
    if type(osdst) is UnicodeType and \
            not os.path.supports_unicode_filenames:
        ossrc = ossrc.encode(FS_CHARSET)
        osdst = osdst.encode(FS_CHARSET)
    shutil.copytree(ossrc, osdst, symlinks)

def umove(ossrc, osdst):
    # umove dosn't work with unicode filename yet
    if type(osdst) is UnicodeType and \
           not os.path.supports_unicode_filenames:
        ossrc = ossrc.encode(FS_CHARSET)
        osdst = osdst.encode(FS_CHARSET)
    shutil.move(ossrc, osdst)

try:
    _v_network = str(socket.gethostbyname(socket.gethostname()))
except:
    _v_network = str(random() * 100000000000000000L)

def make_uuid(*args):
    t = str(time.time() * 1000L)
    r = str(random()*100000000000000000L)
    data = t +' '+ r +' '+ _v_network +' '+ str(args)
    uid = md5(data).hexdigest()
    return uid

