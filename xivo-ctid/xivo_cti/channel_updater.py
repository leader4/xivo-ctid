# -*- coding: utf-8 -*-

# Copyright (C) 2007-2013 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import logging

from xivo_cti.ioc.context import context

logger = logging.getLogger(__name__)


def parse_new_caller_id(event):
    updater = context.get('channel_updater')
    updater.new_caller_id(event['Channel'], event['CallerIDName'], event['CallerIDNum'])


def parse_hold(event):
    logger.debug('Parse hold %s', event)
    updater = context.get('channel_updater')
    updater.set_hold(event['Channel'], event['Status'] == 'On')


def assert_has_channel(func):
    def _fn(self, *args, **kwargs):
        channel_name = args[0]
        if channel_name not in self.innerdata.channels:
            logger.warning('Trying to update an untracked channel %s', channel_name)
        else:
            func(self, *args, **kwargs)
    return _fn


class ChannelUpdater(object):

    def __init__(self, innerdata):
        self.innerdata = innerdata

    @assert_has_channel
    def new_caller_id(self, channel_name, name, number):
        channel = self.innerdata.channels[channel_name]
        channel.set_extra_data('xivo', 'calleridname', name)
        channel.set_extra_data('xivo', 'calleridnum', number)

    @assert_has_channel
    def set_hold(self, channel_name, status):
        channel = self.innerdata.channels[channel_name]
        self.innerdata.handle_cti_stack('setforce', ('channels', 'updatestatus', channel_name))
        channel.properties['holded'] = status
        self.innerdata.handle_cti_stack('empty_stack')
