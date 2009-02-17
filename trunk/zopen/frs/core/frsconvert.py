# -*- encoding:utf-8 -*-
import os,sys
import simplejson as json
from types import ListType
from gnosis.xml.objectify import XML_Objectify

from zopen.frs.core.frs import FRS
from zopen.frs.core.manifest import Manifest
from zopen.frs.core.metadata import Metadata
from zopen.frs.core.jsonutils import AwareJSONEncoder



def frsConvert():
    ospath = os.path.normpath(sys.argv[1])
    frs = FRS()
    traverlpaths = []
    for dirpath, dirnames, filenames in os.walk(ospath):
        traverlpaths.append(dirpath)
        if dirpath == ospath:
            traverlpaths.remove(dirpath)
        if ".frs" in dirpath:
            traverlpaths.remove(dirpath)
            continue
        for filename in filenames:
            traverlpaths.append(os.path.join(dirpath,filename))

    for dirpath in traverlpaths:
        print dirpath,10*'-'
        manifestpath =  frs.manifestpath(dirpath)
        print manifestpath,10*'*'
        mf = Manifest()
        mf.load(file(manifestpath).read())
        print 'contenttype:', mf.contenttype
        print 'uid: ', mf.uid
        print 'manifest:', mf.manifest
        metadata = {}
        metadata['main']={}
        metadata['main']['contenttype'] = mf.contenttype
        metadata['dublin']={}
        for item in mf.manifest:
            if item['name']:
                metadata['main']['mimetype'] = item['mimetype']
            else:
                filename = item['fullpath']
                subfilepath = frs.subfilespath(dirpath,filename)
                xml_obj = XML_Objectify(subfilepath).make_instance()
                if hasattr(xml_obj,"cmf_type"):
                     metadata['main']['contenttype'] = xml_obj.cmf_type.PCDATA
                if hasattr(xml_obj,"dc_creator"):
                    metadata['dublin']['creators'] = ["users."+xml_obj.dc_creator.PCDATA]
                if hasattr(xml_obj,"dc_title"):
                    metadata['dublin']['title'] = xml_obj.dc_title.PCDATA
                if hasattr(xml_obj,"dc_language"):
                    metadata['dublin']['language'] =xml_obj.dc_language.PCDATA
                if hasattr(xml_obj,"dc_subject"):
                    metadata['dublin']['subjects'] = [subject.PCDATA for subject in xml_obj.dc_subject]
                if hasattr(xml_obj,"dc_description"):
                    metadata['dublin']['description'] = xml_obj.dc_description.PCDATA
                if hasattr(xml_obj,"xmp_CreateDate"):
                    metadata['dublin']['created'] = xml_obj.xmp_CreateDate.PCDATA
                if hasattr(xml_obj,"xmp_ModifyDate"):
                    metadata['dublin']['modified'] = xml_obj.xmp_ModifyDate.PCDATA
                for field in xml_obj.field:
                    if field.id == "effectiveDate":
                        metadata['dublin']['effective'] = field.PCDATA

        metadatapath =  frs.metadatapath(dirpath)
        fd = file(metadatapath,"w")
        json.dump(metadata,fd,ensure_ascii=False,indent=4,cls=AwareJSONEncoder)
        fd.close()
