.. _index:

Welcome to Savory Pie's documentation!
======================================

Savory Pie is an API building library, we give you the pieces to build the API
you need. Currently Django is the main target, but the only dependencies on
Django are a single view and Resources and Fields that understand Django's ORM.

A Basic API might look something like this:

**Example Resources**:

.. code-block:: python

   class UserResource(savory_pie.django.resources.ModelResource):
       parent_resource_path = 'users'
       model_class = User

        fields = [
            fields.AttributeField('name', type=str),
            fields.AttributeField('age', type=int),
        ]


    class UserQuerySetResource(savory_pie.django.resources.QuerySetResource):
        resource_class = UserResource

**URL configuration**:

.. code-block:: python

    api_resource = resources.APIResource()
    api_resource.register_class(UserQuerySetResource)

    url(r'^api/v1/(.*)$', savory_pie.django.views.api_view(api_resource))


**Request**::

    GET /api/v1/users/1/ HTTP/1.1
    Host: example.com
    Accept: application/json

**Response**::

    HTTP/1.1 200 OK
    Vary: Accept
    Content-Type: application/json

    {
        'resourceUri': 'http://localhost/api/v1/users/1/',
        'name': 'Bob',
        'age': 45
    }

Narrative documentation
=======================
.. toctree::
   :maxdepth: 2

   narr/getting_started
   narr/running_tests
   narr/resources
   narr/fields
   narr/filters
   narr/validation
   narr/extending
   narr/django
   narr/authorization

API Documentation
=================

Documentation for all of Savory Pie API.

.. toctree::
   :maxdepth: 2

   api

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

