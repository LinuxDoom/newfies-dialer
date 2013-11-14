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
#from django.conf import settings
#from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render_to_response, get_object_or_404, render
from django.utils.translation import ugettext as _
from django.template.context import RequestContext
from django.contrib.auth.forms import PasswordChangeForm, \
    UserCreationForm, AdminPasswordChangeForm
from django.contrib.auth.models import Permission
#from django.views.decorators.csrf import csrf_exempt
from appointment.models.calendars import Calendar
from appointment.models.events import Event
from appointment.constants import CALENDAR_USER_COLUMN_NAME, CALENDAR_COLUMN_NAME,\
    EVENT_COLUMN_NAME
from appointment.forms import CalendarUserChangeDetailExtendForm, \
    CalendarUserNameChangeForm, CalendarForm, EventForm
from appointment.models.users import CalendarUserProfile, CalendarUser
from user_profile.models import Manager
from user_profile.forms import UserChangeDetailForm
from dialer_campaign.function_def import user_dialer_setting_msg
from common.common_functions import get_pagination_vars
import json


@permission_required('appointment.view_calendar_user', login_url='/')
@login_required
def calendar_user_list(request):
    """CalendarUser list for the logged in Manager

    **Attributes**:

        * ``template`` - frontend/appointment/calendar_user/list.html

    **Logic Description**:

        * List all calendar_user which belong to the logged in manager.
    """
    sort_col_field_list = ['user', 'updated_date']
    default_sort_field = 'id'
    pagination_data = \
        get_pagination_vars(request, sort_col_field_list, default_sort_field)

    PAGE_SIZE = pagination_data['PAGE_SIZE']
    sort_order = pagination_data['sort_order']

    calendar_user_list = CalendarUserProfile.objects\
        .filter(manager=request.user).order_by(sort_order)

    template = 'frontend/appointment/calendar_user/list.html'
    data = {
        'msg': request.session.get('msg'),
        'calendar_user_list': calendar_user_list,
        'total_calendar_user': calendar_user_list.count(),
        'PAGE_SIZE': PAGE_SIZE,
        'CALENDAR_USER_COLUMN_NAME': CALENDAR_USER_COLUMN_NAME,
        'col_name_with_order': pagination_data['col_name_with_order'],
        'dialer_setting_msg': user_dialer_setting_msg(request.user),
    }
    request.session['msg'] = ''
    request.session['error_msg'] = ''
    return render_to_response(template, data,
                              context_instance=RequestContext(request))


@permission_required('appointment.add_calendaruserprofile', login_url='/')
@login_required
def calendar_user_add(request):
    """Add new calendar user for the logged in manager

    **Attributes**:

        * ``form`` - UserCreationForm
        * ``template`` - frontend/appointment/calendar_user/change.html

    **Logic Description**:

        * Add a new calendar user which will belong to the logged in manager
          via the UserCreationForm & get redirected to the calendar user list
    """
    form = UserCreationForm()
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            calendar_user = form.save()

            calendar_user_profile = CalendarUserProfile.objects.create(
                user=calendar_user,
                manager=Manager.objects.get(username=request.user)
            )

            request.session["msg"] = _('"%(name)s" added as calendar user.') %\
                {'name': request.POST['username']}
            return HttpResponseRedirect('/calendar_user/%s/' % str(calendar_user_profile.id))

    template = 'frontend/appointment/calendar_user/change.html'
    data = {
        'form': form,
        'action': 'add',
        'dialer_setting_msg': user_dialer_setting_msg(request.user),
    }
    return render_to_response(template, data,
                              context_instance=RequestContext(request))


@permission_required('appointment.delete_calendaruserprofile', login_url='/')
@login_required
def calendar_user_del(request, object_id):
    """Delete a calendar_user for a logged in manager

    **Attributes**:

        * ``object_id`` - Selected calendar_user object
        * ``object_list`` - Selected calendar_user objects

    **Logic Description**:

        * Delete calendar_user from a calendar_user list.
    """
    if int(object_id) != 0:
        # When object_id is not 0
        # 1) delete calendar_user profile & agent
        calendar_user_profile = get_object_or_404(
            CalendarUserProfile, pk=object_id, manager_id=request.user.id)
        calendar_user = CalendarUser.objects.get(pk=calendar_user_profile.user_id)

        request.session["msg"] = _('"%(name)s" is deleted.')\
            % {'name': calendar_user}
        calendar_user.delete()
    else:
        # When object_id is 0 (Multiple records delete)
        values = request.POST.getlist('select')
        values = ", ".join(["%s" % el for el in values])
        try:
            # 1) delete all calendar users belonging to a managers
            calendar_user_list = CalendarUserProfile.objects\
                .filter(manager_id=request.user.id)\
                .extra(where=['id IN (%s)' % values])

            if calendar_user_list:
                user_list = calendar_user_list.values_list('user_id', flat=True)
                calendar_users = CalendarUser.objects.filter(pk__in=user_list)
                request.session["msg"] = _('%(count)s calendar user(s) are deleted.')\
                    % {'count': calendar_user_list.count()}
                calendar_users.delete()
        except:
            raise Http404

    return HttpResponseRedirect('/calendar_user/')


