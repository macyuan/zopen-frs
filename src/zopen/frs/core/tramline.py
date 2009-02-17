# -*- encoding: UTF-8 -*-
import os, tempfile, random, sys, errno
from tramline2frs import processUploadResult, getDownloadPath, removeFiles, moveFiles, archiveFile, removeArchive

def tramline_path(req):
    return req.get_options()['tramline_path']

def tramline_upload_path(req):
    return os.path.join(tramline_path(req), 'upload')

def tramline_repository_path(req):
    return os.path.join(tramline_path(req), 'repository')

def create_paths(req):
    for p in [tramline_path(req),
              tramline_upload_path(req),
              tramline_repository_path(req)]:
        if not os.path.isdir(p):
            os.mkdir(p)

FILE_CHUNKSIZE = 8 * 1024

"""
inputfilter() and outputfilter() are what is called by Apache.

There can potentially (theoretically? it's hard to reproduce) be
multiple calls per request in the case of large amount of data being
uploaded. read() and readline() are not guaranteed to deliver all
data, but may just stop in the middle of a request. .read() may then
return an empty string. We know the filtering is actually done when
filter.read() returns None.

We make sure multiple calls to inputfilter and outputfilter in a
request end up together, i.e. the right FilterProcessor class
instance. We do this by tucking away a process-unique id inside the
request headers. This way we can identify we're actually a subsequent
call for an existing request request. The id is used to look up the
FilterProcessor class instance in the FilterRegistry and the data is
pushed into it.

Care is taken so that not too much memory is used when reading
in data. Apache turns out to read in chunks of about 8 kilobytes
typically, and at most this amount of data is kept in memory at any
one point. Data is written out as soon as possible.
"""

def no_filter(filter):
    """ 避免inputfilter死循环

    see: http://www.modpython.org/pipermail/mod_python/2007-August/024138.html
    """
    try:
        s = filter.read()
    except:
        return

    while s:
        filter.write(s)
        s = filter.read()

    if s is None:
        filter.close()

def inputfilter(filter):
    # we're done if we're in a subrequest
    if filter.req.main is not None:
        #filter.pass_on()
        no_filter(filter)
        return

    # we only handle POST requests
    # 仅仅将projects区域的内容保存到文件系统
    if filter.req.method != 'POST' or filter.req.uri.find('projects') == -1:
        #filter.pass_on()
        no_filter(filter)
        return

    # we only handle multipart/form-data
    enctype = filter.req.headers_in.get('Content-Type')
    if enctype[:19] != 'multipart/form-data':
        #filter.pass_on()
        no_filter(filter)
        return

    # check whether we have an id already
    id = filter.req.headers_in.get('tramline_id')

    if id is None:
        # no id, so create new processor instance and store
        # away id
        processor = theProcessorRegistry.createProcessor()
        filter.req.headers_in['tramline_id'] = str(processor.id)
    else:
        # reuse existing processor instance based on id
        processor = theProcessorRegistry.getProcessor(int(id))
        
    # read data from filter. Result can be a string, an empty string
    # or None.
    s = filter.read()
    while s:
        # as long as we have data, push it into processor
        processor.pushInput(s, filter)
        s = filter.read()
    # if we got no more data, this may mean we are broken in the middle
    # of a request. In that case, we're done for now, but inputfilter()
    # will be called again later
    if s is not None:
        return
    # s is None, so we are done with this request. Signal processor with
    # this so it can take special action if necessary
    processor.finalizeInput(filter)
    
    # we do not remove the processor yet from the registry nor the
    # tramline_id from the request header as this is done in the output phase.
    # The processor can retain state until then.

    # XXX One problem is that if output does not happen, we do not ever remove
    # the processor, causing a leak.
    
    # close the filter.
    filter.close()

def outputfilter(filter):
    # we're done if we're in a subrequset
    if filter.req.main is not None:
        filter.pass_on()
        filter.flush()
        return

    # in case of post request, we may need to do a commit/abort
    # of previous input round
    if filter.req.method == 'POST':
        outputfilter_post(filter)
        return
    # in case of a get request, we may need to serve up files,
    # depending on what's in the headers
    elif filter.req.method == 'GET':
        outputfilter_get(filter)
        return
    
    filter.pass_on()
    filter.flush()
    
