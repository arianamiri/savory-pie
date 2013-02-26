class APIContext(object):
    """
    Context object passed as the second argument (after self) to Resources and Fields.

    The context object provides a hook into the underlying means to translates
    resources to / from URIs.
    """
    def __init__(self, base_uri, root_resource, formatter):
        self.base_uri = base_uri
        self.root_resource = root_resource

        self.formatter = formatter

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
        if resource.resource_path is None:
            raise ValueError, 'unaddressable resource'

        return self.base_uri + resource.resource_path


def _split_resource_path(resource_path):
    path_fragments = resource_path.split('/')
    if path_fragments[-1] == '':
        return path_fragments[:-1]
    else:
        return path_fragments