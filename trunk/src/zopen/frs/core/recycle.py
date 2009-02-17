from config import FRS_REMOVED_FOLDER_NAME
from utils import timetag
import datetime
import time

class RecycleMixin:
    """ trushcase enables mixin for file repository system 
    """

    def removedpath(self, path, *args):
        return self.frspath( self.joinpath(path, FRS_REMOVED_FOLDER_NAME), *args)

    def recycleAssets(self, path, srcNames):
        """ remove file or tree to trush folder """
        removedPath = self.removedpath(path, timetag() )
        for name in srcNames:
            srcPath = self.joinpath(path, name)
            dstPath = self.joinpath(removedPath, name)
            self.moveAsset(srcPath, dstPath)

    def listRemoves(self, path):
        removedPath = self.removedpath(path)
        if not self.exists(removedPath):
            return []
        return self.listdir(removedPath)

    def listRemovedAssets(self, path, removeName):
        removedPath = self.removedpath(path, removeName)
        return self.listdir(removedPath)

    def revertRemove(self, path, removeName, assetNames=[]):
        removedPath = self.removedpath(path, removeName)
        if not assetNames:
            assetNames = self.listdir(removedPath)
        for name in assetNames:
            srcPath = self.joinpath(removedPath, name)
            dstPath = self.joinpath(path, self.getNewName(path, name))
            self.moveAsset(srcPath, dstPath)

        if not self.listdir(removedPath):
            self.rmtree(removedPath)

    def realRemove(self, path, removeName, assetNames=[]):
        removedPath = self.removedpath(path, removeName)
        if not assetNames:
            self.rmtree(removedPath)
	    return 

        for name in assetNames:
            srcPath = self.joinpath(removedPath, name)
            self.removeAsset(srcPath)
        if not self.listdir(removedPath):
            self.rmtree(removedPath)

    def walkTrashBox(self, top_path='/', days=0, cmp_result=0):
        """ -1: older than history day; 0: all; 1: greater than history day 
        """
        cur_date = datetime.datetime(*time.gmtime()[:7])
        history_date = cur_date - datetime.timedelta(days)
        history_date_name = timetag(history_date)

        if top_path != '/':
            removeNames = self.listRemoves(top_path)
            if cmp_result != 0:
                removeNames = [removeName for removeName in removeNames
                            if cmp(removeName, history_date_name) == cmp_result]
            if removeNames:
                yield top_path, removeNames

        for parent_path, dirnames, filenames in self.walk(top_path):
            for dirname in dirnames:
                dir_vpath = self.joinpath(parent_path, dirname)
                removeNames = self.listRemoves(dir_vpath)
                if cmp_result != 0:
                    removeNames = [removeName for removeName in removeNames
                            if cmp(removeName, history_date_name) == cmp_result]
                if removeNames:
                    yield dir_vpath, removeNames

    def cleanTrushBox(self, top_path='/', days=30, cmp_result=-1):
        """ delete all items in trushboxes older than <keepDays> """
        for dir_vpath, remove_names in self.walkTrashBox(top_path, days, cmp_result):
            for remove_name in remove_names:
                self.realRemove(dir_vpath, remove_name)

