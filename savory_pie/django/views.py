from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from savory_pie.context import APIContext
from savory_pie.formatters import JSONFormatter


def api_view(root_resource):
    """
    View function factory that provides accessing to the resource tree
    rooted at root_resource.

    The produced function needs to be bound into URLs as r'^some/base/path/(.*)$'
    """
    if root_resource.resource_path is None:
        root_resource.resource_path = ''

    @csrf_exempt
    def view(request, resource_path):
        full_path = _strip_query_string(request.get_full_path())
        if len(resource_path) == 0:
            base_path = full_path
        else:
            base_path = full_path[:-len(resource_path)]

        ctx = APIContext(
            base_uri=request.build_absolute_uri(base_path),
            root_resource=root_resource,
            formatter=JSONFormatter()
        )

        try:
            resource = ctx.resolve_resource_path(resource_path)

            if resource is None:
                return _not_found(ctx, request)

            if request.method == 'GET':
                return _process_get(ctx, resource, request)
            elif request.method == 'POST':
                return _process_post(ctx, resource, request)
            elif request.method == 'PUT':
                return _process_put(ctx, resource, request)
            elif request.method == 'DELETE':
                return _process_delete(ctx, resource, request)
            else:
                return _not_allowed_method(ctx, resource, request)
        except:
            import traceback
            return _internal_error(ctx, request, traceback.format_exc())

    return view


def _strip_query_string(path):
    return path.split('?', 1)[0]


def _process_get(ctx, resource, request):
    if 'GET' in resource.allowed_methods:
        content_dict = resource.get(ctx, _ParamsImpl(request.GET))
        return _content_success(ctx, resource, request, content_dict)
    else:
        return _not_allowed_method(ctx, resource, request)

def _process_post(ctx, resource, request):
    if 'POST' in resource.allowed_methods:
        new_resource = resource.post(ctx, ctx.formatter.read_from(request))
        return _created(ctx, request, request, new_resource)
    else:
        return _not_allowed_method(ctx, resource, request)

def _process_put(ctx, resource, request):
    if 'PUT' in resource.allowed_methods:
        resource.put(ctx,ctx.formatter.read_from(request))
        return _no_content_success(ctx, request, request)
    else:
        return _not_allowed_method(ctx, resource, request)

def _process_delete(ctx, resource, request):
    if 'DELETE' in resource.allowed_methods:
        resource.delete()
        return _success(ctx, request, request)
    else:
        return _not_allowed_method(ctx, resource, request)


def _not_found(ctx, request):
    return HttpResponse(status=404)

def _not_allowed_method(ctx, resource, request):
    response = HttpResponse(status=405)
    response['Allowed'] = ','.join(resource.allowed_methods)
    return response

def _created(ctx, resource, request, new_resource):
    response = HttpResponse(status=201)
    response['Location'] = ctx.build_resource_uri(new_resource)
    return response

def _content_success(ctx, resource, request, content_dict):
    response = HttpResponse(status=200, content_type=ctx.formatter.content_type)
    ctx.formatter.write_to(content_dict, response)
    return response

def _no_content_success(ctx, resource, request):
    return HttpResponse(status=204)

def _success(ctx, resource, request, content_dict=None):
    return HttpResponse(status=200)

def _internal_error(ctx, request, error):
    response = HttpResponse(status=500, content_type=ctx.formatter.content_type)
    error_body = { ctx.formatter.default_published_property('error'): error }
    ctx.formatter.write_to(error_body, response)
    return response


class _ParamsImpl(object):
    def __init__(self, GET):
        self._GET = GET

    def get(self, key, default=None):
        return self._GET.get(key, default)

    def get_as(self, key, type, default=None):
        value = self._GET.get(key, None)
        return default if value is None else type(value)

    def get_list(self, key):
        list = self._GET.get(key, None)
        return [] if list is None else list

    def get_list_of(self, key, type):
        list = self._GET.get(key, None)
        if list is None:
            return []
        else:
            return [type(x) for x in list]

