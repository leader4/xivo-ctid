# -*- coding: utf-8 -*-

# Copyright (C) 2007-2014 Avencall
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

import time
import unittest

from hamcrest import assert_that
from hamcrest import equal_to
from hamcrest import only_contains
from mock import Mock
from mock import patch
from mock import sentinel

from xivo.asterisk.extension import Extension
from xivo_cti import dao
from xivo_cti.dao import channel_dao
from xivo_cti.dao import user_dao

from xivo_cti.exception import NoSuchCallException
from xivo_cti.exception import NoSuchLineException
from xivo_cti.interfaces.interface_cti import CTI
from xivo_cti.services.call.call import Call
from xivo_cti.services.call.manager import CallManager
from xivo_cti.services.call.storage import CallStorage
from xivo_cti.services.current_call import formatter
from xivo_cti.services.current_call import manager
from xivo_cti.services.current_call import notifier
from xivo_cti.services.current_call.manager import BRIDGE_TIME
from xivo_cti.services.current_call.manager import LINE_CHANNEL
from xivo_cti.services.current_call.manager import ON_HOLD
from xivo_cti.services.current_call.manager import PEER_CHANNEL
from xivo_cti.services.current_call.manager import TRANSFER_CHANNEL
from xivo_cti.services.device.manager import DeviceManager
from xivo_cti import xivo_ami


class _BaseTestCase(unittest.TestCase):

    def setUp(self):
        self.device_manager = Mock(DeviceManager)
        self.notifier = Mock(notifier.CurrentCallNotifier)
        self.formatter = Mock(formatter.CurrentCallFormatter)
        self.ami_class = Mock(xivo_ami.AMIClass)
        self.call_manager = Mock(CallManager)
        self.call_storage = Mock(CallStorage)

        self.manager = manager.CurrentCallManager(
            self.notifier,
            self.formatter,
            self.ami_class,
            self.device_manager,
            self.call_manager,
            self.call_storage,
        )

        self.line_1 = 'sip/tc8nb4'
        self.line_2 = 'sip/6s7foq'
        self.channel_1 = 'SIP/tc8nb4-00000004'
        self.channel_2 = 'SIP/6s7foq-00000005'


