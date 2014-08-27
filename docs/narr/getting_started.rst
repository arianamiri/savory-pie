.. index::
   single: Getting Started

.. _narr_getting_started:

Creating your first API with Savory Pie and Django
=======================================

This is going to be a set of steps on how to add Savory Pie to your Django application.
You are not required to use Django with Savory Pie, but for this example we are going to
go through a steps of how to setup.

For this example we are going to assume that your Django application has a set of Models: Car and Driver.

**Example Resources**:

.. code-block:: python

    from django.db import models

    class Driver(django.db.models.Model):
        name = models.CharField(max_length=128, help_text=_('name'))
        models.ForeignKey(Car, help_text=_('car'), related_name='driver')

    class Car(django.db.models.Model):
        type = models.CharField(max_length=128, help_text=_('type'))
        open_seats =  models.PositiveIntegerField(help_text=_('type'), default=3)


When you want to add a Savory Pie resource to your application, it is as simple as adding the api
endpoint to your `urls.py` file.

Create a root resource for your new api endpoint. This endpoint should be versioned.

Creating simple ModelResources
===============

The fields of the Django models are represented by Savory Pie fields, which can present the
field information in various formats. The simplest is the `AttributeField`, which can represent
ints, floats, booleans, or strings.

.. code-block:: python

    from savory_pie.django import fields

    class CarResource(resources.ModelResource):
        parent_resource_path = 'group'
        model_class = Group

        fields = [
            fields.AttributeField('type', type=str),
            fields.AttributeField('open_seats', type=int),
        ]

    class DriverResource(resources.ModelResource):
        parent_resource_path = 'person'
        model_class = Person

        fields = [
            fields.AttributeField('name', type=str),
        ]

When we GET these resources, we receive simple JSON representations for these objects. The
actual values you would see would depend upon the contents of your database.

.. code-block:: javascript

    // GET /api/driver/1
    {
        name: 'Batman'
    }

    // GET /api/car/3
    {
        type: 'Batmobile',
        openSeats: 1
    }

Creating a SubModelResource
===============

Each driver drives one car, but a car may have many drivers. The `ForeignKey` from the
`Driver` model to the `Car` model enforces this one-to-many relationship.

.. code-block:: python

    from savory_pie.django import fields

    class CarResource(resources.ModelResource):
        parent_resource_path = 'group'
        model_class = Group

        fields = [
            fields.AttributeField('type', type=str),
            fields.AttributeField('open_seats', type=int),
            fields.URIListResourceField('drivers', DriverResource),
        ]

    class DriverResource(resources.ModelResource):
        parent_resource_path = 'person'
        model_class = Person

        fields = [
            fields.AttributeField('name', type=str),
            fields.SubModelResourceField('car', CarResource),
        ]

The use of `SubModelResourceField` means that the JSON for the `Group` will appear embedded in the
JSON for the `Person`. Because the members of the group are represented as a `URIListResourceField`,
we see the resource URI for each person in the `members` list of the group.

.. code-block:: javascript

    // GET /api/driver/1
    {
        name: 'Batman',
        car: {
            type: 'Batmobile',
            open_seats: 1,
            drivers: [
                '/api/driver/1',
                '/api/driver/2'
            ]
        }
    }

If the drivers of the car were instead represented as a `RelatedManagerField`, then the
`drivers` list of the cart would contain the full JSON representation of each `Driver`, which
would of course include the JSON for the `Car`, leading to an **infinite JSON regress**. This
situation obviously must be avoided.

The other good option would be to use `URIResourceField` to represent the `Car` within the JSON
for a `Driver`, while using a `RelatedManagerField` to represent the drivers of a car.

.. code-block:: javascript

    // GET /api/car/3
    {
        type: 'Batmobile',
        drivers: [
            {
                name: 'Batman',
                car: '/api/car/3'
            },
            {
                name: 'Robin',
                car: '/api/car/3'
            }
        ]
    }


Creating a QuerySetResource for your Resource
===============
...

Creating a unified Endpoint for your Module
===============
...

Adding your api endpoint to your application
===============
To add this new CarApi endpoint all you would need to do is register this api endpoint to a root url resource and then add
it to your url patterns.

**Example Adding Your Endpoint To Your Application**:

.. code-block:: python

    from django.conf.urls import patterns, url
    from savory_pie.django.views import api_view
    import car_api

    root_resource = APIResource()
    root_resource.register(car_api)

    urlpatterns = patterns(
        ...
        url(r'^api/v2/(.*)$', api_view(root_resource))
        ...
    )

Adding Authorization
===============
See :ref: _narr_authorization

GET, PUT, POST, DELETE
===============
...

PUT and POST retry
===============
...