def outputfilter_post(filter):

    if filter.req.status != 500 and \
                filter.req.headers_out.has_key('tramline_remove_archive'):
        removeArchive(filter.req.headers_out['tramline_remove_archive'])

    if filter.req.status != 500 and filter.req.headers_out.has_key('tramline_remove'):
        # log(filter.req.headers_out['tramline_remove'])
        removeFiles(filter.req.headers_out['tramline_remove'])

    if filter.req.status != 500 and filter.req.headers_out.has_key('tramline_move'):
        # log(filter.req.headers_out['tramline_move'])
        moveFiles(filter.req.headers_out['tramline_move'])

    if filter.req.status != 500 and filter.req.headers_out.has_key('tramline_archive'):
        # log(filter.req.headers_out['tramline_move'])
        archiveFile(filter.req.headers_out['tramline_archive'])

    

    # get id
    id = filter.req.headers_in.get('tramline_id')

    if id is None:
        # we're done now, just pass along data
        filter.pass_on()
        try:
            filter.flush()
        except:
            pass
        return

    # reuse existing processor instance based on id
    processor = theProcessorRegistry.getProcessor(int(id))

    is_ok = filter.req.headers_out.has_key('tramline_ok')
    if is_ok:
        # if the appserver said okay, 
        processor.commit(filter.req)
    else:
        # if the appserver didn't say okay
        processor.abort()

    # remove the processor id from the request now, as we're done with it
    theProcessorRegistry.removeProcessor(processor)
    
    # remove the id from the request as well
    del filter.req.headers_in['tramline_id']

    # now pass along the data.
    filter.pass_on()
    try:
        filter.flush()
    except:
        pass

def outputfilter_get(filter):
    # remove something?


    if filter.req.status != 500 and \
                filter.req.headers_out.has_key('tramline_remove_archive'):
        removeArchive(filter.req.headers_out['tramline_remove_archive'])

    # check whether we want to do file serving using tramline
    if not filter.req.headers_out.has_key('tramline_file'):
        filter.pass_on()
        #filter.flush()
        return
    # now read file id
    data = []
    s = filter.read()
    while s:
        data.append(s)
        s = filter.read()
    file_id = ''.join(data)

    # when show a image
    if not file_id:
        filter.pass_on()
        try:
            filter.flush()
        except:
            pass
        return

    # XXX what if file doesn't exist? 404?
    p = getDownloadPath(filter.req, file_id)
    size = os.stat(p).st_size
    filter.req.headers_out['content-length'] = str(size)
    # filter.req.sendfile(p)
    f = open(p, 'rb')
    while True:
        data = f.read(FILE_CHUNKSIZE)
        if not data:
            break
        filter.write(data)
        # flush the data out as soon as possible, so we don't
        # waste memory
        filter.flush()
    f.close()
    # close filter if last read is None
    if s is None:
        filter.close()
    
class ProcessorRegistry:
    def __init__(self):
        self._processors = {}

    def getProcessor(self, id):
        return self._processors[id]

    def createProcessor(self):
        # XXX thread issues?
        while True:
            id = random.randrange(sys.maxint)
            if id not in self._processors:
                break
        result = self._processors[id] = Processor(id)
        return result

    def removeProcessor(self, processor):
        del self._processors[processor.id]

theProcessorRegistry = ProcessorRegistry()

