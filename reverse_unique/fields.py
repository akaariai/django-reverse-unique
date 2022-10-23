import django
from django.db import models
from django.db.models.fields.related import ForeignObject
from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor


class ReverseUniqueDescriptor(ForwardManyToOneDescriptor):
    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("%s must be accessed via instance" % self.field.name)
        instance.__dict__[self.field.get_cache_name()] = value
        if value is not None and not self.field.remote_field.multiple:
            setattr(value, self.field.related.get_cache_name(), instance)

    def __get__(self, instance, *args, **kwargs):
        try:
            return super().__get__(instance, *args, **kwargs)
        except self.field.remote_field.model.DoesNotExist:
            instance.__dict__[self.field.get_cache_name()] = None
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
        kwargs['on_delete'] = models.DO_NOTHING
        super().__init__(*args, **kwargs)

    def resolve_related_fields(self):
        if self.through is None:
            possible_models = [self.model] + [m for m in self.model.__mro__ if hasattr(m, '_meta')]
            possible_targets = [f for f in self.remote_field.model._meta.concrete_fields
                                if f.remote_field and f.remote_field.model in possible_models]
            if len(possible_targets) != 1:
                raise Exception("Found %s target fields instead of one, the fields found were %s."
                                % (len(possible_targets), [f.name for f in possible_targets]))
            related_field = possible_targets[0]
        else:
            related_field = self.model._meta.get_field(self.through).field
        if related_field.remote_field.model._meta.concrete_model != self.model._meta.concrete_model:
            # We have found a foreign key pointing to parent model.
            # This will only work if the fk is pointing to a value
            # that can be found from the child model, too. This is
            # the case only when we have parent pointer in child
            # pointing to same field as the found foreign key is
            # pointing to. Lets find this out. And, lets handle
            # only the single column case for now.
            if len(related_field.to_fields) > 1:
                raise ValueError(
                    "FIXME: No support for multi-column joins in parent join case."
                )
            to_fields = self._find_parent_link(related_field)
        else:
            to_fields = [f.name for f in related_field.foreign_related_fields]
        self.to_fields = [f.name for f in related_field.local_related_fields]
        self.from_fields = to_fields
        return super().resolve_related_fields()

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
            found_link = curr_model._meta.get_ancestor_link(related_field.remote_field.model)
            if not found_link:
                # OK, we found to parent model. Lets check that the pointed to
                # field contains the correct value.
                last_link = ancestor_links[-1]
                if last_link.foreign_related_fields != related_field.foreign_related_fields:
                    curr_opts = curr_model._meta
                    rel_opts = self.remote_field.model._meta
                    opts = self.model._meta
                    raise ValueError(
                        "The field(s) %s of model %s.%s which %s.%s.%s is "
                        "pointing to cannot be found from %s.%s. "
                        "Add ReverseUnique to parent instead." % (
                            ', '.join([f.name for f in related_field.foreign_related_fields]),
                            curr_opts.app_label, curr_opts.object_name,
                            rel_opts.app_label, rel_opts.object_name, related_field.name,
                            opts.app_label, opts.object_name
                        )
                    )
                break
            if ancestor_links:
                assert found_link.local_related_fields == ancestor_links[-1].foreign_related_fields
            ancestor_links.append(found_link)
            curr_model = found_link.remote_field.model
        return [self.model._meta.get_ancestor_link(related_field.remote_field.model).name]

    def get_filters(self):
        if callable(self.filters):
            return self.filters()
        else:
            return self.filters

    def _get_extra_restriction(self, alias, related_alias):
        remote_model = self.remote_field.model
        qs = remote_model.objects.filter(self.get_filters()).query
        my_table = self.model._meta.db_table
        rel_table = remote_model._meta.db_table
        illegal_tables = set([t for t in qs.alias_map if qs.alias_refcount[t] > 0]).difference(
            set([my_table, rel_table]))
        if illegal_tables:
            raise Exception("This field's filters refers illegal tables: %s" % illegal_tables)
        where = qs.where
        where.relabel_aliases({my_table: related_alias, rel_table: alias})
        return where

    if django.VERSION[0] >= 4:
        get_extra_restriction = _get_extra_restriction
    else:
        def get_extra_restriction(self, where_class, alias, related_alias):
            return self._get_extra_restriction(alias, related_alias)

    def get_extra_descriptor_filter(self, instance):
        return self.get_filters()

    def get_path_info(self, *args, **kwargs):
        ret = super().get_path_info(*args, **kwargs)
        assert len(ret) == 1
        return [ret[0]._replace(direct=False)]

    def contribute_to_class(self, cls, name):
        super().contribute_to_class(cls, name)
        setattr(cls, self.name, ReverseUniqueDescriptor(self))

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['filters'] = self.filters
        if self.through is not None:
            kwargs['through'] = self.through
        return name, path, args, kwargs
