import contextlib
from dateutil import parser


class APIContext(object):
    """
    Context object passed as the second argument (after self) to Resources and Fields.

    The context object provides a hook into the underlying means to translates
    resources to / from URIs.

    The context has a streaming_response attribute which defaults to False. If
    this is set to True the get method of the resource should not return a
    dict, but an iterable of strings. It is the job of the resource to make
    sure the content_type of the request, ctx.formatter.content_type is
    respected. This can be used as a performance improvement when returning
    large result sets where fragments of them can be pre-computed/cached and
    stitched in to a final result.
    """
    def __init__(self, base_uri, root_resource, formatter, request=None):
        self.base_uri = base_uri
        self.root_resource = root_resource
        self.formatter = formatter
        self.request = request
        self.headers_dict = {}
        self.object_stack = []
        self.streaming_response = False

    def resolve_resource_uri(self, uri):
        """
        Resolves the resource that corresponds to the current URI,
        but only within the same resource tree.
        """
        if not uri.startswith(self.base_uri):
            return None

        return self.resolve_resource_path(uri[len(self.base_uri):])

    def resolve_resource_path(self, resource_path):
        """
        Resolves a resource using a resource path (not a full URI),
        but only within the same resource tree.
        """
        resource = self.root_resource
        cur_resource_path = ''

        for path_fragment in _split_resource_path(resource_path):
            cur_resource_path = cur_resource_path + '/' + path_fragment
            resource = resource.get_child_resource(self, path_fragment)

            if not resource:
                return None

            if resource.resource_path is None:
                resource.resource_path = cur_resource_path

        return resource

    def build_resource_uri(self, resource):
        """
        Given a Resource with a resource_path, provides the correspond URI.
        Raises a ValueError if the resource_path of the Resource is None.
        """
        resource_path = resource.resource_path

        if resource_path is None:
            raise ValueError(u'unaddressable resource')

        return self.base_uri + resource_path

    def set_header(self, header, value):
        """
        Updates self.header_dict property for processing in the view where the Response headers should be set from
        header_dict
        """
        self.headers_dict[header] = value
        return self.headers_dict

    def set_expires_header(self, new_expires):
        current_expires = self.headers_dict.get('Expires', new_expires)

        expires_date = min(
            [current_expires, new_expires],
            key=lambda expires: parser.parse(expires) if isinstance(expires, basestring) else expires
        )
        self.set_header('Expires', expires_date)

    @contextlib.contextmanager
    def target(self, target):
        self.push(target)
        yield
        self.pop()

    def push(self, target):
        self.object_stack.append(target)

    def pop(self):
        return self.object_stack.pop()

    def peek(self, n=1):
        return self.object_stack[-n]


def _split_resource_path(resource_path):
    path_fragments = resource_path.split('/')
    if path_fragments[-1] == '':
        return path_fragments[:-1]
    else:
        return path_fragments
