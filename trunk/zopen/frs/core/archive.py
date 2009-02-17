""" asset archive management
"""
import time
from xml.sax import parseString, ContentHandler

from utils import timetag
from config import FRS_ARCHIVED_FOLDER_NAME, FRS_ARCHIVE_INFO_FILE_NAME

from string import Template


archive_template = Template("""<?xml version="1.0" ?>
<archive xmlns="http://zopechina.com/ns/frs"
         filename="$filename"
         actor="$actor"
         time="$time"><![CDATA[$comment]]></archive>
""")

class ArchiveInfo:

    def __init__(self, id='', **kw):
        self.id = id
        self.archive = kw
        self.archive['time'] = kw.get('time', time.strftime('%Y-%m-%d %H:%M:%S'))

    def load(self, manifest_body):
        print 'loading archive info ........................'
        parser = ArchiveParser(self)
        parseString( manifest_body, parser)

    def write2xml(self, stream):
        xml_str = archive_template.substitute(**self.archive)
        stream.write(xml_str.encode('utf8'))

class ArchiveParser( ContentHandler ):
    
    def __init__(self, archiveinfo=None):
        self._ai = archiveinfo or ArchiveInfo()
        self._chars = []

    def getArchiveInfo(self):
        return self._ai

    def startElement(self, name, attrs):
        if name == 'archive':
            self._ai.archive['actor'] = attrs.get('actor', '')
            self._ai.archive['time'] = attrs.get('time', '')
            self._ai.archive['filename'] = attrs.get('filename', '')

    def endElement( self, name ):
        if name == 'archive':
            self._ai.archive['comment'] = "".join(self._chars).strip()
        self._chars = []

    def characters( self, buffer ):
        self._chars.append( buffer )

class ArchiveSupportMixin:

    def archivedpath(self, path, *args):
        return self.frspath(path, FRS_ARCHIVED_FOLDER_NAME, *args)

    def archiveinfopath(self, path):
        return self.frspath(path, FRS_ARCHIVE_INFO_FILE_NAME)

    def archive(self, path, id=None, **archiveInfo):
        archivePath = self.archivedpath(path)
        if not self.exists(archivePath):
            self.makedirs(archivePath)


        if not id:
            ext = self.splitext(path)[-1]
            id = timetag() + ext
        dstpath = self.joinpath(archivePath, id)
        self.copyAsset(path, dstpath, copycache=0, copy_archiveinfo=0)

        ai_path = self.archiveinfopath(dstpath)
        ai = ArchiveInfo(id=id, filename=self.basename(path), **archiveInfo)
        ai.write2xml(open(self.ospath(ai_path), 'w'))

    def listArchives(self, path):
        archivePath = self.archivedpath(path)
        if self.exists(archivePath):
            archives = self.listdir(archivePath)
        else:
            archives = []
        if self.exists(self.archiveinfopath(path)):
            archives.append('')
        return archives

    def getArchiveInfo(self, path, archivename):
        if archivename == '':
            ai_path = self.archiveinfopath(path)
        else:
            ai_path = self.archiveinfopath(self.archivedpath(path, archivename))
        ai = ArchiveInfo(id=archivename)
        try:
            ai.load(open(self.ospath(ai_path)).read() )
        except IOError:
            pass
        return ai.archive

    def copyArchive(self, path, archiveName, dstPath):
        assetpath = self.archivedpath(path, archiveName)
        return self.copyAsset(assetpath, dstPath, copycache=0, copy_archiveinfo=0)

    def removeArchive(self, path, archiveName):
        self.removeAsset( self.archivedpath(path, archiveName) )

if __name__ == '__main__':
    ai = ArchiveInfo(id='asdfasdfas', time='2003-12-23', actor='panjy', comment='asdjas asd f as df', filename='aa.txt')
    from StringIO import StringIO
    stream = StringIO()
    ai.write2xml(open('sample-archive-info.xml', 'w'))

    print stream.getvalue()
    ai = ArchiveInfo(id='asdfasdfas')
    ai.load(open('sample-archive-info.xml').read())
    print ai.archive

