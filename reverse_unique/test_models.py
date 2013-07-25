from datetime import date

from django.db import models
from django.db.models import Q, F
from django.utils.translation import get_language
from reverse_unique import ReverseUnique

class Article(models.Model):
    pub_date = models.DateField()
    active_translation = ReverseUnique(
        "ArticleTranslation", filters=Q(lang=get_language))

    class Meta:
        app_label = 'reverse_unique'

class ArticleTranslation(models.Model):
    article = models.ForeignKey(Article)
    lang = models.CharField(max_length=2)
    title = models.CharField(max_length=100)
    abstract = models.CharField(max_length=100, null=True)
    body = models.TextField()

    class Meta:
        unique_together = ('article', 'lang')
        app_label = 'reverse_unique'


# The idea for DefaultTranslationArticle is that article's have default
# language. This allows testing of filter condition targeting both
# tables in the join.
class DefaultTranslationArticle(models.Model):
    pub_date = models.DateField()
    default_lang = models.CharField(max_length=2)
    active_translation = ReverseUnique(
        "DefaultTranslationArticleTranslation", filters=Q(lang=get_language))
    default_translation = ReverseUnique(
        "DefaultTranslationArticleTranslation", filters=Q(lang=F('article__default_lang')))

    class Meta:
        app_label = 'reverse_unique'

class DefaultTranslationArticleTranslation(models.Model):
    article = models.ForeignKey(DefaultTranslationArticle)
    lang = models.CharField(max_length=2)
    title = models.CharField(max_length=100)
    abstract = models.CharField(max_length=100, null=True)
    body = models.TextField()

    class Meta:
        unique_together = ('article', 'lang')
        app_label = 'reverse_unique'


class Guest(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = 'reverse_unique'

class Room(models.Model):
    current_reservation = ReverseUnique(
        "Reservation", through='reservations',
        filters=(Q(from_date__lte=date.today) & (
            Q(until_date__gte=date.today) | Q(until_date__isnull=True))))

    class Meta:
        app_label = 'reverse_unique'

class Reservation(models.Model):
    room = models.ForeignKey(Room, related_name='reservations')
    guest = models.ForeignKey(Guest)
    from_date = models.DateField()
    until_date = models.DateField(null=True)  # NULL means reservation "forever".

    class Meta:
        app_label = 'reverse_unique'

class Parent(models.Model):
    rel1 = ReverseUnique("Rel1", filters=Q(f1="foo"))

    class Meta:
        app_label = 'reverse_unique'

class Rel1(models.Model):
    parent = models.ForeignKey(Parent, related_name="rel1list")
    f1 = models.CharField(max_length=10)

    class Meta:
        app_label = 'reverse_unique'

class Child(Parent):
    rel2 = ReverseUnique("Rel2", filters=Q(f1="foo"))

    class Meta:
        app_label = 'reverse_unique'

class Rel2(models.Model):
    child = models.ForeignKey(Child, related_name="rel2list")
    f1 = models.CharField(max_length=10)

    class Meta:
        app_label = 'reverse_unique'
