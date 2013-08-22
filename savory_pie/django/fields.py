import collections
import logging

import django.core.exceptions
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields import FieldDoesNotExist
from django.utils.functional import Promise

from savory_pie import fields as base_fields
from savory_pie.errors import SavoryPieError
from savory_pie.django.validators import ValidationError

logger = logging.getLogger(__name__)


class DjangoField(base_fields.Field):
    def schema(self, ctx, **kwargs):
        model = kwargs['model']
        field_name = (model._meta.pk.name if self.name == 'pk' else self.name)
        # TODO: need to remove _field, field is a global state, we should not be changing it on an instance level
        self._field = None
        try:
            self._field = model._meta.get_field(field_name)
        except:
            # probably only for m2m fields
            try:
                self._field = model._meta.get_field_by_name(field_name)[0].field
            except FieldDoesNotExist:
                self._field = None

        schema = super(DjangoField, self).schema(ctx, **kwargs)
        if isinstance(self.validator, collections.Iterable):
            schema['validators'] = [validator.to_schema() for validator in self.validator]
        else:
            schema['validators'] = [self.validator.to_schema()]

        if self._field:
            _schema = {
                'blank': self._field.blank,
                'default': ctx.formatter.to_api_value(type(self._field.get_default()), self._field.get_default()),
                'helpText': self._field.help_text,
                'nullable': self._field.null,
                'readonly': not self._field.editable,
                'unique': self._field.unique
            }
            if self._field.choices:
                _schema['choices'] = self._field.choices
            if isinstance(_schema['helpText'], Promise):
                _schema['helpText'] = unicode(_schema['helpText'])
        else:
            _schema = {}

        return dict(schema.items() + _schema.items())


class AttributeField(base_fields.AttributeField, DjangoField):
    """
    Django extension of the basic AttributeField that adds support for optimized select_related
    or prefetch_related calls.

    Parameters:
            :class:`savory_pie.fields.AttributeField`

            ``use_prefetch``
                optional -- tells the attribute field to use
                prefetch_related rather than a select_related.  Defaults to false.

                There are two reasons you might need to do this...

                - select_related will not work when the foreign key allows null.
                - select_related will not work when the foreign key is a GenericForeignKey.

                See https://docs.djangoproject.com/en/dev/ref/models/querysets/

                This parameter is meaningless for top-level attributes.
    """
    def __init__(self, *args, **kwargs):
        self._use_prefetch = kwargs.pop('use_prefetch', False)
        super(AttributeField, self).__init__(*args, **kwargs)

    def prepare(self, ctx, related):
        related_attr = '__'.join(self._attrs[:-1])
        if related_attr:
            if self._use_prefetch:
                related.prefetch(related_attr)
            else:
                related.select(related_attr)

    def handle_incoming(self, ctx, source_dict, target_obj):
        super(AttributeField, self).handle_incoming(ctx, source_dict, target_obj)

    def save(self, target_obj):
        # TODO: remove this save call and track all models to save in the ctx.
        # Also run a topo-sort in the ctx and save models in the order.  We can
        # then remove all of the save order logic from the fields.
        self._get_object(target_obj).save()

    def filter_by_item(self, ctx, filter_args, source_dict):
        from savory_pie.django.utils import getLogger
        getLogger().pprint((self, filter_args, source_dict))
        filter_args[self._full_attribute] = source_dict[self._compute_property(ctx)]

    def pre_save(self, model):
        return True