class Processor:
    def __init__(self, id):
        self.id = id
        self._upload_files = []
        self._incoming = []
        # we use a state pattern where the handle method gets
        # replaced by the current handle method for this state.
        self.handle = self.handle_first_boundary

    def pushInput(self, data, out):
        lines = data.splitlines(True)
        for line in lines:
            self.pushInputLine(line, out)

    def pushInputLine(self, data, out):
        # collect data
        self._incoming.append(data)
        # if we're not at the end of the line, input was broken
        # somewhere. We return to collect more first.
        if data[-1] != '\n':
            return
        # now use the line in whatever handle method is current
        if len(self._incoming) == 1:
            line = data
        else:
            line = ''.join(self._incoming)
        self._incoming = []

        self.handle(line, out)

    def finalizeInput(self, out):
        if self._upload_files:
            out.req.headers_in['tramline'] = ''

    def commit(self, req):
        # server internal error!
        if req.status == 500:
            del req.headers_out['tramline_ok']
            self.abort()
            return
        
        processUploadResult(req)

        # 清除tramline_ok的header
        del req.headers_out['tramline_ok']

        #for upload_file in self._upload_files:
        #    dummy, filename = os.path.split(upload_file)
        #    os.rename(upload_file,
        #              os.path.join(tramline_repository_path(req), filename))

    def abort(self):
        for upload_file in self._upload_files:
            os.remove(upload_file)
    
    def handle_first_boundary(self, line, out):
        self._boundary = line
        self._last_boundary = self._boundary.rstrip() + '--\r\n'
        self.init_headers()
        self.handle = self.handle_headers
        out.write(line)
        
    def init_headers(self):
        self._disposition = None
        self._disposition_options = {}
        self._content_type = 'text/plain'
        self._content_type_options = {}
        
    def handle_headers(self, line, out):
        out.write(line)
        if line in ['\n', '\r\n']:
            self.init_data(out)
            return
        key, value = line.split(':', 1)
        key = key.lower()
        if key == "content-disposition":
            self._disposition, self._disposition_options = parse_header(
                value)
        elif key == "content-type":
            self._content_type, self._content_type_options = parse_header(
                value)

    def init_data(self, out):
        filename = self._disposition_options.get('filename')
        # if filename is empty, assume no file is submitted and submit
        # empty file -- don't tramline this special case
        if filename is None or not filename:
            self.handle = self.handle_data
            return
        fd, pathname, file_id = createUniqueFile(out.req)
        self._f = os.fdopen(fd, 'wb')
        self._upload_files.append(pathname)
        out.write(pathname)
        #out.write('\r\n')
        
        self._previous_line = None
        self.handle = self.handle_file_data
        
    def handle_data(self, line, out):
        out.write(line)
        if line == self._boundary:
            self.init_headers()
            self.handle = self.handle_headers
        elif line == self._last_boundary:
            # we should be done
            self.handle = None # shouldn't be called again

    def handle_file_data(self, line, out):
        if line == self._boundary:
            # write last line, but without \r\n
            self._f.write(self._previous_line[:-2])
            size = self._f.tell()
            out.write('|%d' % size)
            out.write('\r\n')
            out.write(line)
            self._f.close()
            self._f = None
            self.handle = self.handle_headers
        elif line == self._last_boundary:
            # write last line, but without \r\n
            self._f.write(self._previous_line[:-2])
            size = self._f.tell()
            out.write('|%d' % size)
            out.write('\r\n')
            out.write(line)
            self._f.close()
            self._f = None
            self.handle = None # shouldn't be called again
        else:
            if self._previous_line is not None:
                self._f.write(self._previous_line)
            self._previous_line = line

def parse_header(s):
    l = [e.strip() for e in s.split(';')]
    result_value = l.pop(0).lower()
    result_d = {}
    for e in l:
        try:
            key, value = e.split('=', 1)
        except ValueError:
            continue
        key = key.strip().lower()
        value = value.strip()
        if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        result_d[key] = value
    return result_value, result_d

def createUniqueFile(req):
    """Create a file with unique file id in upload directory.

    Returns file descriptor, path, like tempfile.mkstemp, but in
    addition returns unique file id.
    """
    create_paths(req)
    # XXX we're relying on implementation of tempfile
    while True:
        file_id = str(random.randrange(sys.maxint))
        # do not accept files already known in the repository
        # this is normally not changing so this should be relatively
        # safe
        if os.path.exists(os.path.join(tramline_repository_path(req),
                                       file_id)):
            continue # try again
        path = os.path.join(tramline_upload_path(req), file_id)
        try:
            fd = os.open(path, tempfile._bin_openflags)
            tempfile._set_cloexec(fd)
            return fd, path, file_id
        except OSError, e:
            if e.errno == errno.EEXIST:
                continue # try again
            raise

def log(data):
    f = open('/var/www/tramline.log', 'ab')
    f.write(data)
    f.write('\n')
    f.close()
