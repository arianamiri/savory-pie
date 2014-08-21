import unittest
from mock import Mock
from savory_pie.fields import URIResourceField, URIListResourceField
from savory_pie.django.auth import DjangoUserPermissionValidator, uri_auth_adapter
from savory_pie.django.fields import RelatedManagerField


class URIAuthorizationAdapterTestCase(unittest.TestCase):

    def _passthrough_method(self, val):
        return val

    def test_uri_auth_adapter_with_related_manager_field(self):
        field = Mock(spec=RelatedManagerField, name='field')
        field.name = 'fieldName'
        field._resource_class.side_effect = self._passthrough_method
        field._compute_property.return_value = 'source_name'

        ctx = Mock(spec=['build_resource_uri'])
        ctx.build_resource_uri.side_effect = self._passthrough_method

        target_obj = Mock(spec=['fieldName'])
        target_obj.fieldName = Mock(spec=['all'])
        target_obj.fieldName.all.return_value = ['uri1', 'uri3', 'uri2']

        source_dict = {'source_name': [{'resourceUri': 'uri2'}, {'resourceUri': 'uri1'}]}

        name, source, target = uri_auth_adapter(field, ctx, source_dict, target_obj)
        self.assertEqual(name, 'source_name')
        self.assertEqual(source, ['uri1', 'uri2'])
        self.assertEqual(target, ['uri1', 'uri2', 'uri3'])

    def test_uri_auth_adapter_with_uri_resource_field(self):
        field = Mock(spec=URIResourceField)
        field.name = 'fieldName'
        field._resource_class.side_effect = self._passthrough_method
        field._compute_property.return_value = 'source_name'

        ctx = Mock(spec=['build_resource_uri'])
        ctx.build_resource_uri.side_effect = self._passthrough_method

        target_obj = Mock(spec=['fieldName'])
        target_obj.fieldName = 'uri2'

        source_dict = {'source_name': 'uri1'}

        name, source, target = uri_auth_adapter(field, ctx, source_dict, target_obj)
        self.assertEqual(name, 'source_name')
        self.assertEqual(source, 'uri1')
        self.assertEqual(target, 'uri2')

    def test_uri_auth_adapter_with_uri_list_resource_field(self):
        field = Mock(spec=URIListResourceField)
        field.name = 'fieldName'
        field._resource_class.side_effect = self._passthrough_method
        field._compute_property.return_value = 'source_name'

        ctx = Mock(spec=['build_resource_uri'])
        ctx.build_resource_uri.side_effect = self._passthrough_method

        target_obj = Mock(spec=['fieldName'])
        target_obj.fieldName = Mock(spec=['all'])
        target_obj.fieldName.all.return_value = ['uri3', 'uri1', 'uri2']

        source_dict = {'source_name': ['uri2', 'uri1']}

        name, source, target = uri_auth_adapter(field, ctx, source_dict, target_obj)
        self.assertEqual(name, 'source_name')
        self.assertEqual(source, ['uri1', 'uri2'])
        self.assertEqual(target, ['uri1', 'uri2', 'uri3'])


class DjangoUserPermissionValidatorTestCase(unittest.TestCase):

    def test_target_source_changed(self):
        validator = DjangoUserPermissionValidator('value')
        ctx = Mock(spec=['user'])
        ctx.request = Mock()
        ctx.request.user.has_perm.return_value = False
        self.assertFalse(validator.is_write_authorized(ctx, None, 'a', 'b'))
        ctx.request.user.has_perm.assert_called_with('value')

    def test_target_source_not_changed(self):
        validator = DjangoUserPermissionValidator('value')
        ctx = Mock(spec=['user'])
        ctx.request = Mock()
        # Should not call has_perm
        ctx.request.user.has_perm.side_effect = Exception
        self.assertTrue(validator.is_write_authorized(ctx, None, 'a', 'a'))
