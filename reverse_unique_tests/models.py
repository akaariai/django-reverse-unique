from datetime import date

from django.db import models
from django.db.models import Q, F
from django.utils.translation import get_language
from reverse_unique import ReverseUnique


def filter_lang():
    return Q(lang=get_language())


class Article(models.Model):
    pub_date = models.DateField()
    active_translation = ReverseUnique(
        "ArticleTranslation", filters=filter_lang)

    class Meta:
        app_label = 'reverse_unique'


class Lang(models.Model):
    code = models.CharField(max_length=2, primary_key=True)

    class Meta:
        app_label = 'reverse_unique'


class ArticleTranslation(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    lang = models.ForeignKey(Lang, on_delete=models.CASCADE)
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
        "DefaultTranslationArticleTranslation", filters=filter_lang)
    default_translation = ReverseUnique(
        "DefaultTranslationArticleTranslation", filters=Q(lang=F('article__default_lang')))

    class Meta:
        app_label = 'reverse_unique'


class DefaultTranslationArticleTranslation(models.Model):
    article = models.ForeignKey(DefaultTranslationArticle, on_delete=models.CASCADE)
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


def filter_reservations():
    return Q(from_date__lte=date.today()) & (
        Q(until_date__gte=date.today()) | Q(until_date__isnull=True))


class Room(models.Model):
    current_reservation = ReverseUnique(
        "Reservation", through='reservations',
        filters=filter_reservations)

    class Meta:
        app_label = 'reverse_unique'


class Reservation(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='reservations')
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE)
    from_date = models.DateField()
    until_date = models.DateField(null=True)  # NULL means reservation "forever".

    class Meta:
        app_label = 'reverse_unique'


class Parent(models.Model):
    rel1 = ReverseUnique("Rel1", filters=Q(f1="foo"))
    uniq_field = models.CharField(max_length=10, unique=True, null=True)

    class Meta:
        app_label = 'reverse_unique'


class Rel1(models.Model):
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name="rel1list")
    f1 = models.CharField(max_length=10)

    class Meta:
        app_label = 'reverse_unique'


class Child(Parent):
    rel2 = ReverseUnique("Rel2", filters=Q(f1="foo"))

    class Meta:
        app_label = 'reverse_unique'


class AnotherChild(Child):
    rel1_child = ReverseUnique("Rel1", filters=Q(f1__startswith="foo"))

    class Meta:
        app_label = 'reverse_unique'


class Rel2(models.Model):
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name="rel2list")
    f1 = models.CharField(max_length=10)

    class Meta:
        app_label = 'reverse_unique'


class Rel3(models.Model):
    a_model = models.ForeignKey(Parent, on_delete=models.CASCADE, to_field='uniq_field')

    class Meta:
        app_label = 'reverse_unique'
