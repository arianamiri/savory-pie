from savory_pie.errors import AuthorizationError


def authorization_adapter(field, ctx, source_dict, target_obj):
    """
    Default adapter works on single field (non iterable)
    """
    name = field._compute_property(ctx)
    source = field.to_python_value(ctx, source_dict[name])
    target = field.to_python_value(ctx, field._get(target_obj))
    return name, source, target


def datetime_auth_adapter(field, ctx, source_dict, target_obj):
    """
    Adapter for fields of date/datetime/time
    """
    name = field._compute_property(ctx)
    source = field.to_python_value(ctx, source_dict[name])
    target = field._get(target_obj)
    return name, source, target


def subobject_auth_adapter(field, ctx, source_dict, target_obj):
    """
    Adapter for fields of savory_pie.fields.SubObjectResourceField, or subclasses thereof
    """
    name = field._compute_property(ctx)
    if source_dict[name] is not None:
        source = source_dict[name]['resourceUri']
    else:
        source = None
    # this is essentially the same logic as in field.get_subresource(), but
    # ignores source_dict as we're only interested in target's resourceUri
    target_subobject = getattr(target_obj, field.name)
    if target_subobject is not None:
        target = ctx.build_resource_uri(field._resource_class(target_subobject))
    else:
        target = None
    return name, source, target


def uri_auth_adapter(field, ctx, source_dict, target_obj):
    """
    Adapter for fields of type savory_pie.fields.URIResourceField
    """
    name = field._compute_property(ctx)
    source = source_dict.get(name, None)
    target_field = getattr(target_obj, field.name, None)

    if target_field:
        target = ctx.build_resource_uri(field._resource_class(target_field))
    else:
        target = None

    return name, source, target


def urilist_auth_adapter(field, ctx, source_dict, target_obj):
    """
    Adapter for fields of type savory_pie.fields.URIListResourceField
    """
    name = field._compute_property(ctx)
    source = source_dict.get(name, None)
    target_field = getattr(target_obj, field.name, None)

    if source:
        source.sort()

    if target_field:
        target = sorted([ctx.build_resource_uri(field._resource_class(target_item))
                         for target_item in target_field.all()])
    else:
        target = None

    return name, source, target


class authorization(object):
    """
    Authorization decorator, takes a permission dictionary key and an adapter function
    @auth_adapter: an adapter function that takes ctx, source_dict, target_obj and
        returns ctx, target_obj, source, target parameters

        Use:
            @authorization(adapter)

    """
    def __init__(self, auth_adapter):
        self.auth_adapter = auth_adapter

    def __call__(self, fn):
        """
        If the user does not have an the authorization raise an AuthorizationError
        """
        def inner(field, ctx, source_dict, target_obj):
            permission = field.permission
            if permission:
                auth_adapter = getattr(permission, 'auth_adapter', None) or self.auth_adapter
                name, source, target = auth_adapter(field, ctx, source_dict, target_obj)
                if not permission.is_write_authorized(ctx, target_obj, source, target):
                    raise AuthorizationError(name)

            return fn(field, ctx, source_dict, target_obj)

        return inner
