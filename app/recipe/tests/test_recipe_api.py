#Test for recipe api's


from decimal import Decimal
import tempfile
import os
from PIL import Image
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe,Tag
from recipe.serializers import RecipeSerializer,RecipeDetailSerializer


RECIPES_URL=reverse('recipe:recipe-list')

def detail_url(recipe_id):
    return reverse('recipe:recipe-detail',args=[recipe_id])

def image_upload_url(recipe_id):
    return reverse('recipe:recipe-upload-image', args=[recipe_id])

def create_user(**params):
    return get_user_model().objects.create_user(**params)

def create_recipe(user,**params):
    defaults={
        'title':'Sample recipe',
        'time_minutes':22,
        'price':Decimal('5.25'),
        'description': 'Sample description',
        'link' : 'http://example.com/recipe.pdf'
    }
    defaults.update(params)
    recipe=Recipe.objects.create(user=user, **defaults)
    return recipe


class PublicRecipeAPITests(TestCase):

    def setUp(self):
        self.client=APIClient()

    def test_auth_required(self):
        res=self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):

    def setUp(self):
        self.client=APIClient()
        self.user = create_user(email='newuser@example.com', password='test123')
        self.user=get_user_model().objects.create_user(
            'user@example.com',
            'testpass123'
        )
        self.client.force_authenticate(self.user)

    def test_retrive_recipe(self):
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res=self.client.get(RECIPES_URL)

        recipes=Recipe.objects.all().order_by('-id')
        serializer=RecipeSerializer(recipes,many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        # other_user=get_user_model().objects.create_user(
        #     'other@example.com',
        #     'otherpass123'
        # )
        other_user= create_user(email='other@example.com', password='other123')
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res=self.client.get(RECIPES_URL)
        recipes=Recipe.objects.filter(user=self.user)
        serializer=RecipeSerializer(recipes,many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        recipe=create_recipe(user=self.user)
        url=detail_url(recipe.id)
        res=self.client.get(url)
        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data,serializer.data)

    def test_create_recipe(self):
        payload={
            'title':'Sample create',
             'time_minutes':30,
             'price':Decimal('5.34')
        }
        res=self.client.post(RECIPES_URL,payload)
        self.assertEqual(res.status_code,status.HTTP_201_CREATED)
        recipe=Recipe.objects.get(id=res.data['id'])
        for k,v in payload.items():
            self.assertEqual(getattr(recipe,k),v)
        self.assertEqual(recipe.user,self.user)

    def partial_update(self):
        original_link='http://example.com/recipe.pdf'
        recipe=create_recipe(
            user=self.user,
            title='Sample recipe title',
            link=original_link
        )

        payload={'title':'new recipe updated'}
        url = detail_url(recipe.id)
        res=self.client.patch(url,payload)
        self.assertEqual(res.status_code,status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assetEqual(recipe.title,payload['title'])
        self.asserEqual(recipe.user,self.user)

    def test_full_update(self):
        """Test full update of recipe."""
        recipe = create_recipe(
            user=self.user,
            title='Sample recipe title',
            link='https://exmaple.com/recipe.pdf',
            description='Sample recipe description.',
        )

        payload = {
            'title': 'New recipe title',
            'link': 'https://example.com/new-recipe.pdf',
            'description': 'New recipe description',
            'time_minutes': 10,
            'price': Decimal('2.50'),
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """Test changing the recipe user results in an error."""
        new_user = create_user(email='user2@example.com', password='test123')
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe successful."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_recipe_other_users_recipe_error(self):
        """Test trying to delete another users recipe gives error."""
        new_user = create_user(email='user2@example.com', password='test123')
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        payload={
            'title': ' thai prawn',
            'time_minutes': 30,
            'price':Decimal('5.35'),
            'tags':[{'name':'Thai'},{'name':'Dinner'}]
        }
        res= self.client.post(RECIPES_URL,payload,format='json')
        self.assertEqual(res.status_code,status.HTTP_201_CREATED)
        recipes=Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(),1)
        recipe=recipes[0]
        self.assertEqual(recipe.tags.count(),2)
        for tag in payload['tags']:
            exists=recipe.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        """Test creating a recipe with existing tag."""
        tag_indian = Tag.objects.create(user=self.user, name='Indian')
        payload = {
            'title': 'Pongal',
            'time_minutes': 60,
            'price': Decimal('4.50'),
            'tags': [{'name': 'Indian'}, {'name': 'Breakfast'}],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

class ImageUploadTests(TestCase):

    def setUp(self):
        self.client=APIClient()
        self.user=get_user_model().objects.create_user(
            'user@example.com',
            'password123'
        )
        self.client.force_authenticate(self.user)
        self.recipe=create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        url=image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img=Image.new('RGB',(10,10))
            img.save(image_file,format='JPEG')
            image_file.seek(0)
            payload={'image':image_file}
            res=self.client.post(url,payload,format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code,status.HTTP_200_OK)
        self.assertIn('image',res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image."""
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'notanimage'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    






    


