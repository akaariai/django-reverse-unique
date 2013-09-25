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
            possible_models = [self.model] + [m for m in self.model.__mro__ if hasattr(m, '_meta')]
            possible_targets = [f for f in self.rel.to._meta.concrete_fields
                                if f.rel and f.rel.to in possible_models]
            if len(possible_targets) != 1:
                raise Exception("Found %s target fields instead of one, the fields found were %s."
                                % (len(possible_targets), [f.name for f in possible_targets]))
            related_field = possible_targets[0]
        else:
            related_field = self.model._meta.get_field_by_name(self.through)[0].field
        if related_field.rel.to._meta.concrete_model != self.model._meta.concrete_model:
            # We have found a foreign key pointing to parent model.
            # This will only work if the fk is pointing to a value
            # that can be found from the child model, too. This is
            # the case only when we have parent pointer in child
            # pointing to same field as the found foreign key is
            # pointing to. Lets find this out. And, lets handle
            # only the single column case for now.
            no_multicol_support_error = (
                "FIXME: no support for multicolumn joins in parent join case")
            assert len(related_field.to_fields) == 1, no_multicol_support_error
            to_fields = self._find_parent_link(related_field)
        else:
            to_fields = [f.attname for f in related_field.foreign_related_fields]
        del self.through
        self.to_fields = [f.attname for f in related_field.local_related_fields]
        self.from_fields = to_fields
        resolved_related_fields = super(ReverseUnique, self).resolve_related_fields()
        return resolved_related_fields

    def _find_parent_link(self, related_field):
        """
        Find a field containing the value of related_field in local concrete
        fields or raise an error if the value isn't available in local table.

        Technical reason for this is that parent model joining is done later
        than filter join production, and that means proucing a join against
        parent tables will not work.
        """
        # The hard part here is to verify that the value in fact can be found
        # from local field. Lets first build the ancestor link chain
        ancestor_links = []
        curr_model = self.model
        while True:
            found_link = curr_model._meta.get_ancestor_link(related_field.rel.to)
            if not found_link:
                # OK, we found to parent model. Lets check that the pointed to
                # field contains the correct value.
                last_link = ancestor_links[-1]
                if last_link.foreign_related_fields != related_field.foreign_related_fields:
                    value_not_found_from_local_model_error = (
                        "The needed value wasn't found from model %s - add ReverseUnique "
                        "to parent instead" % self.model._meta.model_name)
                    assert False, value_not_found_from_local_model_error
                break
            if ancestor_links:
                assert found_link.local_related_fields == ancestor_links[-1].foreign_related_fields
            ancestor_links.append(found_link)
            curr_model = found_link.rel.to
        return [self.model._meta.get_ancestor_link(related_field.rel.to).attname]

    def get_extra_restriction(self, where_class, alias, related_alias):
        qs = self.rel.to.objects.filter(self.filters).query
        my_table = self.model._meta.db_table
        rel_table = self.rel.to._meta.db_table
        illegal_tables = set([t for t in qs.tables if qs.alias_refcount[t] > 0]).difference(
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