class AttributeFieldWithModel(AttributeField):
    """
    Django extension of the django AttributeField that adds support for setting up the multi-level expression
    with models, so it can be properly saved/added. This should only be used for multi-level expressioned attributes.

    Parameters:
            :class:`savory_pie.fields.AttributeField`

            ``model``
                A model class that is the model of the second last attribute, used to get at the object of this model

            ``extras``
                Extra values to be added to the filter call

    .. code-block:: python

        AttributeFieldWithModel('foo.property', type=int, model=ModelFoo, extras={'type': 'bar'})

    .. code-block:: javascript

        {'property': obj.foo}

    .. code-block:: python

        AttributeFieldWithModel('foo.bar.property', type=int, model=ModelBar)

    .. code-block:: javascript

        {'property': obj.foo.bar}

    """
    def __init__(self, *args, **kwargs):
        self._model = kwargs.pop('model', {})
        self._extras = kwargs.pop('extras', {})
        super(AttributeFieldWithModel, self).__init__(*args, **kwargs)

    def _get_object_with_model(self, root_obj, source_dict):
        obj = root_obj
        for i, attr in enumerate(self._attrs[:-1]):
            try:
                obj = getattr(obj, attr)
            except ObjectDoesNotExist:
                # only look for the model, if we are at the second last level,
                # i.e. if it's foo.bar.property, only do this when we are at 'bar'
                if i == len(self._attrs)-2:
                    filter_parms = self._extras.copy()
                    filter_parms[self._bare_attribute] = source_dict[self._bare_attribute]
                    new_obj = self._model.objects.get(**filter_parms)
                    setattr(obj, attr, new_obj)
                    obj = new_obj
                else:
                    raise SavoryPieError(u'Unable to save attribute field: {0}'.format(self._full_attribute))
        return obj

    def handle_incoming(self, ctx, source_dict, target_obj):
        obj = self._get_object_with_model(target_obj, source_dict)

        value = self.to_python_value(ctx, source_dict[self._compute_property(ctx)])
        setattr(obj, self._bare_attribute, value)

    def pre_save(self, model):
        return True


class URIResourceField(base_fields.URIResourceField, DjangoField):
    """
    Django extension of the basic URIResourceField that adds support for optimized
    select_related or prefetch_related calls.

    Parameters:
            :class:`savory_pie.fields.URIResourceField`

            ``use_prefetch``
                optional -- tells the attribute field to use
                prefetch_related rather than a select_related.  Defaults to false.

                There are two reasons you might need to do this...

                - select_related will not work when the foreign key allows null.
                - select_related will not work when the foreign key is a GenericForeignKey.

                See https://docs.djangoproject.com/en/dev/ref/models/querysets/

                This parameter is meaningless for top-level attributes.
    """
    def __init__(self, *args, **kwargs):
        self._use_prefetch = kwargs.pop('use_prefetch', False)
        super(URIResourceField, self).__init__(*args, **kwargs)

    def prepare(self, ctx, related):
        if self._use_prefetch:
            related.sub_prefetch(self._attribute)
        else:
            related.sub_select(self._attribute)

    def pre_save(self, model):
        return True


class URIListResourceField(base_fields.URIListResourceField, DjangoField):
    """
    Django extension of the basic URIListResourceField

        Parameters:
            :class:`savory_pie.fields.URIListResourceField`

            ``pre_save``
                optional -- tells the sub-model resource field whether to save
                before or after the related field.
    """
    def prepare(self, ctx, related):
        related.prefetch(self._attribute)

    def get_iterable(self, value):
        return value.all()

    def pre_save(self, model):
        return False


