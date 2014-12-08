django-reverse-unique
=====================

A ReverseUnique and LatestRelated model field implementations for Django

The ReverseUnique field can be used to access single model instances from
the reverse side of ForeignKey. Essentially, ReverseUnique can be used to
generate OneToOneField like behaviour in the reverse direction of a normal
ForeignKey. The idea is to add an unique filter condition when traversing the
foreign key to reverse direction.

LatestRelated can be used to fetch latest object from a related model by some
field. The typical example is messaging board threads, and posts to each thread.
One typically wants to construct a list view ordered by latest post to each
thread, and also show the latest post title (or expert, or poster) for each
thread. LatestRelated allows one to filter(), select_related(), order_by()
and so on on latest related object.

To be able to use reverse unique, you will need a unique constraint for the
reverse side or otherwise know that only one instance on the reverse side can
match.

LatestRelated example
~~~~~~~~~~~~~~~~~~~~~

This example is directly from the tests. The models are::

    class Task(models.Model):
        name = models.TextField()
        last_taskmodification = LatestRelated("TaskModification", by='-created')

        class Meta:
            app_label = 'reverse_unique'


    class TaskModification(models.Model):
        task = models.ForeignKey(Task)
        modification = models.TextField()
        created = models.DateTimeField()

        class Meta:
            app_label = 'reverse_unique'
            unique_together = [('task', 'created')]

Here the last_taskmodification field is defined so that it will fetch the
last modification by the TaskModification model's created field.

Example queries::

    self.t1 = Task.objects.create(name='Foo')
    self.t2 = Task.objects.create(name='Foo2')
    self.t1_tm1 = TaskModification.objects.create(task=self.t1, created=datetime.datetime.now(), modification='Earlier')
    self.t1_tm2 = TaskModification.objects.create(task=self.t1, created=datetime.datetime.now(), modification='Later')
    self.t2_tm1 = TaskModification.objects.create(task=self.t2, created=datetime.datetime.now(), modification='Earlier2')
    self.t2_tm2 = TaskModification.objects.create(task=self.t2, created=datetime.datetime.now(), modification='Later2')
    with assertNumQueries(1):
        qs = Task.objects.select_related('last_taskmodification').order_by('pk')
        self.assertEqual(len(qs), 2)
        self.assertEqual(qs[0], self.t1)
        self.assertEqual(qs[1], self.t2)
        self.assertEqual(qs[0].last_taskmodification, self.t1_tm2)
        self.assertEqual(qs[1].last_taskmodification, self.t2_tm2)
    # Fetch latest threads
    Task.objects.order_by('last_taskmodification__created')[0:10]
    # Fetch threads not touched after start of 2014
    Task.objecs.filter(last_taskmodification__created__lte=datetime.date(2014, 01, 01))

These queries will fetch the tasks and their associated latest modification, in
a single query. The SQL looks something like this (for the select_related query)::
    
    SELECT "reverse_unique_task"."id", "reverse_unique_task"."name", "reverse_unique_taskmodification"."id",
           "reverse_unique_taskmodification"."task_id", "reverse_unique_taskmodification"."modification",
           "reverse_unique_taskmodification"."created"
      FROM "reverse_unique_task"
      LEFT OUTER JOIN "reverse_unique_taskmodification" ON (
               "reverse_unique_task"."id" = "reverse_unique_taskmodification"."task_id"
                AND ("reverse_unique_taskmodification"."created" =
                        (SELECT MAX("reverse_unique_taskmodification"."created") AS "by"
                           FROM "reverse_unique_taskmodification"
                          WHERE "reverse_unique_task"."id" = "reverse_unique_taskmodification"."task_id"))
            )


ReverseUnique Example
~~~~~~~~~~~~~~~~~~~~~

It is always nice to see actual use cases. We will model employees with time
dependent salaries in this example. This use case could be modelled as::

    class Employee(models.Model):
        name = models.TextField()

    class EmployeeSalary(models.Model):
        employee = models.ForeignKey(Employee, related_name='employee_salaries')
        salary = models.IntegerField()
        valid_from = models.DateField()
        valid_until = models.DateField(null=True)

It is possible to save data like "Anssi has salary of 10€ from 2000-1-1 to 2010-1-1,
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