@permission_required('appointment.change_calendaruserprofile', login_url='/')
@login_required
def calendar_user_change(request, object_id):
    """Update/Delete calendar user for the logged in manager

    **Attributes**:

        * ``object_id`` - Selected calendar_user object
        * ``form`` - CalendarUserChangeDetailExtendForm, CalendarUserNameChangeForm
        * ``template`` - frontend/appointment/calendar_user/change.html

    **Logic Description**:

        * Update/delete selected calendar user from the calendar_user list
          via CalendarUserChangeDetailExtendForm & get redirected to calendar_user list
    """
    calendar_user_profile = get_object_or_404(CalendarUserProfile, pk=object_id, manager_id=request.user.id)
    calendar_user_userdetail = get_object_or_404(CalendarUser, pk=calendar_user_profile.user_id)

    form = CalendarUserChangeDetailExtendForm(request.user, instance=calendar_user_profile)
    calendar_user_username_form = CalendarUserNameChangeForm(
        initial={'username': calendar_user_userdetail.username,
                 'password': calendar_user_userdetail.password})

    if request.method == 'POST':
        if request.POST.get('delete'):
            calendar_user_del(request, object_id)
            return HttpResponseRedirect('/calendar_user/')
        else:
            form = CalendarUserChangeDetailExtendForm(request.user, request.POST, instance=calendar_user_profile)

            calendar_user_username_form = CalendarUserNameChangeForm(request.POST,
                initial={'password': calendar_user_userdetail.password},
                instance=calendar_user_userdetail)

            # Save calendar_user username
            if calendar_user_username_form.is_valid():
                calendar_user_username_form.save()

                if form.is_valid():
                    form.save()
                    request.session["msg"] = _('"%(name)s" is updated.') \
                        % {'name': calendar_user_profile.user}
                    return HttpResponseRedirect('/calendar_user/')

    template = 'frontend/appointment/calendar_user/change.html'
    data = {
        'form': form,
        'calendar_user_username_form': calendar_user_username_form,
        'action': 'update',
        'dialer_setting_msg': user_dialer_setting_msg(request.user),
    }
    return render_to_response(template, data,
                              context_instance=RequestContext(request))


@login_required
def calendar_user_change_password(request, object_id):
    """
    CalendarUser Detail change

    **Attributes**:

        * ``form`` - AdminPasswordChangeForm
        * ``template`` - 'frontend/appointment/calendar_user/change_password.html',
             'frontend/registration/user_detail_change.html'

    **Logic Description**:

        * Reset calendar_user password.
    """
    msg_pass = ''
    error_pass = ''

    calendar_user_userdetail = get_object_or_404(CalendarUser, pk=object_id)
    calendar_user_username = calendar_user_userdetail.username

    user_password_form = AdminPasswordChangeForm(user=calendar_user_userdetail)
    if request.method == 'POST':
        user_password_form = AdminPasswordChangeForm(user=calendar_user_userdetail,
                                                     data=request.POST)
        if user_password_form.is_valid():
            user_password_form.save()
            request.session["msg"] = _('%s password has been changed.' % calendar_user_username)
            return HttpResponseRedirect('/agent/')
        else:
            error_pass = _('please correct the errors below.')

    template = 'frontend/appointment/calendar_user/change_password.html'
    data = {
        'calendar_user_username': calendar_user_username,
        'user_password_form': user_password_form,
        'msg_pass': msg_pass,
        'error_pass': error_pass,
    }
    request.session['msg'] = ''
    request.session['error_msg'] = ''
    return render_to_response(template, data,
                              context_instance=RequestContext(request))


