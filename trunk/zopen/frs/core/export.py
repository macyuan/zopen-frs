# -*- encoding:utf-8 -*-
import simplejson as json
import os

def getMetadata(self):
    """
    导出格式为:
    [{'title':title,'creator':creator,'contenttype':contenttype,'id':id,'modified':modified},{}]
    """
    info = []
    for obj in self.contentValues():
        metadata = {}
        metadata['id'] = unicode(obj.getId())
        metadata['title'] = unicode(obj.Title())
        metadata['creator'] = unicode(obj.Creator())
        metadata['description'] = unicode(obj.Description())
        metadata['modified'] = obj.modified().strftime("%Y-%m-%d %H:%M:%S")
        metadata['contenttype']= unicode(obj.getPortalTypeName())
        if metadata['contenttype'] == 'Image':
            metadata['mimetype'] = unicode(obj.getContentType())
            metadata['data'] = str(obj.getRawImage().data)
        elif metadata['contenttype'] == 'Document':
            metadata['mimetype'] = unicode(obj.getContentType())
            metadata['data'] = unicode(obj.getRawText())
            if self.getDefaultPage() == obj.getId():
                metadata['id'] = 'index.rst'
        elif metadata['contenttype'] == 'News Item':
            metadata['mimetype'] = unicode(obj.getContentType())
            metadata['data'] = unicode(obj.CookedBody())
        elif metadata['contenttype'] == 'File':
            metadata['mimetype'] = unicode(obj.getContentType())
            metadata['data'] = str(obj.getRawFile().data)
        elif metadata['contenttype']== 'Folder':
            subobject = getMetadata(obj)
            metadata['subobject'] = subobject
            metadata['keys'] = [ (key == obj.getDefaultPage() and 'index.rst' or \
                    key) for key in obj.contentIds()]
            metadata['hidden_keys'] = [ (item.getId() == obj.getDefaultPage() \
                and 'index.rst' or item.getId() ) for item in \
                    obj.contentValues() if item.getExcludeFromNav()]
        else:
            continue

        info.append(metadata)

    return info

def export(self):
    dump_root = os.path.join(os.environ['INSTANCE_HOME'], 'var', 'frsdump')
    if not os.path.exists(dump_root):
        os.makedirs(dump_root)
    os.chdir(dump_root)
    info = getMetadata(self)
    try:
        frsexport(info)
    except Exception ,e:
        return e
    return "export success!"

def frsexport(all_files):
    #先导出当前层次的文件
    for newfile in all_files:
        if newfile['contenttype']!='Folder':
            mkfile(newfile)
    for newfolder in all_files:
        if newfolder['contenttype']=='Folder':
            dirpath = mkfolder(newfolder)
            oldpath = os.getcwd()
            os.chdir(dirpath)
            frsexport(newfolder['subobject'])
            os.chdir(oldpath)

def mkfolder(newfile):
    metadata = {}
    metadata['main'] = {}
    metadata['dublin'] = {}
    metadata['main']['id'] = newfile['id']
    metadata['main']['contenttype'] = newfile['contenttype']
    metadata['dublin']['title'] = newfile['title']
    metadata['dublin']['description'] = newfile['description']
    metadata['dublin']['creators'] = (newfile['creator'],)
    metadata['dublin']['modified'] = newfile['modified']
    os.mkdir(newfile['id'])
    frspath = os.path.join(os.getcwd(),'.frs',newfile['id'])
    if not os.path.exists(frspath):
        os.makedirs(frspath)
    metadatapath = os.path.join(frspath,'metadata.json')
    f = file(metadatapath,'wb')
    json.dump(metadata,f,ensure_ascii=False,indent=4)
    f.close()
    dirpath = os.path.join(os.getcwd(),newfile['id'])
    return dirpath

def mkfile(newfile):
    metadata = {}
    metadata['main'] = {}
    metadata['dublin'] = {}
    metadata['main']['id'] = newfile['id']
    metadata['main']['contenttype'] = newfile['contenttype']
    metadata['main']['mimetype'] = newfile['mimetype']
    metadata['dublin']['title'] = newfile['title']
    metadata['dublin']['description'] = newfile['description']
    metadata['dublin']['creators'] = (newfile['creator'],)
    metadata['dublin']['modified'] = newfile['modified']
    out = file(newfile['id'],'w')
    out.write(newfile['data'])
    out.close()
    frspath = os.path.join(os.getcwd(),'.frs',newfile['id'])
    if not os.path.exists(frspath):
        os.makedirs(frspath)
    metadatapath = os.path.join(frspath,'metadata.json')
    f = file(metadatapath,'w')
    json.dump(metadata,f,ensure_ascii=False,indent=4)
    f.close()

