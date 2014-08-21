from savory_pie.fields import URIResourceField, URIListResourceField
from savory_pie.django.fields import RelatedManagerField


def uri_auth_adapter(field, ctx, source_dict, target_obj):
    """
    Authorization adapter for use in fields representing a 1 to many relationship.  Is used when you want to prevent
    unauthorized users from changing the associations of different models.
    """
    name = field._compute_property(ctx)
    source_field = source_dict[name]
    target_field = getattr(target_obj, field.name)
    source = None
    target = None

    if source_field and target_field:
        if isinstance(field, RelatedManagerField):
            source = [source_field_item['resourceUri'] for source_field_item in source_field]
            target = [ctx.build_resource_uri(field._resource_class(target_item)) for target_item in target_field.all()]
            source.sort()
            target.sort()
        elif isinstance(field, URIResourceField):
            source = source_field
            target = ctx.build_resource_uri(field._resource_class(target_field))
        elif isinstance(field, URIListResourceField):
            source = source_field
            target = [ctx.build_resource_uri(field._resource_class(target_item)) for target_item in target_field.all()]
            source.sort()
            target.sort()
        else:
            raise TypeError('uri_auth_adapter can only be used with fields of type URIResourceField,' +
                            ' URIListResourceField or RelatedManagerField')

    return name, source, target


class DjangoUserPermissionValidator(object):
    """
    Permissions Validator is used to tie into an authorization.  Is used in conjunction with the authorization decorator
    Added to the field init method.
    """
    def __init__(self, permission_name, auth_adapter=None):
        self.permission_name = permission_name
        self.auth_adapter = auth_adapter

    def is_write_authorized(self, ctx, target_obj, source, target):
        """
        Leverages the users has_perm(key) method to leverage the authorization.
        Only check if the source and target have changed.
        """
        user = ctx.request.user

        if source != target:
            return user.has_perm(self.permission_name)

        return True

    def fill_schema(self, schema_dict):
        # TODO: implement fill_schema
        pass