class TestCurrentCallManager(_BaseTestCase):

    @patch('time.time')
    def test_bridge_channels(self, mock_time):
        bridge_time = time.time()
        mock_time.return_value = bridge_time

        self.manager.bridge_channels(self.channel_1, self.channel_2)

        expected = {
            self.line_1: [
                {PEER_CHANNEL: self.channel_2,
                 LINE_CHANNEL: self.channel_1,
                 BRIDGE_TIME: bridge_time,
                 ON_HOLD: False}
            ],
            self.line_2: [
                {PEER_CHANNEL: self.channel_1,
                 LINE_CHANNEL: self.channel_2,
                 BRIDGE_TIME: bridge_time,
                 ON_HOLD: False}
            ],
        }

        self.assertEqual(self.manager._calls_per_line, expected)
        calls = self._get_notifier_calls()
        assert_that(calls, only_contains(self.line_1, self.line_2))

    @patch('time.time')
    def test_bridge_channels_transfer_answered(self, mock_time):
        bridge_time = time.time()
        mock_time.return_value = bridge_time

        transferer_channel = self.channel_1
        transferee_channel = 'Local/123@default-00000009;1'

        calls_per_line = {
            self.line_1: [
                {PEER_CHANNEL: self.channel_2,
                 LINE_CHANNEL: self.channel_1,
                 BRIDGE_TIME: bridge_time,
                 ON_HOLD: False,
                 TRANSFER_CHANNEL: transferee_channel}
            ],
        }
        self.manager._calls_per_line = calls_per_line

        self.manager.bridge_channels(transferer_channel, transferee_channel)

        self.notifier.attended_transfer_answered.assert_called_once_with(self.line_1)

    @patch('time.time')
    def test_bridge_channels_transfer_answered_reverse_order(self, mock_time):
        bridge_time = time.time()
        mock_time.return_value = bridge_time

        transferer_channel = self.channel_1
        transferee_channel = 'Local/123@default-00000009;1'

        calls_per_line = {
            self.line_1: [
                {PEER_CHANNEL: self.channel_2,
                 LINE_CHANNEL: self.channel_1,
                 BRIDGE_TIME: bridge_time,
                 ON_HOLD: False,
                 TRANSFER_CHANNEL: transferee_channel}
            ],
        }
        self.manager._calls_per_line = calls_per_line

        self.manager.bridge_channels(transferee_channel, transferer_channel)

        self.notifier.attended_transfer_answered.assert_called_once_with(self.line_1)

    @patch('time.time')
    def test_bridge_channels_transfer_answered_when_line_has_multiple_calls(self, mock_time):
        bridge_time = time.time()
        mock_time.return_value = bridge_time

        transferer_channel = self.channel_1
        transferee_channel = 'Local/123@default-00000009;1'

        calls_per_line = {
            self.line_1: [
                {PEER_CHANNEL: 'SIP/sdkfjh-00000000012',
                 LINE_CHANNEL: self.channel_1,
                 BRIDGE_TIME: bridge_time},
                {PEER_CHANNEL: self.channel_2,
                 LINE_CHANNEL: self.channel_1,
                 BRIDGE_TIME: bridge_time,
                 TRANSFER_CHANNEL: transferee_channel}
            ],
        }
        self.manager._calls_per_line = calls_per_line

        self.manager.bridge_channels(transferer_channel, transferee_channel)

        self.notifier.attended_transfer_answered.assert_called_once_with(self.line_1)

    def test_masquerade_with_the_same_local_channel(self):
        line_1 = u'local/6000@pomme;1'
        line_2 = u'local/6000@pomme;2'
        local_line_1 = u'local/6000@pomme;1'
        local_line_2 = u'local/6000@pomme;2'

        line_1_channel = u'Local/6000@pomme-00000023;1'
        line_2_channel = u'Local/6000@pomme-00000022;1'
        local_line_1_channel = u'Local/6000@pomme-00000023;1'

        self.manager._calls_per_line = {
            local_line_1: [{BRIDGE_TIME: 1358197027.3219039,
                            PEER_CHANNEL: line_2_channel,
                            LINE_CHANNEL: local_line_1_channel,
                            ON_HOLD: False}],
            local_line_2: [{BRIDGE_TIME: 1358197027.242239,
                            PEER_CHANNEL: line_1_channel,
                            LINE_CHANNEL: u'Local/id-292@agentcallback-00000013;2',
                            ON_HOLD: False}],
            line_1: [{BRIDGE_TIME: 1358197027.2422481,
                      PEER_CHANNEL: u'Local/id-292@agentcallback-00000013;2',
                      LINE_CHANNEL: line_1_channel,
                      ON_HOLD: False}],
            line_2: [{BRIDGE_TIME: 1358197027.3218949,
                      PEER_CHANNEL: local_line_1_channel,
                      LINE_CHANNEL: line_2_channel,
                      ON_HOLD: False}]}

        self.manager.masquerade(local_line_1_channel, local_line_1_channel)

        # It is expected not to freeze here
        # TODO find something better to expect from this kind of scenario

    @patch('time.time')
    def test_bridge_channels_transfer_answered_not_tracked(self, mock_time):
        bridge_time = time.time()
        mock_time.return_value = bridge_time

        transferer_channel = self.channel_1
        transferee_channel = 'Local/123@default-00000009;1'

        calls_per_line = {
            self.line_1: [
                {PEER_CHANNEL: self.channel_2,
                 LINE_CHANNEL: self.channel_1,
                 BRIDGE_TIME: bridge_time,
                 ON_HOLD: False}
            ],
        }
        self.manager._calls_per_line = calls_per_line

        self.manager.bridge_channels(transferer_channel, transferee_channel)

        call_count = self.notifier.attended_transfer_answered.call_count
        self.assertEqual(call_count, 0)

    def test_masquerade_agent_call(self):
        line_1 = u'sip/6s7foq'
        line_2 = u'sip/pcm_dev'
        local_line_1 = u'local/id-292@agentcallback;1'
        local_line_2 = u'local/id-292@agentcallback;2'

        line_1_channel = u'SIP/6s7foq-00000023'
        line_2_channel = u'SIP/pcm_dev-00000022'
        local_line_1_channel = u'Local/id-292@agentcallback-00000013;1'

        self.manager._calls_per_line = {
            local_line_1: [{BRIDGE_TIME: 1358197027.3219039,
                            PEER_CHANNEL: line_2_channel,
                            LINE_CHANNEL: local_line_1_channel,
                            ON_HOLD: False}],
            local_line_2: [{BRIDGE_TIME: 1358197027.242239,
                            PEER_CHANNEL: line_1_channel,
                            LINE_CHANNEL: u'Local/id-292@agentcallback-00000013;2',
                            ON_HOLD: False}],
            line_1: [{BRIDGE_TIME: 1358197027.2422481,
                      PEER_CHANNEL: u'Local/id-292@agentcallback-00000013;2',
                      LINE_CHANNEL: line_1_channel,
                      ON_HOLD: False}],
            line_2: [{BRIDGE_TIME: 1358197027.3218949,
                      PEER_CHANNEL: local_line_1_channel,
                      LINE_CHANNEL: line_2_channel,
                      ON_HOLD: False}]}

        self.manager.masquerade(local_line_1_channel, line_1_channel)

        expected = {
            line_1: [{BRIDGE_TIME: 1358197027.2422481,
                      PEER_CHANNEL: line_2_channel,
                      LINE_CHANNEL: line_1_channel,
                      ON_HOLD: False}],
            line_2: [{BRIDGE_TIME: 1358197027.3218949,
                      PEER_CHANNEL: line_1_channel,
                      LINE_CHANNEL: u'SIP/pcm_dev-00000022',
                      ON_HOLD: False}]
        }

        self.assertEqual(self.manager._calls_per_line, expected)

    def test_masquerade_bridged_channels(self):
        bridged_line_1_channel = u'bridge/SIP/6s7foq-00000023'
        line_1_channel = u'SIP/6s7foq-00000023'

        self.manager.masquerade(bridged_line_1_channel, line_1_channel)

    def test_bridge_channels_on_hold(self):
        bridge_time = 123456.44

        self.manager._calls_per_line = {
            self.line_1: [
                {PEER_CHANNEL: self.channel_2,
                 BRIDGE_TIME: bridge_time,
                 ON_HOLD: True}
            ],
            self.line_2: [
                {PEER_CHANNEL: self.channel_1,
                 BRIDGE_TIME: bridge_time,
                 ON_HOLD: False}
            ],
        }

        self.manager.bridge_channels(self.channel_1, self.channel_2)

        expected = {
            self.line_1: [
                {PEER_CHANNEL: self.channel_2,
                 BRIDGE_TIME: bridge_time,
                 ON_HOLD: True}
            ],
            self.line_2: [
                {PEER_CHANNEL: self.channel_1,
                 BRIDGE_TIME: bridge_time,
                 ON_HOLD: False}
            ],
        }

        self.assertEqual(self.manager._calls_per_line, expected)
        self.assertEqual(self.notifier.publish_current_call.call_count, 0)

    def test_end_call(self):
        bridge_time = 123456.44

        self.manager._calls_per_line = {
            self.line_1: [
                {PEER_CHANNEL: 'SIP/mytrunk-12345',
                 LINE_CHANNEL: 'SIP/tc8nb4-000002',
                 BRIDGE_TIME: bridge_time,
                 ON_HOLD: True},
                {PEER_CHANNEL: self.channel_2,
                 LINE_CHANNEL: self.channel_1,
                 BRIDGE_TIME: bridge_time,
                 ON_HOLD: False},
            ],
            self.line_2: [
                {PEER_CHANNEL: self.channel_1,
                 LINE_CHANNEL: self.channel_2,
                 BRIDGE_TIME: bridge_time,
                 ON_HOLD: False}
            ],
        }

        self.manager.end_call(self.channel_1)

        expected = {
            self.line_1: [
                {PEER_CHANNEL: 'SIP/mytrunk-12345',
                 LINE_CHANNEL: 'SIP/tc8nb4-000002',
                 BRIDGE_TIME: bridge_time,
                 ON_HOLD: True}
            ],
        }

        self.assertEqual(self.manager._calls_per_line, expected)
        calls = self._get_notifier_calls()
        assert_that(calls, only_contains(self.line_1, self.line_2))

    def test_remove_transfer_channel(self):
        line = u'SIP/6s7foq'.lower()
        channel = u'%s-0000007b' % line
        transfer_channel = u'Local/1003@pcm-dev-00000021;1'

        self.manager._calls_per_line = {
            line: [
                {PEER_CHANNEL: self.channel_2,
                 LINE_CHANNEL: channel,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False,
                 TRANSFER_CHANNEL: transfer_channel}
            ],
        }
        expected_calls_per_line = {
            line: [
                {PEER_CHANNEL: self.channel_2,
                 LINE_CHANNEL: channel,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
        }

        self.manager.remove_transfer_channel(transfer_channel)
        calls_per_line = self.manager._calls_per_line

        self.assertEqual(expected_calls_per_line, calls_per_line)
        self.notifier.publish_current_call.assert_called_once_with(line)

    def test_remove_transfer_channel_not_tracked(self):
        line = u'SIP/6s7foq'.lower()
        channel = u'%s-0000007b' % line
        transfer_channel = u'Local/1003@pcm-dev-00000021;1'

        self.manager._calls_per_line = {
            line: [
                {PEER_CHANNEL: self.channel_2,
                 LINE_CHANNEL: channel,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
        }

        self.manager.remove_transfer_channel(transfer_channel)

    def test_hold_channel(self):
        self.manager._calls_per_line = {
            self.line_1: [
                {PEER_CHANNEL: self.channel_2,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
            self.line_2: [
                {PEER_CHANNEL: self.channel_1,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
        }

        self.manager.hold_channel(self.channel_2)

        expected = {
            self.line_1: [
                {PEER_CHANNEL: self.channel_2,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: True}
            ],
            self.line_2: [
                {PEER_CHANNEL: self.channel_1,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
        }

        self.assertEqual(self.manager._calls_per_line, expected)
        self.notifier.publish_current_call.assert_called_once_with(self.line_1)

    def test_hold_channel_no_error_after_restart(self):
        self.manager.hold_channel(self.channel_2)

    def test_unhold_channel(self):
        self.manager._calls_per_line = {
            self.line_1: [
                {PEER_CHANNEL: self.channel_2,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: True}
            ],
            self.line_2: [
                {PEER_CHANNEL: self.channel_1,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
        }

        self.manager.unhold_channel(self.channel_2)

        expected = {
            self.line_1: [
                {PEER_CHANNEL: self.channel_2,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
            self.line_2: [
                {PEER_CHANNEL: self.channel_1,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
        }

        self.assertEqual(self.manager._calls_per_line, expected)
        self.notifier.publish_current_call.assert_called_once_with(self.line_1)

    def test_unhold_channel_no_error_after_restart(self):
        self.manager.unhold_channel(self.channel_2)

    def test_get_line_calls(self):
        self.manager._calls_per_line = {
            self.line_1: [
                {PEER_CHANNEL: self.channel_2,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: True}
            ],
            self.line_2: [
                {PEER_CHANNEL: self.channel_1,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
        }

        calls = self.manager.get_line_calls(self.line_1)

        self.assertEquals(calls, self.manager._calls_per_line[self.line_1])

    def test_get_line_calls_no_line(self):
        channel_1 = 'SIP/tc8nb4-00000004'
        channel_2 = 'SIP/6s7foq-00000005'
        self.manager._calls_per_line = {
            self.line_1: [
                {PEER_CHANNEL: channel_2,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: True}
            ],
            self.line_2: [
                {PEER_CHANNEL: channel_1,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
        }

        calls = self.manager.get_line_calls('SCCP/654')

        self.assertEquals(calls, [])

    @patch('xivo_dao.user_line_dao.get_line_identity_by_user_id')
    def test_complete_transfer(self, mock_get_line_identity):
        user_id = 5
        self.manager._calls_per_line = {
            self.line_1: [
                {PEER_CHANNEL: self.channel_2,
                 LINE_CHANNEL: self.channel_1,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
            self.line_2: [
                {PEER_CHANNEL: self.channel_1,
                 LINE_CHANNEL: self.channel_2,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
        }
        mock_get_line_identity.return_value = self.line_1

        self.manager.complete_transfer(user_id)

        self.manager.ami.hangup.assert_called_once_with(self.channel_1)

    @patch('xivo_dao.user_line_dao.get_line_identity_by_user_id')
    def test_complete_transfer_no_transfer_target_channel(self, mock_get_line_identity):
        user_id = 5
        self.manager._calls_per_line = {
            self.line_1: [
                {PEER_CHANNEL: self.channel_2,
                 LINE_CHANNEL: self.channel_1,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
            self.line_2: [
                {PEER_CHANNEL: self.channel_1,
                 LINE_CHANNEL: self.channel_2,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
        }
        mock_get_line_identity.return_value = self.line_1

        self.manager.complete_transfer(user_id)

        # No exception

    @patch('xivo_dao.user_line_dao.get_line_identity_by_user_id')
    def test_complete_transfer_no_call(self, mock_get_line_identity):
        user_id = 5
        self.manager._calls_per_line = {
            self.line_1: [
            ],
        }
        mock_get_line_identity.return_value = self.line_1

        self.manager.complete_transfer(user_id)

    @patch('xivo_dao.user_line_dao.get_line_identity_by_user_id')
    def test_attended_transfer(self, mock_get_line_identity):
        user_id = 5
        number = '1234'
        line_context = 'ctx'
        self.manager._calls_per_line = {
            self.line_1: [
                {PEER_CHANNEL: self.channel_2,
                 LINE_CHANNEL: self.channel_1,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
            self.line_2: [
                {PEER_CHANNEL: self.channel_1,
                 LINE_CHANNEL: self.channel_2,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
        }
        mock_get_line_identity.return_value = self.line_1
        dao.user = Mock(user_dao.UserDAO)
        dao.user.get_context.return_value = line_context

        self.manager.attended_transfer(user_id, number)

        self.manager.ami.atxfer.assert_called_once_with(
            self.channel_1, number, line_context)

    @patch('xivo_dao.user_line_dao.get_line_identity_by_user_id')
    def test_direct_transfer(self, mock_get_line_identity):
        user_id = 5
        number = '9876'
        line_context = 'mycontext'
        self.manager._calls_per_line = {
            self.line_1: [
                {PEER_CHANNEL: self.channel_2,
                 LINE_CHANNEL: self.channel_1,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
            self.line_2: [
                {PEER_CHANNEL: self.channel_1,
                 LINE_CHANNEL: self.channel_2,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
        }
        mock_get_line_identity.return_value = self.line_1
        dao.user = Mock(user_dao.UserDAO)
        dao.user.get_context.return_value = line_context

        self.manager.direct_transfer(user_id, number)

        self.manager.ami.transfer.assert_called_once_with(
            self.channel_2, number, line_context)

    @patch('xivo_dao.user_line_dao.get_line_identity_by_user_id')
    @patch('xivo_cti.dao.queue')
    def test_switchboard_hold(self, mock_queue_dao, mock_get_line_identity):
        mock_queue_dao.get_number_context_from_name.return_value = '3006', 'ctx'
        queue_name = 'queue_on_hold'
        user_id = 7
        mock_get_line_identity.return_value = self.line_2

        self.manager._calls_per_line = {
            self.line_1: [
                {PEER_CHANNEL: self.channel_2,
                 LINE_CHANNEL: self.channel_1,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
            self.line_2: [
                {PEER_CHANNEL: self.channel_1,
                 LINE_CHANNEL: self.channel_2,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
        }

        self.manager.switchboard_hold(user_id, queue_name)

        self.manager.ami.transfer.assert_called_once_with(self.channel_1, '3006', 'ctx')

    @patch('xivo_dao.user_line_dao.get_line_identity_by_user_id', Mock())
    @patch('xivo_cti.dao.user.get_line')
    def test_switchboard_retrieve_waiting_call_when_not_talking_then_retrieve_the_call(self, mock_get_line):
        unique_id = '1234567.44'
        user_id = 5
        line_identity = 'sccp/12345'
        line_cid_name = 'John'
        line_cid_number = '123'
        line_callerid = '"%s" <%s>' % (line_cid_name, line_cid_number)
        line = {
            'identity': line_identity,
            'callerid': line_callerid,
        }
        ringing_channel = 'sccp/12345-0000001'
        channel_to_intercept = 'SIP/acbdf-348734'
        cid_name, cid_number = 'Alice', '5565'
        conn = Mock(CTI)

        dao.channel = Mock(channel_dao.ChannelDAO)
        dao.channel.get_channel_from_unique_id.return_value = channel_to_intercept
        dao.channel.get_caller_id_name_number.return_value = cid_name, cid_number
        dao.channel.channels_from_identity.return_value = [ringing_channel]
        mock_get_line.return_value = line

        self.manager.switchboard_retrieve_waiting_call(user_id, unique_id, conn)

        self.manager.ami.hangup.assert_called_once_with(ringing_channel)
        self.manager.ami.switchboard_retrieve.assert_called_once_with(
            line_identity, channel_to_intercept, cid_name, cid_number, line_cid_name, line_cid_number)
        self.call_manager.answer_next_ringing_call.assert_called_once_with(conn, line_identity)

    @patch('xivo_dao.user_line_dao.get_line_identity_by_user_id')
    def test_switchboard_retrieve_waiting_call_when_talking_then_do_nothing(self, mock_get_line_identity):
        unique_id = '1234567.44'
        user_id = 5
        user_line = 'sccp/12345'
        talking_channel = 'sccp/12345-0000001'
        channel_to_intercept = 'SIP/acbdf-348734'
        cid_name, cid_number = 'Alice', '5565'
        client_connection = Mock(CTI)
        self.manager._calls_per_line = {
            user_line: [
                {PEER_CHANNEL: self.channel_2,
                 LINE_CHANNEL: talking_channel,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
        }

        dao.channel = Mock(channel_dao.ChannelDAO)
        dao.channel.get_channel_from_unique_id.return_value = channel_to_intercept
        dao.channel.get_caller_id_name_number.return_value = cid_name, cid_number
        dao.channel.channels_from_identity.return_value = [talking_channel]
        mock_get_line_identity.return_value = user_line

        self.manager.switchboard_retrieve_waiting_call(user_id, unique_id, client_connection)

        assert_that(self.ami_class.hangup.call_count, equal_to(0))
        assert_that(self.ami_class.switchboard_retrieve.call_count, equal_to(0))

    @patch('xivo_dao.user_line_dao.get_line_identity_by_user_id')
    def test_switchboard_retrieve_waiting_call_when_no_channel_then_return(self, mock_get_line_identity):
        unique_id = '1234567.44'
        user_id = 5
        user_line = 'sccp/12345'
        channel_to_intercept = 'SIP/acbdf-348734'

        dao.channel = Mock(channel_dao.ChannelDAO)
        dao.channel.get_channel_from_unique_id.side_effect = LookupError()
        mock_get_line_identity.return_value = user_line
        client_connection = Mock(CTI)

        self.manager.switchboard_retrieve_waiting_call(user_id, unique_id, client_connection)

        call_count_retrieve = self.manager.ami.switchboard_retrieve.call_count
        self.assertEqual(call_count_retrieve, 0)

    def test_set_transfer_channel(self):
        line = u'SIP/6s7foq'.lower()
        channel = u'%s-0000007b' % line
        transfer_channel = u'Local/1003@pcm-dev-00000021;1'

        self.manager._calls_per_line = {
            line: [
                {PEER_CHANNEL: self.channel_2,
                 LINE_CHANNEL: channel,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
        }

        self.manager.set_transfer_channel(channel, transfer_channel)

        calls = self.manager._calls_per_line[line]
        call = [c for c in calls if c[LINE_CHANNEL] == channel][0]

        self.assertEqual(call[TRANSFER_CHANNEL], transfer_channel)

    def test_set_transfer_channel_not_tracked(self):
        line = u'SIP/6s7foq'.lower()
        channel = u'%s-0000007b' % line
        transfer_channel = u'Local/1003@pcm-dev-00000021;1'

        self.manager.set_transfer_channel(channel, transfer_channel)

    @patch('xivo_dao.user_line_dao.get_line_identity_by_user_id')
    def test_cancel_transfer(self, mock_get_line_identity):
        local_transfer_channel = u'Local/1003@pcm-dev-00000032;'
        transfer_channel = local_transfer_channel + u'1'
        transfered_channel = local_transfer_channel + u'2'
        user_id = 5
        self.manager._calls_per_line = {
            self.line_1: [
                {PEER_CHANNEL: self.channel_2,
                 LINE_CHANNEL: self.channel_1,
                 BRIDGE_TIME: 1234,
                 TRANSFER_CHANNEL: transfer_channel,
                 ON_HOLD: False}
            ],
            self.line_2: [
                {PEER_CHANNEL: self.channel_1,
                 LINE_CHANNEL: self.channel_2,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
        }
        mock_get_line_identity.return_value = self.line_1

        self.manager.cancel_transfer(user_id)

        self.manager.ami.hangup.assert_called_once_with(transfered_channel)

    @patch('xivo_dao.user_line_dao.get_line_identity_by_user_id')
    def test_cancel_transfer_wrong_number(self, mock_get_line_identity):
        user_id = 5
        self.manager._calls_per_line = {
            self.line_1: [
                {PEER_CHANNEL: self.channel_2,
                 LINE_CHANNEL: self.channel_1,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
            self.line_2: [
                {PEER_CHANNEL: self.channel_1,
                 LINE_CHANNEL: self.channel_2,
                 BRIDGE_TIME: 1234,
                 ON_HOLD: False}
            ],
        }
        mock_get_line_identity.return_value = self.line_1

        self.manager.cancel_transfer(user_id)

        # Only test that it does not crash at the moment

    def test_local_channel_peer(self):
        local_channel = u'Local/1003@pcm-dev-00000032;'
        mine = local_channel + u'1'
        peer = local_channel + u'2'

        result = self.manager._local_channel_peer(mine)

        self.assertEqual(result, peer)

        result = self.manager._local_channel_peer(peer)

        self.assertEqual(result, mine)

    def test_get_cid_name_and_number(self):
        line = {
            'callerid': '"John" <123>',
        }

        cid_name, cid_num = self.manager._get_cid_name_and_number_from_line(line)

        self.assertEqual(cid_name, 'John')
        self.assertEqual(cid_num, '123')

    def test_get_cid_name_and_number_on_error(self):
        line = {
            'callerid': 'foobar',
        }

        cid_name, cid_num = self.manager._get_cid_name_and_number_from_line(line)

        self.assertEqual(cid_name, '')
        self.assertEqual(cid_num, '')

    def _get_notifier_calls(self):
        return [call[0][0] for call in self.notifier.publish_current_call.call_args_list]


class TestHangup(_BaseTestCase):

    def test_with_no_active_call_does_not_crash(self):
        self.manager._get_active_call = Mock(side_effect=NoSuchCallException('some error'))

        self.manager.hangup(sentinel.user_id)

    def test_when_everything_works(self):
        self.manager._get_active_call = Mock(return_value=sentinel.call)

        self.manager.hangup(sentinel.user_id)

        self.call_manager.hangup.assert_called_once_with(sentinel.call)


class TestGetActiveCall(_BaseTestCase):

    @patch('xivo_cti.dao.user.get_line', Mock(side_effect=NoSuchLineException()))
    def test_no_line(self):
        self.assertRaises(NoSuchCallException, self.manager._get_active_call, sentinel.userid)

    @patch('xivo_cti.dao.user.get_line', Mock(return_value={'context': sentinel.context}))
    def test_line_as_no_number(self):
        self.assertRaises(NoSuchCallException, self.manager._get_active_call, sentinel.user_id)

    @patch('xivo_cti.dao.user.get_line', Mock(return_value={'number': sentinel.number}))
    def test_line_as_no_context(self):
        self.assertRaises(NoSuchCallException, self.manager._get_active_call, sentinel.user_id)

    @patch('xivo_cti.dao.user')
    def test_when_everything_works(self, mock_user_dao):
        active_call = Mock(Call)
        mock_user_dao.get_line.return_value = {'number': sentinel.number,
                                               'context': sentinel.context}
        self.call_storage.find_all_calls_for_extension.return_value = [active_call]

        self.manager.hangup(sentinel.userid)

        mock_user_dao.get_line.assert_called_once_with(sentinel.userid)
        self.call_manager.hangup.assert_called_once_with(active_call)
        self.call_storage.find_all_calls_for_extension.assert_called_once_with(
            Extension(sentinel.number, sentinel.context, True)
        )

    @patch('xivo_cti.dao.user')
    def test_when_there_is_no_call_on_the_extension(self, mock_user_dao):
        mock_user_dao.get_line.return_value = {'number': sentinel.number,
                                               'context': sentinel.context}
        self.call_storage.find_all_calls_for_extension.return_value = []

        self.manager.hangup(sentinel.userid)

        mock_user_dao.get_line.assert_called_once_with(sentinel.userid)
        assert_that(self.call_manager.hangup.call_count, equal_to(0))
        self.call_storage.find_all_calls_for_extension.assert_called_once_with(
            Extension(sentinel.number, sentinel.context, True)
        )
