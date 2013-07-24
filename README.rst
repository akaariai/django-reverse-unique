django-reverse-unique
=====================

A ReverseUnique model field implementation for Django

The ReverseUnique field can be used to access single model instances from
the reverse side of ForeignKey. Essentially, ReverseUnique can be used to
generate OneToOneField like behaviour from a ForeignKey. You will need an
unique filter condition on the reverse ForeignKey relation so that there
is at most one instance on the reverse side that can match.

To be able to use reverse unique, you will need a unique constraint for the
reverse side or otherwise know that only one instance on the reverse side can
match.

The usage is simple::

    from django.db import models
    from reverse_unique import ReverseUnique
    from django.utils.translation import get_language, activate

    class Article(models.Model):
        active_translation = ReverseUnique("ArticleTranslation",
                                           filters=Q(lang=get_language))

    class ArticleTranslation(models.Model):
        article = models.ForeignKey(Article)
        lang = models.CharField(max_length=2)
        title = models.CharField(max_length=100)
        body = models.TextField()

        class Meta:
            unique_together = ('article', 'lang')

    activate("fi")
    objs = Article.objects.filter(
        active_translation__title__icontains="foo"
    ).select_related('active_translation')
    # Generated query is something like:
    #    select article.*, article_translation.*
    #      from article
    #      join article_translation on article_translation.article_id = article.id
    #                               and article_translation.lang = 'fi'
    # If you activate "en" instead, the lang is changed.
    # Now you can access objs[0].active_translation without generating more
    # queries.

    # The active_translation lookup should work in all places where core
    # fields can be used.

Similarly one could fetch current active reservation for a hotel room etc.

Installation
~~~~~~~~~~~~

The requirement for ReverseUnique is Django 1.6+. You will need to place the
reverse_unique directory in Python path, then just use it like done in above
example. The tests (reverse_unique/tests.py) contain a couple more examples.
No setup.py yet, sorry.

Known issues
~~~~~~~~~~~~

None currently. Note that django-reverse-unique is at alpha stage currently.
