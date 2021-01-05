import decimal
import numbers

from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.forms.widgets import NumberInput
from django import forms

IdentifierValidator = RegexValidator("[a-z][a-z_]+")

MONEY_FIELD_DECIMAL_PLACES = 9
FORMATTED_DECIMAL_FIELD_DECIMAL_PLACES = 9
FORMATTED_DECIMAL_FIELD_MAX_DIGITS = 36


class InternalIdentifierField(models.CharField):

    def __init__(self, **kwargs):
        if "unique" not in kwargs:
            raise ValueError("Error! You must explicitly set the `unique` flag for `InternalIdentifierField`s.")
        kwargs.setdefault("max_length", 64)
        kwargs.setdefault("blank", True)
        kwargs.setdefault("null", bool(kwargs.get("blank")))  # If it's allowed to be blank, it should be null
        kwargs.setdefault("verbose_name", _("internal identifier"))
        kwargs.setdefault("help_text", _(u"Do not change this value if you are not sure what you are doing."))
        kwargs.setdefault("editable", False)
        super(InternalIdentifierField, self).__init__(**kwargs)
        self.validators.append(IdentifierValidator)

    def get_prep_value(self, value):
        # Save `None`s instead of falsy values (such as empty strings)
        # for `InternalIdentifierField`s to avoid `IntegrityError`s on unique fields.
        prepared_value = super(InternalIdentifierField, self).get_prep_value(value)
        if self.null:
            return prepared_value or None
        return prepared_value

    def deconstruct(self):
        (name, path, args, kwargs) = super(InternalIdentifierField, self).deconstruct()
        kwargs["null"] = self.null
        kwargs["unique"] = self.unique
        kwargs["blank"] = self.blank
        kwargs.pop("verbose_name", None)
        kwargs.pop("help_text", None)
        return name, path, args, kwargs


class FormattedDecimalFormField(forms.DecimalField):
    # Chrome automatically converts a step with more than 5 decimals places to scientific notation
    MAX_DECIMAL_PLACES_FOR_STEP = 5

    def widget_attrs(self, widget):
        # be more lenient when setting step than the default django widget_attrs
        if isinstance(widget, NumberInput) and 'step' not in widget.attrs:
            if self.decimal_places <= self.MAX_DECIMAL_PLACES_FOR_STEP:
                step = format(decimal.Decimal('1') / 10 ** self.decimal_places, 'f')
            else:
                step = 'any'
            widget.attrs.setdefault('step', step)
        return super(FormattedDecimalFormField, self).widget_attrs(widget)


class FormattedDecimalField(models.DecimalField):
    """
    DecimalField subclass to display decimal values in non-scientific
    format.
    """

    def value_from_object(self, obj):
        value = super(FormattedDecimalField, self).value_from_object(obj)
        if isinstance(value, numbers.Number):
            return self.format_decimal(decimal.Decimal(str(value)))

    def format_decimal(self, value, max_digits=100, exponent_limit=100):
        assert isinstance(value, decimal.Decimal)
        val = value.normalize()
        (sign, digits, exponent) = val.as_tuple()
        if exponent > exponent_limit:
            raise ValueError('Error! Exponent is too large for formatting: %r.' % value)
        elif exponent < -exponent_limit:
            raise ValueError('Error! Exponent is too small for formatting: %r.' % value)
        if len(digits) > max_digits:
            raise ValueError('Error! Too many digits for formatting: %r.' % value)
        return format(val, 'f')

    def formfield(self, **kwargs):
        kwargs.setdefault("form_class", FormattedDecimalFormField)
        return super(FormattedDecimalField, self).formfield(**kwargs)


class MoneyValueField(FormattedDecimalField):
    def __init__(self, **kwargs):
        kwargs.setdefault("decimal_places", MONEY_FIELD_DECIMAL_PLACES)
        kwargs.setdefault("max_digits", FORMATTED_DECIMAL_FIELD_MAX_DIGITS)
        super(MoneyValueField, self).__init__(**kwargs)


class QuantityField(FormattedDecimalField):
    def __init__(self, **kwargs):
        kwargs.setdefault("decimal_places", FORMATTED_DECIMAL_FIELD_DECIMAL_PLACES)
        kwargs.setdefault("max_digits", FORMATTED_DECIMAL_FIELD_MAX_DIGITS)
        kwargs.setdefault("default", 0)
        super(QuantityField, self).__init__(**kwargs)
