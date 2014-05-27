# -*- coding: utf-8 -*-
from __future__ import unicode_literals
# from django.conf import settings
import django
from django.utils import encoding, translation, unittest
from django.test import TestCase
from django.contrib import auth
from django.core.urlresolvers import reverse
from .models import Article, Category


class ArticleTestCase(TestCase):

    credentials = {
        'username': 'admin',
        'password': 'password'
    }

    @classmethod
    def setUpClass(cls):
        auth.models.User.objects.create_superuser(email='', **cls.credentials)

    def assertInContent(self, member, resp, msg=None):
        return super(ArticleTestCase, self).assertIn(member, encoding.smart_text(resp.content), msg)

    def assertNotInContent(self, member, resp, msg=None):
        return super(ArticleTestCase, self).assertNotIn(member, encoding.smart_text(resp.content), msg)

    def setUp(self):
        cat = Category()
        cat.name = "Cheese"
        cat.save()
        self.cat_id = cat.id

        art = Article()
        art.set_current_language('en')
        art.title = "Cheese omelet"
        art.slug = "cheese-omelet"
        art.content = "This is the wonderful recipe of a cheese omelet."
        art.set_current_language('fr')
        art.title = "Omelette du fromage"
        art.slug = "omelette-du-fromage"
        art.content = "Voilà la recette de l'omelette au fromage"
        art.category = cat

        art.save()

        self.art_id = art.id

    def test_home(self):
        resp = self.client.get('/', follow=True)
        self.assertRedirects(resp, '/en/')
        self.assertTemplateUsed(resp, 'article/list.html')
        self.assertNotInContent("/en/cheese-omelet", resp)

        # now published
        Article.objects.filter(id=self.art_id).update(published=True)

        resp = self.client.get(reverse('article-list'))  # == /en/
        self.assertInContent("/en/cheese-omelet", resp)

    def test_view_article(self):
        resp = self.client.get(reverse('article-details', kwargs={'slug': 'cheese-omelet'}))
        self.assertEqual(404, resp.status_code)

        # now published
        Article.objects.filter(id=self.art_id).update(published=True)

        resp = self.client.get(reverse('article-details', kwargs={'slug': 'cheese-omelet'}))
        self.assertTemplateUsed(resp, 'article/details.html')
        self.assertInContent("This is the wonderful recipe of a cheese omelet.", resp)

    def test_admin_list(self):
        self.client.login(**self.credentials)
        resp = self.client.get(reverse('admin:article_article_changelist'))
        self.assertEqual(200, resp.status_code)
        self.assertTemplateUsed(resp, 'admin/change_list.html')

    @unittest.skipIf(django.VERSION < (1, 5), "bug with declared_fieldsets in ArticleAdmin")
    def test_admin_add(self):
        self.client.login(**self.credentials)
        resp = self.client.get(reverse('admin:article_article_add'))
        self.assertEqual(200, resp.status_code)
        self.assertIn('<h1>Add Article (English)</h1>', encoding.smart_text(resp.content))

        translation.activate('fr')
        resp = self.client.get(reverse('admin:article_article_add'))
        self.assertEqual(200, resp.status_code)
        self.assertInContent('<h1>Ajout Article (Anglais)</h1>', resp)

        translation.activate('en')

        resp = self.client.get(reverse('admin:article_article_add'), {"language": "nl"})
        self.assertEqual(200, resp.status_code)
        self.assertInContent('<h1>Add Article (Dutch)</h1>', resp)

    @unittest.skipIf(django.VERSION < (1, 5), "bug with declared_fieldsets in ArticleAdmin")
    def test_admin_add_post(self):
        self.client.login(**self.credentials)
        resp = self.client.post(
            reverse('admin:article_article_add'),
            {
                'title': "my article",
                'slug': "my-article",
                'content': "my super content",
            },
            follow=True
        )

        self.assertRedirects(resp, reverse('admin:article_article_changelist'))
        self.assertEqual(1, Article.objects.filter(translations__slug='my-article').count())

    @unittest.skipIf(django.VERSION < (1, 5), "bug with declared_fieldsets in ArticleAdmin")
    def test_admin_change(self):
        self.client.login(**self.credentials)
        resp = self.client.get(reverse('admin:article_article_change', args=[self.art_id]))
        self.assertEqual(200, resp.status_code)
        self.assertInContent('<h1>Change Article (English)</h1>', resp)
        self.assertInContent('name="title" type="text" value="Cheese omelet"', resp)

        translation.activate('fr')
        resp = self.client.get(reverse('admin:article_article_change', args=[self.art_id]))
        self.assertEqual(200, resp.status_code)
        self.assertInContent('<h1>Modification de Article (Anglais)</h1>', resp)
        self.assertInContent('name="title" type="text" value="Cheese omelet"', resp)

        translation.activate('en')

        resp = self.client.get(reverse('admin:article_article_change', args=[self.art_id]), {"language": "nl"})
        self.assertEqual(200, resp.status_code)
        self.assertInContent('<h1>Change Article (Dutch)</h1>', resp)
        self.assertInContent('name="title" type="text" />', resp)

    def test_admin_change_category(self):
        self.client.login(**self.credentials)
        resp = self.client.get(reverse('admin:article_category_change', args=[self.cat_id]))
        self.assertEqual(200, resp.status_code)

        self.client.login(**self.credentials)
        resp = self.client.get(reverse('admin:article_stackedcategory_change', args=[self.cat_id]))
        self.assertEqual(200, resp.status_code)

        self.client.login(**self.credentials)
        resp = self.client.get(reverse('admin:article_tabularcategory_change', args=[self.cat_id]))
        self.assertEqual(200, resp.status_code)

    def test_admin_delete_translation(self):
        self.client.login(**self.credentials)
        # delete confirmation
        resp = self.client.get(
            reverse('admin:article_article_delete_translation', args=[self.art_id, 'en']),
        )
        self.assertTemplateUsed(resp, 'admin/delete_confirmation.html')

        # we can go to the pagein nl even if there is no translation in that language
        translation.activate('nl')
        resp = self.client.get(
            reverse('admin:article_article_delete_translation', args=[self.art_id, 'en']),
        )
        self.assertTemplateUsed(resp, 'admin/delete_confirmation.html')
        translation.activate('en')

        # delete confirmed
        resp = self.client.post(
            reverse('admin:article_article_delete_translation', args=[self.art_id, 'en']),
            {"post": "yes"}
        )
        self.assertRedirects(resp, reverse('admin:article_article_changelist'))
        self.assertEqual(0, Article.objects.filter(translations__slug='cheese-omelet').count())

        # try to delete something that is not there
        resp = self.client.post(
            reverse('admin:article_article_delete_translation', args=[self.art_id, 'en']),
            {"post": "yes"}
        )
        self.assertEqual(404, resp.status_code)

        # try to delete the only remaining translation
        translation.activate('fr')
        resp = self.client.post(
            reverse('admin:article_article_delete_translation', args=[self.art_id, 'fr']),
            {"post": "yes"}
        )
        self.assertEqual(200, resp.status_code)
        self.assertTemplateUsed(resp, 'admin/parler/deletion_not_allowed.html')

    @unittest.expectedFailure
    def test_admin_delete_translation_unavailable(self):
        """
        To be fixed : when trying to delete the last language when a translation
        in the current language does not exist, parler fails with exception:
            Article does not have a translation for the current language!
        """
        self.client.login(**self.credentials)
        # delete confirmed
        resp = self.client.post(
            reverse('admin:article_article_delete_translation', args=[self.art_id, 'en']),
            {"post": "yes"}
        )

        # now try to delete the last translation, but the active language is english, and there is no translation in this language
        resp = self.client.post(
            reverse('admin:article_article_delete_translation', args=[self.art_id, 'fr']),
            {"post": "yes"}
        )
        self.assertEqual(200, resp.status_code)
        self.assertTemplateUsed(resp, 'admin/parler/deletion_not_allowed.html')

    def test_admin_delete(self):

        self.client.login(**self.credentials)
        resp = self.client.post(
            reverse('admin:article_article_changelist'),
            {
                'action': 'delete_selected',
                'select_across': 0,
                'index': 0,
                '_selected_action': self.art_id,
            }
        )
        self.assertEqual(200, resp.status_code)
        self.assertTemplateUsed(resp, 'admin/delete_selected_confirmation.html')

        # confirmed deleteion
        resp = self.client.post(
            reverse('admin:article_article_changelist'),
            {
                'action': 'delete_selected',
                'post': 'yes',
                '_selected_action': self.art_id,
            },
            follow=True
        )
        self.assertRedirects(resp, reverse('admin:article_article_changelist'))
        self.assertEqual(0, Article.objects.count())
