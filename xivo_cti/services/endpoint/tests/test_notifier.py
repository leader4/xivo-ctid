# -*- coding: utf-8 -*-

# Copyright (C) 2014 Avencall
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

import unittest

from ..status_notifier import StatusNotifier
from ..status_notifier import EndpointStatusUpdateEvent
from xivo_cti.ctiserver import CTIServer
from mock import Mock
from mock import patch


@patch('xivo_cti.services.endpoint.status_notifier.config',
       {'uuid': 'xivo-uuid',
        'status_notifier': {
            'exchange_name': 'configured-status-exchange',
            'exchange_type': 'direct',
            'routing_keys': {
                'endpoint': 'configured-endpoint-status-routing'}}})
class TestStatusNotifier(unittest.TestCase):

    def setUp(self):
        self._bus_status_notifier = Mock()
        self._ctiserver = Mock(CTIServer)
        self._notifier = StatusNotifier(self._ctiserver,
                                        self._bus_status_notifier)

    def test_that_notify_calls_send_cti_event(self):
        phone_id = '42'
        new_status = 8

        self._notifier.notify(phone_id, new_status)

        self._ctiserver.send_cti_event.assert_called_once_with(
            {'class': 'getlist',
             'listname': 'phones',
             'function': 'updatestatus',
             'tipbxid': 'xivo',
             'tid': phone_id,
             'status': {'hintstatus': new_status},
            }
        )

    def test_that_notify_sends_endpoint_status_update_event_on_the_bus(self):
        phone_id = '42'
        new_status = 0

        self._notifier.notify(phone_id, new_status)

        expected_bus_msg = EndpointStatusUpdateEvent('xivo-uuid', phone_id, new_status)

        self._bus_status_notifier.publish_event.assert_called_once_with(
            'configured-status-exchange',
            'configured-endpoint-status-routing',
            expected_bus_msg,
        )