class SubModelResourceField(base_fields.SubObjectResourceField, DjangoField):
    """
    Django extension of the basic SubObjectResourceField that adds support for
    optimized select_related or prefetch_related calls.

        Parameters:
            :class:`savory_pie.fields.SubModelResourceField`

            ``use_prefetch``
                optional -- tells the sub-model resource field to use
                prefetch_related rather than a select_related.  Defaults to false.

                There are two reasons you might need to do this...

                - select_related will not work when the foreign key allows null.
                - select_related will not work when the foreign key is a GenericForeignKey.

                See https://docs.djangoproject.com/en/dev/ref/models/querysets/
    """
    def __init__(self, *args, **kwargs):
        self._use_prefetch = kwargs.pop('use_prefetch', False)
        self._skip_validation = kwargs.pop('skip_validation', False)
        super(SubModelResourceField, self).__init__(*args, **kwargs)

    def validate_resource(self, ctx, key, resource, source_dict):
        if self._skip_validation:
            return {}
        else:
            return super(SubModelResourceField, self).validate_resource(ctx, key, resource, source_dict)

    def prepare(self, ctx, related):
        if self._use_prefetch:
            related.prefetch(self._attribute)
            self._resource_class.prepare(ctx, related.sub_prefetch(self._attribute))
        else:
            related.select(self._attribute)
            self._resource_class.prepare(ctx, related.sub_select(self._attribute))

    def schema(self, ctx, **kwargs):
        kwargs = dict(kwargs.items() + {'schema': {'type': 'related', 'relatedType': 'to_one'}}.items())
        return super(SubModelResourceField, self).schema(ctx, **kwargs)

    def get_subresource(self, ctx, source_dict, target_obj):
        sub_source_dict = source_dict[self._compute_property(ctx)]
        try:
            # Look at non-null FK
            sub_resource = super(SubModelResourceField, self).get_subresource(
                ctx,
                source_dict,
                target_obj
            )
        except django.core.exceptions.ObjectDoesNotExist:
            # Search by the source dict
            if sub_source_dict:
                sub_resource = self._resource_class.get_by_source_dict(ctx, sub_source_dict)
            else:
                sub_resource = None

        # Make sure the new model is attached
        if hasattr(sub_resource, 'model'):
            setattr(target_obj, self._attribute, sub_resource.model)
        return sub_resource

    def get_submodel(self, ctx, source_object):
        try:
            # Look at non-null FK
            sub_model = super(SubModelResourceField, self).get_submodel(
                ctx,
                source_object
            )
        except django.core.exceptions.ObjectDoesNotExist:
            sub_model = None

        return sub_model

    def _get_field(self, model):
        field_name = (model._meta.pk.name if self.name == 'pk' else self.name)
        field = None
        try:
            field = model._meta.get_field(field_name)
        except:
            # probably only for m2m fields
            try:
                field = model._meta.get_field_by_name(field_name)[0].field
            except FieldDoesNotExist:
                field = None
        return field

    def pre_save(self, model):
        '''
        This is to figure if we need to pre_save the foreign key or not.
        If Model A has foreign key to Model B, do everything normal
        If Model B has foreign key to Model A, you need to save Model A first before setting value on Model B
        @return: a Boolean variable used in ModelResources' put
        '''

        field = self._get_field(model)
        if field:
            attribute_name = field.related.field.name
            try:
                attribute = getattr(self._resource_class.model_class, attribute_name)
            except AttributeError:
                logger.debug('Setting pre_save to True with attribute %s', self._attribute)
                return True
            else:
                if isinstance(attribute, django.db.models.fields.related.ReverseSingleRelatedObjectDescriptor):
                    logger.debug('Setting pre_save to False with attribute %s and attribute_name %s',
                                 self._attribute, attribute_name)
                    return False

        return True


class OneToOneField(SubModelResourceField):
    """
    Django extension of the basic SubModelResourceField that is specifically for
    OneToOneField.

    When the resource can't be found, instead of looking it up with the source dictionary,
    it'll create a new instance for this resource since there is a 1-to-1 constraint.

    """

    def get_subresource(self, ctx, source_dict, target_obj):
        try:
            # Look at non-null FK
            sub_resource = super(SubModelResourceField, self).get_subresource(
                ctx,
                source_dict,
                target_obj
            )
        except django.core.exceptions.ObjectDoesNotExist:
            # create a new resource, since this is a one to one field
            sub_resource = self._resource_class.create_resource()

        # Make sure the new model is attached
        if hasattr(sub_resource, 'model'):
            setattr(target_obj, self._attribute, sub_resource.model)
        return sub_resource


class RelatedManagerField(base_fields.IterableField, DjangoField):
    """
    Django extension of the basic IterableField that adds support for
    optimized select_related or prefetch_related calls.

        Parameters:
            :class:`savory_pie.fields.IterableField`
    """
    def __init__(self, *args, **kwargs):
        super(RelatedManagerField, self).__init__(*args, **kwargs)

    def get_iterable(self, value):
        return value.all()

    def prepare(self, ctx, related):
        attrs = self._attribute.replace('.', '__')
        related.prefetch(attrs)
        self._resource_class.prepare(ctx, related.sub_prefetch(attrs))

    def schema(self, ctx, **kwargs):
        dct = {'type': 'related', 'relatedType': 'to_many', 'fields': {}}
        if self._resource_class:
            for f in self._resource_class.fields:
                subkwargs = kwargs.copy()
                subkwargs['model'] = self._resource_class.model_class
                try:
                    dct['fields'][f._compute_property(ctx)] = f.schema(ctx, **subkwargs)
                except Exception, e:
                    logger.exception(e)    # field name is probably broken
        kwargs['schema'] = dct
        return super(RelatedManagerField, self).schema(ctx, **kwargs)

    def pre_save(self, model):
        '''
        This is to figure out if we need to pre_save the many to many field or not.
        In this case, we always want the related model to save first, before we save ourselves.
        @return: a Boolean variable used in ModelResources' put
        '''
        return False


