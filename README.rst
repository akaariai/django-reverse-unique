django-reverse-unique
=====================

.. image:: https://github.com/akaariai/django-reverse-unique/workflows/Test/badge.svg
    :target: https://github.com/akaariai/django-reverse-unique/actions
    :alt: Build Status

.. image:: https://coveralls.io/repos/akaariai/django-reverse-unique/badge.svg?branch=master
    :target: https://coveralls.io/r/akaariai/django-reverse-unique?branch=master
    :alt: Coverage Status

A ReverseUnique model field implementation for Django

The ReverseUnique field can be used to access single model instances from
the reverse side of ForeignKey. Essentially, ReverseUnique can be used to
generate OneToOneField like behaviour in the reverse direction of a normal
ForeignKey. The idea is to add an unique filter condition when traversing the
foreign key to reverse direction.

To be able to use reverse unique, you will need a unique constraint for the
reverse side or otherwise know that only one instance on the reverse side can
match.

Example
~~~~~~~

It is always nice to see actual use cases. We will model employees with time
dependent salaries in this example. This use case could be modelled as::

    class Employee(models.Model):
        name = models.TextField()

    class EmployeeSalary(models.Model):
        employee = models.ForeignKey(Employee, related_name='employee_salaries')
        salary = models.IntegerField()
        valid_from = models.DateField()
        valid_until = models.DateField(null=True)

It is possible to save data like "Anssi has salary of 10€ from 2000-1-1 to 2009-12-31,
and salary of 11€ from 2010-1-1 to infinity (modelled as None in the models).

Unfortunately when using these models it isn't trivial to just fetch the
employee and his salary to display to the user. It would be possible to do so by
looping through all salaries of an employee and checking which of the EmployeeSalaries
is currently in effect. However, this approach has a couple of drawbacks:

  - It doesn't perform well in list views
  - Most of all It is impossible to execute queries that refer the employee's current
    salary. For example, getting the top 10 best paid employees or the average
    salary of employees is impossible to achieve in single query.

Django-reverse-unique to the rescue! Lets change the Employee model to::

    from datetime import datetime
    class Employee(models.Model):
        name = models.TextField()
        current_salary = models.ReverseUnique(
            "EmployeeSalary",
            filter=Q(valid_from__gte=datetime.now) &
                   (Q(valid_until__isnull=True) | Q(valid_until__lte=datetime.now))
        )

Now we can simply issue a query like::

    Employee.objects.order_by('current_salary__salary')[0:10]

or::

    Employee.objects.aggregate(avg_salary=Avg('current_salary__salary'))

What did happen there? We added a ReverseUnique field. This field is the reverse
of the EmployeeSalary.employee foreign key with an additional restriction that the
relation must be valid at the moment the query is executed. The first
"EmployeeSalary" argument refers to the EmployeeSalary model (we have to use
string as the EmployeeSalary model is defined after the Employee model). The
filter argument is a Q-object which can refer to the fields of the remote model.

Another common problem for Django applications is how to store model translations.
The storage problem can be solved with django-reverse-unique. Here is a complete
example for that use case::

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
    # Generated query is
    #    select article.*, article_translation.*
    #      from article
    #      join article_translation on article_translation.article_id = article.id
    #                               and article_translation.lang = 'fi'
    # If you activate "en" instead, the lang is changed.
    # Now you can access objs[0].active_translation without generating more
    # queries.

Similarly one could fetch current active reservation for a hotel room etc.

Installation
~~~~~~~~~~~~

The requirement for ReverseUnique is Django 1.6+. You will need to place the
reverse_unique directory in Python path, then just use it like done in above
example. The tests (reverse_unique/tests.py) contain a couple more examples.
Easiest way to install is::

    pip install -e git://github.com/akaariai/django-reverse-unique.git#egg=reverse_unique

Testing
~~~~~~~

You'll need to have a supported version of Django installed. Go to
testproject directory and run::

    python manage.py test reverse_unique