@permission_required('calendar.view_calendar', login_url='/')
@login_required
def calendar_list(request):
    """Calendar list for the logged in user

    **Attributes**:

        * ``template`` - frontend/appointment/calendar/list.html

    **Logic Description**:

        * List all calendars which belong to the logged in user.
    """
    sort_col_field_list = ['id', 'name', 'user', 'max_concurrent',
                           'created_date']
    default_sort_field = 'id'
    pagination_data = \
        get_pagination_vars(request, sort_col_field_list, default_sort_field)

    PAGE_SIZE = pagination_data['PAGE_SIZE']
    sort_order = pagination_data['sort_order']

    calendar_user_list = CalendarUserProfile.objects.values_list('user_id', flat=True).filter(manager=request.user).order_by('id')

    calendar_list = Calendar.objects\
        .filter(user_id__in=calendar_user_list).order_by(sort_order)

    template = 'frontend/appointment/calendar/list.html'
    data = {
        'msg': request.session.get('msg'),
        'calendar_list': calendar_list,
        'total_calendar': calendar_list.count(),
        'PAGE_SIZE': PAGE_SIZE,
        'CALENDAR_COLUMN_NAME': CALENDAR_COLUMN_NAME,
        'col_name_with_order': pagination_data['col_name_with_order'],
        'dialer_setting_msg': user_dialer_setting_msg(request.user),
    }
    request.session['msg'] = ''
    request.session['error_msg'] = ''
    return render_to_response(template, data,
                              context_instance=RequestContext(request))


@permission_required('calendar.add_calendar', login_url='/')
@login_required
def calendar_add(request):
    """Add a new calendar for the logged in user

    **Attributes**:

        * ``form`` - CalendarForm
        * ``template`` - frontend/appointment/calendar/change.html

    **Logic Description**:

        * Add new contact belonging to the logged in user
          via ContactForm & get redirected to the contact list
    """
    form = CalendarForm(request.user)
    error_msg = False
    # Add contact
    if request.method == 'POST':
        form = CalendarForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            request.session["msg"] = _('"%s" is added.') % request.POST['name']
            return HttpResponseRedirect('/calendar/')

    template = 'frontend/appointment/calendar/change.html'
    data = {
        'form': form,
        'action': 'add',
        'error_msg': error_msg,
        'dialer_setting_msg': user_dialer_setting_msg(request.user),
    }
    return render_to_response(template, data,
                              context_instance=RequestContext(request))


@permission_required('calendar.delete_calendar', login_url='/')
@login_required
def calendar_del(request, object_id):
    """Delete calendar for the logged in user

    **Attributes**:

        * ``object_id`` - Selected calendar object
        * ``object_list`` - Selected calendar objects

    **Logic Description**:

        * Delete selected calendar from the calendar list
    """
    if int(object_id) != 0:
        # When object_id is not 0
        calendar = get_object_or_404(Calendar, pk=object_id)

        # Delete Calendar
        request.session["msg"] = _('"%s" is deleted.') % calendar.name
        calendar.delete()
    else:
        # When object_id is 0 (Multiple records delete)
        values = request.POST.getlist('select')
        values = ", ".join(["%s" % el for el in values])

        try:
            calendar_list = Calendar.objects.extra(where=['id IN (%s)' % values])
            if calendar_list:
                request.session["msg"] =\
                    _('%s calendar(s) are deleted.') % calendar_list.count()
                calendar_list.delete()
        except:
            raise Http404
    return HttpResponseRedirect('/calendar/')


@permission_required('calendar.change_calendar', login_url='/')
@login_required
def calendar_change(request, object_id):
    """Update/Delete calendar for the logged in user

    **Attributes**:

        * ``object_id`` - Selected calendar object
        * ``form`` - CalendarForm
        * ``template`` - frontend/appointment/calendar/change.html

    **Logic Description**:

        * Update/delete selected calendar from the calendar list
          via CalendarForm & get redirected to the calendar list
    """
    calendar = get_object_or_404(Calendar, pk=object_id)

    form = CalendarForm(request.user, instance=calendar)
    if request.method == 'POST':
        # Delete calendar
        if request.POST.get('delete'):
            return HttpResponseRedirect('/calendar/del/%s/' % object_id)
        else:
            # Update calendar
            form = CalendarForm(request.user, request.POST, instance=calendar)
            if form.is_valid():
                form.save()
                request.session["msg"] = _('"%s" is updated.') % request.POST['name']
                return HttpResponseRedirect('/calendar/')

    template = 'frontend/appointment/calendar/change.html'
    data = {
        'form': form,
        'action': 'update',
        'dialer_setting_msg': user_dialer_setting_msg(request.user),
    }
    return render_to_response(template, data,
                              context_instance=RequestContext(request))


