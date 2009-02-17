# -*- encoding: UTF-8 -*-
import os,sys

reload(sys)
sys.setdefaultencoding('utf-8')
del sys.setdefaultencoding

import PIL.Image

frs_conf = """[cache]
path=/var/everydo-frscache

[root]
sites = /var/everydo-frs

[site]
/=/sites
"""

from zopen.frs.core import loadFRSFromConfig
frs = loadFRSFromConfig(frs_conf)

sizes= {'large'   : (768, 768),
        'preview' : (400, 400),
        'mini'    : (200, 200),
        'thumb'   : (128, 128),
        'tile'    :  (64, 64),
        'icon'    :  (32, 32),
        'listing' :  (16, 16),
       }

def processUploadResult(req):
    ok_info = req.headers_out['tramline_ok']
    # ok_info id:vpath:oprations|id:vpath:options

    for file_info in ok_info.split('|'):
        ospath, zpath, operations = file_info.split(':')
        #tramline_path = req.get_options()['tramline_path']
        #ospath = os.path.join(tramline_path, 'upload', id)
        dst_ospath = moveToFRS(ospath, zpath)

        if 's' in operations: # 进行图片预览处理操作
            vpath = frs.sitepath2Vpath(zpath)
            isf = frs.getCacheFolder(vpath, 'imagescales')

            if not os.path.exists(isf):
                os.makedirs(isf)
                filenames = []
            else:
                filenames = os.listdir(isf)

            for size in sizes:
                filename = "image_%s" % size
                
                # remove old caches
                if filename in filenames:
                    os.remove(os.path.join(isf, filename))

                fullpath = os.path.join(isf, filename)
                scale(dst_ospath, fullpath, sizes[size])

def getDownloadPath(req, zpath):
    splitted = zpath.split(':')
    zpath = splitted[0]
    vpath = frs.sitepath2Vpath(zpath)
    if len(splitted) == 1:
       try:
           #把虚拟文件系统上的路径转为真实文件系统的路径
           return frs.ospath(vpath)
       except:
           raise zpath
    else:
        zpath, namespace, cachename, filename = splitted
        if namespace == 'cache':
        # 不同大小的图片
            cachefolderpath = frs.getCacheFolder(vpath, cachename)
            return os.path.join(cachefolderpath, filename)
        elif namespace == 'archive':
        # 支持中间版本的下载
            archiveName = filename
            archiveFilePath = frs.archivedpath(vpath, archiveName)
            return frs.ospath(archiveFilePath)

def moveToFRS(ospath, zpath):
    vpath = frs.sitepath2Vpath(zpath)
    dst_ospath = frs.ospath(vpath)
    dir = os.path.dirname(dst_ospath)
    if not os.path.exists(dir):
        os.makedirs(dir)
    os.rename(ospath, dst_ospath)
    return dst_ospath

def scale(original_file, thumbnail_file, size, default_format = 'PNG'):
    try:
        image = PIL.Image.open(original_file)
    except IOError:
        # XXX 删除现有的 scale图片
        return 

    # consider image mode when scaling
    # source images can be mode '1','L,','P','RGB(A)'
    # convert to greyscale or RGBA before scaling
    # preserve palletted mode (but not pallette)
    # for palletted-only image formats, e.g. GIF
    # PNG compression is OK for RGBA thumbnails
    original_mode = image.mode
    if original_mode == '1':
        image = image.convert('L')
    elif original_mode == 'P':
        image = image.convert('RGBA')
    image.thumbnail(size, PIL.Image.ANTIALIAS)
    format = image.format and image.format or default_format
    # decided to only preserve palletted mode
    # for GIF, could also use image.format in ('GIF','PNG')
    if original_mode == 'P' and format == 'GIF':
        image = image.convert('P')
    # quality parameter doesn't affect lossless formats
    image.save(thumbnail_file, format, quality=88)

def removeFiles(tramline_remove_string):
    zpaths = tramline_remove_string.split(':')
    vpaths = [frs.sitepath2Vpath(zpath) for zpath in zpaths]

    for vpath in vpaths:
        frs.removeAsset(vpath)

        #basename = frs.basename(vpath)
        #pathname = frs.dirname(vpath)
        #frs.recycleAssets(pathname, [basename])

def removeArchive(tramline_remove_archive_string):
    zpath, archiveName = tramline_remove_archive_string.split('|', 1)
    vpath = frs.sitepath2Vpath(zpath)
    frs.removeArchive(vpath, archiveName)

def moveFiles(tramline_move_string):
    paths = tramline_move_string.split('|')

    for path in paths:
        zpath_from, zpath_to = path.split(':')
        vpath_from = frs.sitepath2Vpath(zpath_from)
        vpath_to = frs.sitepath2Vpath(zpath_to)

        try:
            frs.moveAsset(vpath_from, vpath_to)
        except:
            log('move error:' + vpath_from + ' to ' + vpath_to)

def archiveFile(tramline_archive_string):
    zpath,actor,id,comment = tramline_archive_string.split('|', 3)
    vpath = frs.sitepath2Vpath(zpath)
    frs.archive(vpath, comment=comment, id=id, actor=actor)

def log(data):
    f = open('/var/www/tramline.log', 'ab')
    f.write(data)
    f.write('\n')
    f.close()

