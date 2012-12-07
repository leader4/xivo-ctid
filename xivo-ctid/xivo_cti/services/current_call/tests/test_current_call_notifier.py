# -*- coding: utf-8 -*-

import unittest

from mock import Mock
from mock import patch

from xivo_cti.services.current_call import notifier
from xivo_cti.services.current_call import formatter
from xivo_cti.interfaces.interface_cti import CTI
from xivo_cti.client_connection import ClientConnection


class TestCurrentCallNotifier(unittest.TestCase):

    def setUp(self):
        self.current_call_formatter = Mock(formatter.CurrentCallFormatter)
        self.notifier = notifier.CurrentCallNotifier(self.current_call_formatter)
        self.line_identity_1 = 'SCCP/1234'
        self.line_identity_2 = 'SIP/abkljhsdf'
        self.client_connection_1 = Mock(CTI)
        self.client_connection_2 = Mock(CTI)

    @patch('xivo_dao.userfeatures_dao.get_line_identity')
    def test_subscribe(self, mock_get_line_identity):
        user_id = 5
        mock_get_line_identity.return_value = self.line_identity_1

        self.client_connection_1.user_id.return_value = user_id

        self.notifier.subscriptions = {}
        self.notifier._report_current_call = Mock()

        self.notifier.subscribe(self.client_connection_1)

        expected_subscriptions = {self.line_identity_1.lower(): self.client_connection_1}
        subscriptions = self.notifier._subscriptions

        self.assertEqual(subscriptions, expected_subscriptions)
        self.notifier._report_current_call.assert_called_once_with(self.line_identity_1.lower())

    def test_publish_current_call(self):
        self.notifier._subscriptions[self.line_identity_1.lower()] = self.client_connection_1
        self.notifier._report_current_call = Mock()

        self.notifier.publish_current_call(self.line_identity_1)

        self.notifier._report_current_call.assert_called_once_with(self.line_identity_1.lower())

    def test_publish_current_call_no_subscriptions(self):
        self.notifier._report_current_call = Mock()

        self.notifier.publish_current_call(self.line_identity_1)

        self.assertEquals(self.notifier._report_current_call.call_count, 0)

    def test_report_current_call(self):
        formatted_current_call = {'class': 'current_call',
                                  'current_call': []}
        self.current_call_formatter.get_line_current_call.return_value = formatted_current_call

        self.notifier._subscriptions[self.line_identity_1.lower()] = self.client_connection_1
        self.notifier._subscriptions[self.line_identity_2.lower()] = self.client_connection_2

        self.notifier._report_current_call(self.line_identity_1)

        self.client_connection_1.send_message.assert_called_once_with(formatted_current_call)
        self.assertEqual(self.client_connection_2.call_count, 0)

    def test_report_current_call_connection_closed(self):
        formatted_current_call = {'class': 'current_call',
                                  'current_call': []}
        self.current_call_formatter.get_line_current_call.return_value = formatted_current_call

        self.notifier._subscriptions[self.line_identity_1.lower()] = self.client_connection_1
        self.notifier._subscriptions[self.line_identity_2.lower()] = self.client_connection_2

        self.client_connection_1.send_message.side_effect = ClientConnection.CloseException()

        self.notifier._report_current_call(self.line_identity_1)

        self.assertEqual(self.client_connection_2.call_count, 0)
        self.assertTrue(self.line_identity_1.lower() not in self.notifier._subscriptions, 'Subscriber not removed')
