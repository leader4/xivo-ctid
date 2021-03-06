# -*- coding: utf-8 -*-

# Copyright (C) 2013-2014 Avencall
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

from xivo_cti.services.call import helper
from xivo_cti.services.call.call import _Channel
from xivo.asterisk.extension import Extension
from xivo_cti.model.endpoint_status import EndpointStatus
from xivo.asterisk.protocol_interface import InvalidChannelError

logger = logging.getLogger(__name__)


class CallReceiver(object):

    def __init__(self, call_storage):
        self._call_storage = call_storage

    def handle_newstate(self, event):
        channel = event['Channel']
        status = helper.channel_state_to_status(event['ChannelState'])

        if status is not None:
            self._update_channel_status(channel, status)

    def handle_hangup(self, event):
        channel = event['Channel']
        status = EndpointStatus.available
        uniqueid = event['Uniqueid']

        self._update_channel_status(channel, status)
        self._call_storage.end_call(uniqueid)

    def _update_channel_status(self, channel, status):
        try:
            extension = helper.get_extension_from_channel(channel)
        except (InvalidChannelError) as e:
            logger.error(e)
        else:
            self._call_storage.update_endpoint_status(extension, status)

    def handle_dial(self, event):
        if event['SubEvent'] == 'Begin':
            self._handle_dial_begin(event)

    def handle_bridge(self, event):
        uniqueid_1 = event.get('Uniqueid1')

        if event['Bridgestate'] == 'Link':
            c1 = event['Channel1']
            c2 = event['Channel2']
            self._add_channel(c2, c1, uniqueid_1, event['Uniqueid2'])
        elif event['Bridgestate'] == 'Unlink':
            self._call_storage.end_call(uniqueid_1)

    def _handle_dial_begin(self, event):
        channel_source = event['Channel']
        channel_destination = event['Destination']
        destination_uniqueid = event['DestUniqueID']
        uniqueid = event['UniqueID']

        self._add_channel(channel_source, channel_destination, uniqueid, destination_uniqueid)

    def handle_new_channel(self, event):
        try:
            channel = event['Channel']
            unique_id = event['Uniqueid']
            source_exten = helper.get_extension_from_channel(channel)
        except (InvalidChannelError, KeyError):
            logger.debug('ignoring %s', event)
            return

        self._call_storage.new_call(
            unique_id,
            '',
            _Channel(source_exten, channel),
            _Channel(Extension('', '', True), ''),
        )

    def handle_masquerade(self, event):
        self._call_storage.merge_local_channels(event['Original'])

    def _add_channel(self, channel_source, channel_destination, uniqueid, destination_uniqueid):
        try:
            extension_source = helper.get_extension_from_channel(channel_source)
            extension_destination = helper.get_extension_from_channel(channel_destination)
        except (InvalidChannelError) as e:
            logger.error(e)
        else:
            self._call_storage.new_call(
                uniqueid,
                destination_uniqueid,
                _Channel(extension_source, channel_source),
                _Channel(extension_destination, channel_destination),
            )