@permission_required('appointment.view_event', login_url='/')
@login_required
def event_list(request):
    """Event list for the logged in user

    **Attributes**:

        * ``template`` - frontend/appointment/event/list.html

    **Logic Description**:

        * List all events which belong to the logged in user.
    """
    sort_col_field_list = ['id', 'start', 'end', 'title',
                           'calendar', 'status']
    default_sort_field = 'id'
    pagination_data = \
        get_pagination_vars(request, sort_col_field_list, default_sort_field)

    PAGE_SIZE = pagination_data['PAGE_SIZE']
    sort_order = pagination_data['sort_order']

    calendar_user_list = CalendarUserProfile.objects.values_list(
        'user_id', flat=True).filter(manager=request.user).order_by('id')

    calendar_id_list = Calendar.objects.values_list(
        'id', flat=True).filter(user_id__in=calendar_user_list).order_by('id')

    event_list = Event.objects.filter(
        calendar_id__in=calendar_id_list).order_by(sort_order)

    template = 'frontend/appointment/event/list.html'
    data = {
        'msg': request.session.get('msg'),
        'event_list': event_list,
        'total_event': event_list.count(),
        'PAGE_SIZE': PAGE_SIZE,
        'EVENT_COLUMN_NAME': EVENT_COLUMN_NAME,
        'col_name_with_order': pagination_data['col_name_with_order'],
        'dialer_setting_msg': user_dialer_setting_msg(request.user),
    }
    request.session['msg'] = ''
    request.session['error_msg'] = ''
    return render_to_response(template, data,
                              context_instance=RequestContext(request))


@permission_required('appointment.add_event', login_url='/')
@login_required
def event_add(request):
    """Add a new event for the logged in user

    **Attributes**:

        * ``form`` - EventForm
        * ``template`` - frontend/appointment/event/change.html

    **Logic Description**:

        * Add new event belonging to the logged in user
          via EventForm & get redirected to the event list
    """
    form = EventForm(request.user)
    error_msg = False
    # Add event
    if request.method == 'POST':
        form = EventForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            request.session["msg"] = _('"%s" is added.') % request.POST['title']
            return HttpResponseRedirect('/event/')

    template = 'frontend/appointment/event/change.html'
    data = {
        'form': form,
        'action': 'add',
        'error_msg': error_msg,
        'dialer_setting_msg': user_dialer_setting_msg(request.user),
    }
    return render_to_response(template, data,
                              context_instance=RequestContext(request))


@permission_required('appointment.delete_event', login_url='/')
@login_required
def event_del(request, object_id):
    """Delete event for the logged in user

    **Attributes**:

        * ``object_id`` - Selected event object
        * ``object_list`` - Selected event objects

    **Logic Description**:

        * Delete selected event from the event list
    """
    if int(object_id) != 0:
        # When object_id is not 0
        event = get_object_or_404(Event, pk=object_id)

        # Delete Event
        request.session["msg"] = _('"%s" is deleted.') % event.title
        event.delete()
    else:
        # When object_id is 0 (Multiple records delete)
        values = request.POST.getlist('select')
        values = ", ".join(["%s" % el for el in values])

        try:
            event_list = Event.objects.extra(where=['id IN (%s)' % values])
            if event_list:
                request.session["msg"] =\
                    _('%s event(s) are deleted.') % event_list.count()
                event_list.delete()
        except:
            raise Http404
    return HttpResponseRedirect('/event/')


@permission_required('appointment.change_event', login_url='/')
@login_required
def event_change(request, object_id):
    """Update/Delete event for the logged in user

    **Attributes**:

        * ``object_id`` - Selected event object
        * ``form`` - EventForm
        * ``template`` - frontend/appointment/event/change.html

    **Logic Description**:

        * Update/delete selected event from the event list
          via EventForm & get redirected to the event list
    """
    event = get_object_or_404(Event, pk=object_id)

    form = EventForm(request.user, instance=event)
    if request.method == 'POST':
        # Delete event
        if request.POST.get('delete'):
            return HttpResponseRedirect('/event/del/%s/' % object_id)
        else:
            # Update event
            form = EventForm(request.user, request.POST, instance=event)
            if form.is_valid():
                form.save()
                request.session["msg"] = _('"%s" is updated.') % request.POST['title']
                return HttpResponseRedirect('/event/')

    template = 'frontend/appointment/event/change.html'
    data = {
        'form': form,
        'action': 'update',
        'dialer_setting_msg': user_dialer_setting_msg(request.user),
    }
    return render_to_response(template, data,
                              context_instance=RequestContext(request))
