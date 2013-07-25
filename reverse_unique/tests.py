import datetime

from django.test import TestCase
from django.utils.translation import activate
from django import forms

from .test_models import (
    Article, ArticleTranslation, Lang, DefaultTranslationArticle,
    DefaultTranslationArticleTranslation, Guest, Room, Reservation,
    Child, Rel1, Rel2)

class ReverseUniqueTests(TestCase):

    def test_translations(self):
        activate('fi')
        fi = Lang.objects.create(code="fi")
        en = Lang.objects.create(code="en")
        a1 = Article.objects.create(pub_date=datetime.date.today())
        at1_fi = ArticleTranslation(article=a1, lang=fi, title='Otsikko', body='Diipadaapa')
        at1_fi.save()
        at2_en = ArticleTranslation(article=a1, lang=en, title='Title', body='Lalalalala')
        at2_en.save()
        with self.assertNumQueries(1):
            fetched = Article.objects.select_related('active_translation').get(
                active_translation__title='Otsikko')
            self.assertTrue(fetched.active_translation.title == 'Otsikko')
        a2 = Article.objects.create(pub_date=datetime.date.today())
        at2_fi = ArticleTranslation(article=a2, lang=fi, title='Atsikko', body='Diipadaapa',
                                    abstract='dipad')
        at2_fi.save()
        a3 = Article.objects.create(pub_date=datetime.date.today())
        at3_en = ArticleTranslation(article=a3, lang=en, title='A title', body='lalalalala',
                                    abstract='lala')
        at3_en.save()
        # Test model initialization with active_translation field.
        a3 = Article(id=a3.id, pub_date=a3.pub_date, active_translation=at3_en)
        a3.save()
        self.assertEqual(
            list(Article.objects.filter(active_translation__abstract=None)),
            [a1, a3])
        self.assertEqual(
            list(Article.objects.filter(active_translation__abstract=None,
                                        active_translation__pk__isnull=False)),
            [a1])
        activate('en')
        self.assertEqual(
            list(Article.objects.filter(active_translation__abstract=None)),
            [a1, a2])

    def test_foreign_key_raises_informative_does_not_exist(self):
        referrer = ArticleTranslation()
        with self.assertRaisesMessage(Article.DoesNotExist, 'ArticleTranslation has no article'):
            referrer.article

    def test_descriptor(self):
        activate('fi')
        fi = Lang.objects.create(code="fi")
        en = Lang.objects.create(code="en")
        a1 = Article.objects.create(pub_date=datetime.date.today())
        at1_fi = ArticleTranslation(article=a1, lang=fi, title='Otsikko', body='Diipadaapa')
        at1_fi.save()
        at2_en = ArticleTranslation(article=a1, lang=en, title='Title', body='Lalalalala')
        at2_en.save()
        with self.assertNumQueries(1):
            self.assertEqual(a1.active_translation.title, "Otsikko")
            self.assertEqual(a1.active_translation.body, "Diipadaapa")
        # The change in current languate isn't unfortunately noticed
        activate("en")
        with self.assertNumQueries(0):
            self.assertEqual(a1.active_translation.title, "Otsikko")
        a1 = Article.objects.get(pk=a1.pk)
        with self.assertNumQueries(1):
            self.assertEqual(a1.active_translation.title, "Title")

    def test_default_trans_article(self):
        activate('fi')
        a1 = DefaultTranslationArticle.objects.create(
            pub_date=datetime.date.today(), default_lang="fi")
        at1_fi = DefaultTranslationArticleTranslation(
            article=a1, lang='fi', title='Otsikko', body='Diipadaapa')
        at1_fi.save()
        at2_en = DefaultTranslationArticleTranslation(
            article=a1, lang='en', title='Title', body='Lalalalala')
        at2_en.save()
        with self.assertNumQueries(2):
            # 2 queries needed as the ORM doesn't know that active_translation ==
            # default_translation in this case.
            self.assertEqual(a1.active_translation.title, "Otsikko")
            self.assertEqual(a1.default_translation.title, "Otsikko")
        activate("en")
        a1 = DefaultTranslationArticle.objects.get(pk=a1.pk)
        with self.assertNumQueries(2):
            self.assertEqual(a1.active_translation.title, "Title")
            self.assertEqual(a1.default_translation.title, "Otsikko")
        qs = DefaultTranslationArticle.objects.filter(active_translation__title="Title")
        self.assertEqual(len(qs), 1)
        qs = DefaultTranslationArticle.objects.filter(active_translation__title="Otsikko")
        self.assertEqual(len(qs), 0)
        qs = DefaultTranslationArticle.objects.filter(default_translation__title="Title")
        self.assertEqual(len(qs), 0)
        qs = DefaultTranslationArticle.objects.filter(default_translation__title="Otsikko")
        self.assertEqual(len(qs), 1)
        qs = DefaultTranslationArticle.objects.filter(active_translation__abstract__isnull=True)
        self.assertEqual(len(qs), 1)
        qs = DefaultTranslationArticle.objects.filter(default_translation__abstract__isnull=True)
        self.assertEqual(len(qs), 1)
        with self.assertNumQueries(1):
            a1 = DefaultTranslationArticle.objects.select_related(
                'active_translation', 'default_translation').get(pk=a1.pk)
            self.assertEqual(a1.active_translation.title, "Title")
            self.assertEqual(a1.default_translation.title, "Otsikko")

        a1 = DefaultTranslationArticle.objects.only(
            'active_translation__title').select_related('active_translation').get(pk=a1.pk)
        with self.assertNumQueries(0):
            self.assertEqual(a1.active_translation.title, "Title")
        with self.assertNumQueries(1):
            self.assertEqual(a1.active_translation.body, "Lalalalala")

