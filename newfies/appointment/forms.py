#
# Newfies-Dialer License
# http://www.newfies-dialer.org
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) 2011-2013 Star2Billing S.L.
#
# The Initial Developer of the Original Code is
# Arezqui Belaid <info@star2billing.com>
#
from django.forms import ModelForm
from django.contrib.auth.forms import UserChangeForm
from django.utils.translation import ugettext as _
from appointment.models.users import CalendarUserProfile, CalendarUser
from appointment.models.events import Event
from appointment.models.calendars import Calendar


class CalendarUserProfileForm(ModelForm):
    """CalendarUserProfileForm"""

    class Meta:
        model = CalendarUserProfile


class EventAdminForm(ModelForm):
    """Admin Event ModelForm"""
    class Meta:
        model = Event
        exclude = ('parent_event', 'occ_count')


class EventForm(EventAdminForm):
    """Event ModelForm"""

    class Meta:
        model = Event
        exclude = ('parent_event', 'occ_count')

    def __init__(self, user, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)

        calendar_user_list = CalendarUserProfile.objects.values_list(
            'user_id', flat=True).filter(manager=user).order_by('id')

        calendar_list = Calendar.objects.values_list(
            'id', 'name').filter(user_id__in=calendar_user_list).order_by('id')
        self.fields['calendar'].choices = calendar_list


class CalendarUserNameChangeForm(UserChangeForm):
    """CalendarUserNameChangeForm is used to change CalendarUser username"""

    class Meta:
        model = CalendarUser
        fields = ["username"]

    def __init__(self, *args, **kwargs):
        super(CalendarUserNameChangeForm, self).__init__(*args, **kwargs)


class CalendarUserChangeDetailExtendForm(ModelForm):
    """A form used to change the detail of a CalendarUser in the manager UI."""
    class Meta:
        model = CalendarUserProfile
        exclude = ('manager', 'user')

    def __init__(self, user, *args, **kwargs):
        self.manager = user
        super(CalendarUserChangeDetailExtendForm, self).__init__(*args, **kwargs)


class CalendarForm(ModelForm):
    """CalendarForm"""
    class Meta:
        model = Calendar

    def __init__(self, user, *args, **kwargs):
        super(CalendarForm, self).__init__(*args, **kwargs)

        calendar_user_list = CalendarUserProfile.objects.values_list(
            'user_id', flat=True).filter(manager=user).order_by('id')
        self.fields['user'].choices = CalendarUser.objects.values_list(
            'id', 'username').filter(id__in=calendar_user_list).order_by('id')
