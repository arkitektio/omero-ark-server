# Create your views here.
from authentikate.utils import authenticate_header_or_none, 
from django.http.response import HttpResponseForbidden
from django.http import HttpResponseForbidden, StreamingHttpResponse

import logging

logger = logging.getLogger(__name__)  #


class ConnCleaningHttpResponse(StreamingHttpResponse):
    """Extension of L{HttpResponse} which closes the OMERO connection."""

    def close(self):
        super(ConnCleaningHttpResponse, self).close()
        try:
            logger.debug("Closing OMERO connection in %r" % self)
            if self.conn is not None and self.conn.c is not None:
                self.conn.close(hard=False)
        except Exception:
            logger.error("Failed to clean up connection.", exc_info=True)



def file_download_view(request, id):
    """
    A dataset is a collection of data files and metadata files.
    It mimics the concept of a folder in a file system and is the top level
    object in the data model.

    """
    pass

    user = authenticate_header_or_none(request.headers)
    if not user:
        return HttpResponseForbidden("Not authenticated")





    rsp = ConnCleaningHttpResponse(
            orig_file.getFileInChunks(buf=settings.CHUNK_SIZE)
        )
    rsp.conn = conn
    rsp["Content-Length"] = orig_file.getSize()
    # ',' in name causes duplicate headers
    fname = orig_file.getName().replace(" ", "_").replace(",", ".")
    rsp["Content-Disposition"] = "attachment; filename=%s" % (fname)