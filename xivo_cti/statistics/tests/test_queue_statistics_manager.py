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

import unittest
import time
from xivo_cti.dao.queue_dao import QueueDAO
from xivo_cti.statistics import queue_statistics_manager
from xivo_cti.statistics.queue_statistics_manager import QueueStatisticsManager
from mock import Mock, patch
from xivo_cti.xivo_ami import AMIClass
from xivo_cti.model.queuestatistic import NO_VALUE


class TestQueueStatisticsManager(unittest.TestCase):

    def setUp(self):
        self.ami_class = Mock(AMIClass)
        self.queue_statistics_manager = QueueStatisticsManager(self.ami_class)

    @patch('xivo_dao.queue_statistic_dao.get_statistics')
    def test_getStatistics(self, mock_queue_statistic_dao):
        window = 3600
        xqos = 25
        dao_queue_statistic = Mock()
        dao_queue_statistic.received_call_count = 7
        dao_queue_statistic.answered_call_count = 12
        dao_queue_statistic.answered_call_in_qos_count = 0
        dao_queue_statistic.abandonned_call_count = 11
        dao_queue_statistic.received_and_done = 11
        dao_queue_statistic.max_hold_time = 120
        dao_queue_statistic.mean_hold_time = 15
        mock_queue_statistic_dao.return_value = dao_queue_statistic

        queue_statistics = self.queue_statistics_manager.get_statistics('3', xqos, window)

        self.assertEqual(queue_statistics.received_call_count, 7)
        self.assertEqual(queue_statistics.answered_call_count, 12)
        self.assertEqual(queue_statistics.abandonned_call_count, 11)
        self.assertEqual(queue_statistics.max_hold_time, 120)
        self.assertEqual(queue_statistics.mean_hold_time, 15)
        mock_queue_statistic_dao.assert_called_with('3', window, xqos)

    @patch('xivo_dao.queue_statistic_dao.get_statistics')
    def test_calculate_efficiency_round_down(self, mock_queue_statistic_dao):
        window = 3600
        xqos = 25
        dao_queue_statistic = Mock()
        dao_queue_statistic.received_call_count = 18
        dao_queue_statistic.answered_call_count = 3
        dao_queue_statistic.answered_call_in_qos_count = 0
        dao_queue_statistic.received_and_done = 11
        mock_queue_statistic_dao.return_value = dao_queue_statistic

        queue_statistics = self.queue_statistics_manager.get_statistics('3', xqos, window)

        self.assertEqual(queue_statistics.efficiency, 27)

    @patch('xivo_dao.queue_statistic_dao.get_statistics')
    def test_calculate_efficiency_round_up(self, mock_queue_statistic_dao):
        window = 3600
        xqos = 25
        dao_queue_statistic = Mock()
        dao_queue_statistic.received_call_count = 18
        dao_queue_statistic.answered_call_count = 12
        dao_queue_statistic.answered_call_in_qos_count = 0
        dao_queue_statistic.received_and_done = 14
        mock_queue_statistic_dao.return_value = dao_queue_statistic

        queue_statistics = self.queue_statistics_manager.get_statistics('3', xqos, window)

        self.assertEqual(queue_statistics.efficiency, 86)

    @patch('xivo_dao.queue_statistic_dao.get_statistics')
    def test_efficiency_no_call_received_and_done(self, mock_queue_statistic_dao):
        window = 3600
        xqos = 25
        dao_queue_statistic = Mock()
        dao_queue_statistic.received_call_count = 3
        dao_queue_statistic.answered_call_count = 0
        dao_queue_statistic.answered_call_in_qos_count = 0
        dao_queue_statistic.received_and_done = 0
        mock_queue_statistic_dao.return_value = dao_queue_statistic

        queue_statistics = self.queue_statistics_manager.get_statistics('3', xqos, window)

        self.assertEqual(queue_statistics.efficiency, NO_VALUE)

    @patch('xivo_dao.queue_statistic_dao.get_statistics')
    def test_qos_no_answered_calls_in_period(self, mock_queue_statistic_dao):
        window = 3600
        xqos = 25
        dao_queue_statistic = Mock()
        dao_queue_statistic.answered_call_count = 0
        mock_queue_statistic_dao.return_value = dao_queue_statistic

        queue_statistics = self.queue_statistics_manager.get_statistics('3', xqos, window)

        self.assertEqual(queue_statistics.qos, NO_VALUE)
        self.assertEqual(queue_statistics.efficiency, NO_VALUE)

    @patch('xivo_dao.queue_statistic_dao.get_statistics')
    def test_qos_round_down(self, mock_queue_statistic_dao):
        window = 3600
        xqos = 25
        dao_queue_statistic = Mock()
        dao_queue_statistic.received_call_count = 50
        dao_queue_statistic.answered_call_count = 11
        dao_queue_statistic.answered_call_in_qos_count = 3
        dao_queue_statistic.received_and_done = 11
        mock_queue_statistic_dao.return_value = dao_queue_statistic

        queue_statistics = self.queue_statistics_manager.get_statistics('3', xqos, window)

        self.assertEqual(queue_statistics.qos, 27)

    @patch('xivo_dao.queue_statistic_dao.get_statistics')
    def test_qos_round_up(self, mock_queue_statistic_dao):
        window = 3600
        xqos = 25
        dao_queue_statistic = Mock()
        dao_queue_statistic.received_call_count = 50
        dao_queue_statistic.answered_call_count = 14
        dao_queue_statistic.answered_call_in_qos_count = 12
        dao_queue_statistic.received_and_done = 14
        mock_queue_statistic_dao.return_value = dao_queue_statistic

        queue_statistics = self.queue_statistics_manager.get_statistics('3', xqos, window)

        self.assertEqual(queue_statistics.qos, 86)

    @patch('xivo_cti.ioc.context.context.get')
    def test_parse_queue_member_status(self, mock_context):
        self.queue_statistics_manager.get_queue_summary = Mock()
        mock_context.return_value = self.queue_statistics_manager
        queue_name = 'services'
        queuememberstatus_event = {'Event': 'QueueMemberStatus',
                                   'Queue': queue_name,
                                   'Interface': 'Agent/4523'}

        queue_statistics_manager.parse_queue_member_status(queuememberstatus_event)

        self.queue_statistics_manager.get_queue_summary.assert_called_once_with(queue_name)

    @patch('xivo_cti.dao.queue', spec=QueueDAO)
    def test_on_queue_member_event(self, mock_is_a_queue):
        queue_member = Mock()
        queue_member.queue_name = 'foobar'

        self.queue_statistics_manager._on_queue_member_event(queue_member)

        self.ami_class.queuesummary.assert_was_called_with(queue_member.queue_name)

    @patch('xivo_cti.dao.queue', spec=QueueDAO)
    def test_get_queue_summary(self, mock_queue_dao):
        queue_name = 'services'
        mock_queue_dao.get_queue_from_name.return_value = True

        self.queue_statistics_manager.get_queue_summary(queue_name)

        self.ami_class.queuesummary.assert_called_once_with(queue_name)

    def test_get_all_queue_summary(self):
        self.queue_statistics_manager.get_all_queue_summary()

        self.ami_class.queuesummary.assert_called_once_with()