class ReverseField(object):
    """
    Django field to handle the creation of new resources that require a foreign
    key to the parent in the API object graph.

    This field only runs on incoming requests on objects which have not been
    saved yet.

    Parameters:
        ``attribute_name``
            the name of the backref on the model.
    """
    __metaclass__ = base_fields.ResourceClassUser

    def __init__(self, attribute_name, resource_class=None):
        self.attribute_name = attribute_name
        self.init_resource_class(resource_class)

    @property
    def name(self):
        return self.attribute_name

    def handle_incoming(self, ctx, source_dict, target_obj):
        if target_obj.pk is not None:
            return
        container = ctx.peek()
        if container is not target_obj:
            setattr(target_obj, self.attribute_name, container)
        else:
            published_property = ctx.formatter.convert_to_public_property(self.attribute_name)
            if published_property in source_dict:
                sub_dict = source_dict.get(published_property)
                if self._resource_class and isinstance(sub_dict, dict) and 'pk' in sub_dict:
                    pk = sub_dict.get('pk')
                    qs = self._resource_class.model_class.objects.filter(pk=pk)
                    if qs.count() == 1:
                        setattr(target_obj, self.attribute_name, qs[0])
                    else:
                        raise ValidationError('cannot find target {0}'.format(self._resource_class))

    def handle_outgoing(self, ctx, source_obj, target_dict):
        pass


class ReverseRelatedManagerField(object):
    """
    Where ReverseField works with one-to-one relationships, this works with
    many-to-one relationships where multiple A models all point to the same B.
    The PUT operation on AResource includes an embedded JSON chunk for a
    BResource, and when the PUT is executed, the BResource and its underlying
    B model are created. In this case, BResource.afield.handle_incoming needs
    to peek up the stack to get the A model, and set the B attribute on that
    A model to this B model.
    """
    from savory_pie.fields import ResourceClassUser
    __metaclass__ = ResourceClassUser

    def __init__(self, attribute_name, resource_class):
        self.attribute_name = attribute_name
        self.init_resource_class(resource_class)

    @property
    def name(self):
        return self.attribute_name

    def handle_outgoing(self, ctx, source_obj, target_dict):
        pass

    def pre_save(self, model):
        return True

    def handle_incoming(self, ctx, source_dict, target_obj):
        if target_obj.pk is not None:
            target = ctx.peek()
            a_model_type = self._resource_class.model_class
            assert type(target) == a_model_type
            setattr(target, self.attribute_name, target_obj)


class RelatedCountField(object):
    """
    Django field to handle counting the number of related objects. This uses
    something like annotate(Count()) under the hood.

    Parameters:
        ''attribute''
            doted name of the field to count

        ``published_property``
            optional -- name exposed in the API
    """
    def __init__(self, attribute, published_property=None):
        self._attribute = attribute
        self._published_property = published_property
        self._orm_attribute = self._attribute.replace('.', '__')

    def _compute_property(self, ctx):
        if self._published_property is not None:
            return ctx.formatter.convert_to_public_property(self._published_property)
        else:
            return ctx.formatter.convert_to_public_property(self._attribute)

    def _get(self, source_obj):
        try:
            return getattr(source_obj, self._orm_attribute + '__count')
        except AttributeError:
            return source_obj.__class__.objects.filter(pk=source_obj.id).values(self._orm_attribute).count()

    def prepare(self, ctx, related):
        # Due to how annotate works with the django ORM, RelatedCountField can
        # only be used on a top level resource. We peek in to the stack to see
        # how deep we are and fail if it is too deep.
        try:
            ctx.peek(2)
        except IndexError:
            pass
        else:
            raise SavoryPieError('RelatedCountField can only be used on a '
                                 'top level ModelResource')

        related.annotate(
            django.db.models.Count,
            self._orm_attribute,
            distinct=True,
        )

    def handle_incoming(self, ctx, source_dict, target_obj):
        pass

    def handle_outgoing(self, ctx, source_obj, target_dict):
        target_dict[self._compute_property(ctx)] = ctx.formatter.to_api_value(
            int,
            self._get(source_obj)
        )
