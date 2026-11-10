"""Exercise shop navigation without calling Bale or touching real data."""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_tmp = tempfile.TemporaryDirectory()
os.chdir(_tmp.name)

import handlers_callback as callback
import handlers_message as message
import builders
import core


class ShopTests(unittest.TestCase):
    def setUp(self):
        self.db = {'42': {'name': 'Tester', 'coins': 1000, 'oil': 0, 'gems': 0}}
        self.patchers = [patch.object(module, 'db', self.db)
                         for module in (callback, message, builders, core)]
        for p in self.patchers:
            p.start()
            self.addCleanup(p.stop)

    def update(self, data, photo=False):
        msg = {'chat': {'id': 42}, 'message_id': 7}
        if photo:
            msg['photo'] = [{'file_id': 'old'}]
        return {'callback_query': {'id': 'cb', 'from': {'id': 42}, 'message': msg, 'data': data}}

    def test_shop_is_editable_text_even_if_photo_fails(self):
        update = {'message': {'chat': {'id': 42, 'type': 'private'}, 'from': {'id': 42, 'first_name': 'Tester'}, 'text': '🏪 فروشگاه'}}
        with patch.object(message, 'send_photo', return_value={'ok': False}) as photo, patch.object(message, 'send_message') as send:
            message.handle_message(update)
        photo.assert_called_once()
        self.assertIn('inline_keyboard', send.call_args.kwargs['reply_markup'])

    def test_shop_navigation_buttons_use_text_edit_and_acknowledge(self):
        for data in ('shop_missile', 'shop_defense', 'shop_talisman', 'shop_drone', 'help_shop', 'shop_back'):
            with self.subTest(data=data), patch.object(callback, 'edit_message') as edit, patch.object(callback, 'show_alert') as ack:
                callback.handle_callback(self.update(data))
                edit.assert_called_once()
                self.assertEqual(edit.call_args.args[1], 7)
                ack.assert_called_once_with('cb', '', False)

    def test_legacy_photo_opens_new_text_menu(self):
        with patch.object(callback, 'send_message', return_value={'ok': True, 'result': {'message_id': 8}}), patch.object(callback, 'edit_message') as edit, patch.object(callback, 'show_alert'):
            callback.handle_callback(self.update('shop_missile', photo=True))
            self.assertEqual(edit.call_args.args[1], 8)

    def test_back_sends_reply_keyboard_not_inline_edit(self):
        with patch.object(callback, 'send_message') as send, patch.object(callback, 'edit_message') as edit, patch.object(callback, 'show_alert'):
            callback.handle_callback(self.update('go_start'))
            send.assert_called_once()
            self.assertIn('keyboard', send.call_args.args[2])
            edit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
