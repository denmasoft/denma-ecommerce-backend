from django.db import models
from oscar.apps.address.abstract_models import (AbstractUserAddress)
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy
from oscar.models.fields import PhoneNumberField


class UserAddress(AbstractUserAddress):
    fax = PhoneNumberField(
        _("Fax"), blank=True,
        help_text=_("In case we need to send your order."))
    company = models.CharField(_("Company"), max_length=255, blank=True)


from oscar.apps.address.models import *