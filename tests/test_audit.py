"""Offline regression harness: no live API calls or production data."""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_tmp = tempfile.TemporaryDirectory()
os.chdir(_tmp.name)

import handlers_payment as payment
import web_panel
import performance
from urllib.request import urlopen


class PaymentTests(unittest.TestCase):
    def setUp(self):
        self.db = {'42': {'coins': 0, 'name': 'test'}}
        self.patches = [patch.object(payment, 'db', self.db),
                        patch.object(payment, 'save_db_now'),
                        patch.object(payment, 'send_message'),
                        patch.object(payment, 'answer_pre_checkout_query')]
        self.mocks = [p.start() for p in self.patches]
        self.addCleanup(lambda: [p.stop() for p in reversed(self.patches)])

    def precheckout(self, payload, total, currency='IRR'):
        payment.handle_pre_checkout_query({'pre_checkout_query': {'id': 'q', 'from': {'id': 42}, 'invoice_payload': payload, 'total_amount': total, 'currency': currency}})
        return self.mocks[3].call_args.args[1]

    def test_valid_world_pass(self):
        self.assertTrue(self.precheckout('world_pass_42_123', payment.WORLD_PASS_PRICE_RIAL))

    def test_valid_item(self):
        pack = payment.ITEM_PACKS['coins']
        self.assertTrue(self.precheckout('item_coins_1_42_123', pack['price_per_unit'] * 10))

    def test_reject_wrong_currency(self):
        self.assertFalse(self.precheckout('world_pass_42_123', payment.WORLD_PASS_PRICE_RIAL, 'USD'))

    def test_reject_wrong_buyer(self):
        self.assertFalse(self.precheckout('world_pass_99_123', payment.WORLD_PASS_PRICE_RIAL))

    def test_reject_zero_quantity(self):
        self.assertFalse(self.precheckout('item_coins_0_42_123', 0))

    def test_item_duplicate_charge(self):
        pack = payment.ITEM_PACKS['coins']
        update = {'message': {'from': {'id': 42}, 'chat': {'id': 42}, 'successful_payment': {
            'invoice_payload': 'item_coins_1_42_123', 'total_amount': pack['price_per_unit'] * 10,
            'currency': 'IRR', 'telegram_payment_charge_id': 'charge-1'}}}
        payment.handle_successful_payment(update)
        payment.handle_successful_payment(update)
        self.assertEqual(self.db['42']['coins'], pack['reward_per_unit'])


class ProcessorTests(unittest.TestCase):
    def test_concurrent_unique_users(self):
        processor = performance.UpdateProcessor(max_workers=10)
        seen = []
        processor.set_handler(lambda update: seen.append(update['update_id']))
        try:
            for i in range(100):
                processor.submit({'update_id': i, 'message': {'from': {'id': 10000 + i}}})
            processor.executor.shutdown(wait=True)
            self.assertEqual(len(set(seen)), 100)
            self.assertEqual(processor.stats()['err'], 0)
        finally:
            processor.executor.shutdown(wait=True)

    def test_payment_bypasses_rate_limits(self):
        processor = performance.UpdateProcessor(max_workers=1)
        handler = unittest.mock.Mock()
        processor.set_handler(handler)
        try:
            with patch.object(performance.user_rate, 'allow', return_value=False), patch.object(performance.global_rate, 'allow', return_value=False):
                processor.submit({'message': {'from': {'id': 42}, 'successful_payment': {}}})
                processor.executor.shutdown(wait=True)
            handler.assert_called_once()
            self.assertEqual(processor.stats()['drop'], 0)
        finally:
            processor.executor.shutdown(wait=True)


class PanelTests(unittest.TestCase):
    def test_http(self):
        with patch.dict(os.environ, {'PORT': '0'}):
            server = web_panel.start_web_panel()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with urlopen(f'http://127.0.0.1:{server.server_port}/health', timeout=2) as response:
            self.assertEqual(response.read(), b'ok\n')


if __name__ == '__main__':
    unittest.main()
