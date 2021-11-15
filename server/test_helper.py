import unittest
import helper


class Test_TestHelper(unittest.TestCase):
    def test_flatten_json(self):
        original_json = {'sender': {'id': '4634820103204695'}, 'recipient': {'id': '103603665458708'},
                         'timestamp': 1636785150248, 'message': {'text': 'hi'}, 'page_id': '103603665458708',
                         'update_time': 1636785150626}
        expected_json = {'sender_id': '4634820103204695', 'recipient_id': '103603665458708', 'timestamp': 1636785150248,
                         'message_text': 'hi', 'page_id': '103603665458708', 'update_time': 1636785150626}
        self.assertEqual(helper.flatten_json(original_json), expected_json)

    def test_convert_epoch_milliseconds_to_datetime_string(self):
        epoch_timestamp = 1636985618000
        expected_date_str = '2021-11-15 09:13:38'
        self.assertEqual(helper.convert_epoch_milliseconds_to_datetime_string(epoch_timestamp), expected_date_str)

    def test_check_date_format(self):
        date_str = '2021-05-10'
        self.assertTrue(helper.check_date_format(date_str))

        date_str = '242345-05-10'
        self.assertFalse(helper.check_date_format(date_str))

    def test_get_todays_date_str(self):
        expected_date = '2021-11-15'
        self.assertEqual(helper.get_todays_date_str(), expected_date)