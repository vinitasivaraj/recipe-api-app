"""tests for models"""
from unittest.mock import patch
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from core import models


def create_user(email='user@example.com',password='testpass123'):
    return get_user_model().objects.create_user(email,password)


class ModelTests(TestCase):

    def test_create_user_with_email_successful(self):
        email = 'test@exmaple.com'
        password = 'test123'
        user=get_user_model().objects.create_user(
            email=email,
            password=password,
        )
        self.assertEqual(user.email,email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalized(self):
        sample_emails=[
            ['test1@EXAMPLE.com', 'test1@example.com'],
            ['Test2@Example.com','Test2@example.com'],
            ['TEST3@EXAMPLE.COM','TEST3@example.com'],
            ['test4@example.COM','test4@example.com'],

        ]

        for email,expected in sample_emails:
            user=get_user_model().objects.create_user(email,'sample123')
            self.assertEqual(user.email, expected)


    def test_new_user_without_email_raise_error(self):
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user("","test123")


    def test_create_superuser(self):
        user= get_user_model().objects.create_superuser(
            'test@email.com',
            'test123'

        )
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_recipe(self):
        user=get_user_model().objects.create_user(
            'test@example.com',
            'testpass123',
        )
        recipe=models.Recipe.objects.create(
            user=user,
            title='Sample recipe name',
            time_minutes=5,
            price=Decimal('5.50'),
            description='Sampe recipe description,',

        )
        self.assertEqual(str(recipe),recipe.title)

    def test_create_tag(self):
        user=create_user()
        tag=models.Tag.objects.create(user=user,name='Tag1')

        self.assertEqual(str(tag),tag.name)

 
    # @patch('core.models.uuid.uuid4')
    # def test_recipe_file_name_uuid(self, mock_uuid):
    #     uuid = 'test-uuid'
    #     mock_uuid.return_value = uuid  # Configure mock
    #     print(f"Mocked uuid4: {mock_uuid.return_value}")  # Debug line

    #     file_path = models.recipe_image_file_path(None, 'example.jpg')
    #     print(f"Generated file path: {file_path}")  # Debug line

    #     self.assertEqual(file_path, f'uploads/recipe/{uuid}.jpg')
    @patch('core.models.uuid.uuid4')
    def test_recipe_file_name_uuid(self, mock_uuid):
        """Test generating image path."""
        uuid = 'test-uuid'
        mock_uuid.return_value = uuid
        file_path = models.recipe_image_file_path(None, 'example.jpg')

        self.assertEqual(file_path, f'uploads/recipe/{uuid}.jpg')