class FormsTests(TestCase):
    # ForeignObjects should not have any form fields, currently the user needs
    # to manually deal with the foreignobject relation.
    class ArticleForm(forms.ModelForm):
        class Meta:
            model = Article
            fields = '__all__'

    def test_foreign_object_form(self):
        # A very crude test checking that the non-concrete fields do not get form fields.
        form = FormsTests.ArticleForm()
        self.assertIn('id_pub_date', form.as_table())
        self.assertNotIn('active_translation', form.as_table())
        form = FormsTests.ArticleForm(data={'pub_date': str(datetime.date.today())})
        self.assertTrue(form.is_valid())
        a = form.save()
        self.assertEqual(a.pub_date, datetime.date.today())
        form = FormsTests.ArticleForm(instance=a, data={'pub_date': '2013-01-01'})
        a2 = form.save()
        self.assertEqual(a.pk, a2.pk)
        self.assertEqual(a2.pub_date, datetime.date(2013, 1, 1))

    def test_reservations(self):
        today = datetime.date.today()
        g1 = Guest.objects.create(name="John")
        g2 = Guest.objects.create(name="Mary")
        room1 = Room.objects.create()
        room2 = Room.objects.create()
        room3 = Room.objects.create()
        Reservation.objects.create(room=room1, guest=g1, from_date=today)
        Reservation.objects.create(
            room=room1, guest=g1, from_date=today - datetime.timedelta(days=10),
            until_date=today - datetime.timedelta(days=9))
        Reservation.objects.create(room=room2, guest=g2, from_date=today, until_date=today)
        Reservation.objects.create(
            room=room2, guest=g1, from_date=today - datetime.timedelta(days=10),
            until_date=today - datetime.timedelta(days=9))
        Reservation.objects.create(room=room3, guest=g2,
                                   from_date=today + datetime.timedelta(days=1))
        self.assertEqual(room1.current_reservation.guest, g1)
        self.assertEqual(room2.current_reservation.guest, g2)
        self.assertEqual(room3.current_reservation, None)
        self.assertQuerysetEqual(
            Room.objects.filter(current_reservation__isnull=True), [room3],
            lambda x: x)
        self.assertQuerysetEqual(
            Room.objects.filter(current_reservation__guest=g1), [room1],
            lambda x: x)
        self.assertQuerysetEqual(
            Room.objects.exclude(current_reservation__guest=g1).order_by('pk'),
            [room2, room3], lambda x: x)

class InheritanceTests(TestCase):
    def test_simple_join(self):
        c1 = Child.objects.create()
        self.assertQuerysetEqual(
            Child.objects.select_related('rel1'), [c1], lambda x: x)
        self.assertQuerysetEqual(
            Child.objects.select_related('rel2'), [c1], lambda x: x)
        self.assertQuerysetEqual(
            Child.objects.select_related('rel1', 'rel2'), [c1], lambda x: x)
        Rel1.objects.create(f1='foo', parent=c1)
        Rel2.objects.create(f1='foo', child=c1)
        with self.assertNumQueries(1):
            qs = list(Child.objects.select_related('rel1', 'rel2'))
            self.assertEqual(
                qs, [c1])
            self.assertEqual(qs[0].rel1.f1, "foo")
            self.assertEqual(qs[0].rel2.f1, "foo")
