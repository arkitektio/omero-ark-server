# Create your views here.
from django.http.response import HttpResponseForbidden
from django.http import HttpResponseForbidden, StreamingHttpResponse
from .decorators import omero_connected
from django.http import HttpResponse, Http404
from .conn import get_conn
from django.conf import settings
from django.views.decorators.cache import cache_page


CACHE_TTL = getattr(settings, 'CACHE_TTL_DEFAULT', 60 * 15)  # 15 minutes


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







def _render_thumbnail(id, size=None):
    """
    Returns a jpeg with the rendered thumbnail for image 'iid'

    @param request:     http request
    @param iid:         Image ID
    @return:            http response containing jpeg
    """

    conn = get_conn()

    size = size or (200,)


    img = conn.getObject("Image", id)
    if img is None:
        logger.debug("(b)Image %s not found..." % (str(id)))
        raise Http404("Failed to render thumbnail")
    else:
        jpeg_data = img.getThumbnail(
            size=size, direct=True, rdefId=None, z=0, t=0
        )
        if jpeg_data is None:
            raise Http404("Failed to render thumbnail")

    return jpeg_data






@omero_connected
@cache_page(CACHE_TTL)
def render_thumbnail(request, id):
    """
    Returns an HttpResponse wrapped jpeg with the rendered thumbnail for image
    'iid'

    @param request:     http request
    @param iid:         Image ID
    """
    print(request)
    jpeg_data = _render_thumbnail(
         id=id,
         size=request.GET.get("size", (200,))
    )
    rsp = HttpResponse(jpeg_data, content_type="image/jpeg")
    return rsp












