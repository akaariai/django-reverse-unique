from django.db.models.fields import FieldDoesNotExist
from django.db.models.fields.related import (
    ReverseSingleRelatedObjectDescriptor, ForeignObject)


class ReverseUniqueDescriptor(ReverseSingleRelatedObjectDescriptor):
    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("%s must be accessed via instance" % self.field.name)
        setattr(instance, self.cache_name, value)
        if value is not None and not self.field.rel.multiple:
            setattr(value, self.field.related.get_cache_name(), instance)

    def __get__(self, instance, *args, **kwargs):
        try:
            return super(ReverseUniqueDescriptor, self).__get__(instance, *args, **kwargs)
        except self.field.rel.to.DoesNotExist:
            setattr(instance, self.cache_name, None)
            return None

class ReverseUnique(ForeignObject):
    requires_unique_target = False

    def __init__(self, *args, **kwargs):
        self.filters = kwargs.pop('filters')
        self.through = kwargs.pop('through', None)
        kwargs['from_fields'] = []
        kwargs['to_fields'] = []
        kwargs['null'] = True
        kwargs['related_name'] = '+'
        super(ReverseUnique, self).__init__(*args, **kwargs)

    def resolve_related_fields(self):
        if self.through is None:
            possible_targets = [f for f in self.rel.to._meta.concrete_fields
                                if f.rel and f.rel.to == self.model]
            if len(possible_targets) != 1:
                raise Exception("Found %s target fields instead of one, the fields found were %s."
                                % (len(possible_targets), [f.name for f in possible_targets]))
            related_field = possible_targets[0]
        else:
            related_field = self.model._meta.get_field_by_name(self.through)[0].field
        del self.through
        self.to_fields = related_field.from_fields
        self.from_fields = related_field.to_fields
        return related_field.reverse_related_fields

    def get_extra_restriction(self, where_class, alias, related_alias):
        qs = self.rel.to.objects.filter(self.filters).query
        my_table = self.model._meta.db_table
        rel_table = self.rel.to._meta.db_table
        illegal_tables = set(qs.tables).difference(
            set([my_table, rel_table]))
        if illegal_tables:
            raise Exception("This field's filters refers illegal tables: %s" % illegal_tables)
        where = qs.where
        where.relabel_aliases({my_table: related_alias, rel_table: alias})
        return where

    def get_extra_descriptor_filter(self, instance):
        return self.filters

    def get_path_info(self):
        ret = super(ReverseUnique, self).get_path_info()
        assert len(ret) == 1
        return [ret[0]._replace(direct=False)]

    def contribute_to_class(self, cls, name):
        super(ReverseUnique, self).contribute_to_class(cls, name)
        setattr(cls, self.name, ReverseUniqueDescriptor(self))
