.. index::
   single: Authorization

.. _narr_authorization:

Implementing Authorization
=================================
This document outlines how to implement write-authorization on Savory Pie resources.


**Protecting a field**

Implementing authorization rules on a Savory Pie resource prevents clients from writing to a resource's fields (via PUT or POST), if they are not authorized to do so.  For example let's start with the following ModelResource:

.. code-block:: python

    from savory_pie.django import fields

    class CarResource(resource.ModelResource):
      parent_resource_path = 'group'
      model_class = Group

      fields = [
        fields.AttributeField('type', type=str),
        fields.AttributeField('open_seats', type=int)
        fields.SubModelResourceField('driver', DriverResource)
      ]


For this first example we will apply an authorization rule that prevents unauthorized users from changing the "type" ``AttributeField``:

.. code-block:: python

    from savory_pie.django import fields
    from savory_pie.django.auth import DjangoUserPermissionValidator

    class CarResource(resource.ModelResource):
      parent_resource_path = 'group'
      model_class = Group

      fields = [
        fields.AttributeField('type', type=str, permission=DjangoUserPermissionValidator('change_type')),
        fields.AttributeField('open_seats', type=int)
        fields.SubModelResourceField('driver', DriverResource)
      ]

Notice that we have added a keyword argument ``permission`` to the first ``AttributeField``.  The ``permission`` argument takes an AuthorizationValidator object as it's argument.  We will go into more detail about these classes below.
With this extra kwarg, we prevent users that don't have the 'change_type' permission from editing that field.  If a user without said permission attempts to edit that field, Savory Pie will return a 403 response to the client.  The same user can edit the other fields of this resource successfully, because they don't have any permissions associated with them.  If the same user attempts edit "type" field, as well as the other fields, none of their changes will be persisted.
The ``permission`` argument can be specified on ``AttributeField``, ``URIResourceField``, ``CompleteURIResourceField``, ``URIListResourceField``, ``SubObjectResourceField``, ``IterableField`` fields and any subclass fields derived from them.

==============
Authorization Validators
==============

The ``permission`` kwarg passed to a field takes an AuthorizationValidator object.  An AuthorizationValidator class is any class that specifies an ``is_write_authorized`` method.  Let's take a look at the the source for the ``DjangoUserPermissionValidator`` class we used above:

.. code-block:: python

  class DjangoUserPermissionValidator(object):
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

The constructor of this AuthorizationValidator takes a ``permission_name`` argument and an ``auth_adapter`` argument.  The ``permission_name`` argument is specific to the the implementation of this AuthorizationValidator, but it is not required that all AuthorizationValidator take a ``permission_name`` argument.  It is recommended that all  AuthorizationValidators take an  ``auth_adapter`` argument (\ *more on that later*\ ).
All AuthorizationValidators must implement the ``is_write_authorized`` method.  As its name implies, this method will determine if the client is authorized to PUT of POST to the specified field.  It takes the following arguments:

ctx
  ``APIContext`` object.
target_obj
  The underlying ORM's representation of the Resource being written to.
source
  The value of the field as sent from the client.
target
  The value of the field as it currently exists on the server.

It is important to note that when a field has a permission applied to it, ``is_write_authorized`` will be invoked, regardless of whether or not the field has been altered.  That is why in the ``DjangoUserPermissionValidator`` compares ``source`` to ``target`` before evaluating the permission.


===================
Authorization Adapters
===================

We mentioned above that Authorization Validators should accept an ``auth_adapter`` keyword argument.  An auth_adpater is a function that retrieves the values that will be passed to an AuthorizationValidator's ``is_write_authorized`` method.

An authorization adapter will be provided the following arguments:

field
  Savory Pie ``Field`` that is being evaluated.
ctx
  ``APIContext`` object.
source_dict
  A dictionary representation of the resource sent from the client.
target_object
  The underlying ORM's representation of the Resource being written to.


Authorization adapters should return the following params:

name
  The name of the ``Field`` that was passed into the Authorization Adapter.
  (This is used to provide messaging back to client).
source
  The value of the field sent from the client.
target
  The current value of the field on the server.

The purpose of having an adapter like this is so that values can be extracted from the `source_dict` and `target_obj` so they can be dirty checked in `is_write_authorized`.  It's job is to get the current value of the field and the intended value of the field into a comparable state.  As such certain adapters only work for certain types of fields.


======
Built In Auth Adapters
======

authorization_adapter
  Used with fields describing simple data, (str, int, etc).  This authorization adapter is used by default when one is not assigned to the AuthorizationValidator

datetime_auth_adapter
  Used with fields that describe dates.

subobject_auth_adapter
  Used primarily with ``SubObjectResourceField`` fields and any subclasses derived from ``SubObjectResourceField``.  This authorization adapter will prevent a user from changing foreign key relationships, but will not gaurd against changes to fields in the object pointed to by the foreign key relationship.  To prevent a user from changing fields in the related object, permissions should be applied to the fields of the related object.

uri_auth_adapter
  Like the subobject_auth_adapter, but supports ``UriResourceField``, ``UriListResourceField``, ``IterableField`` and any of their subclasses.  This authorization adapter will prevent a user from changing foreign key relationships, but will not gaurd against changes to fields in the object pointed to by the foreign key relationship.