import unittest
import test_tokenfrugal
class RepeatGuardTest(unittest.TestCase):
 def setUp(self):
  self.h=test_tokenfrugal.AgentTest();self.h.setUp()
 def tearDown(self):self.h.tearDown()
 def test_duplicate_read_is_short_note(self):
  a=self.h._agent([{'tool':'read_file','args':{'path':'inventory/total.py'}},{'tool':'read_file','args':{'path':'inventory/total.py'}}]);a.max_steps=2
  a.run('inspect')
  self.assertNotIn('Already inspected',a.transcript[0]['observation'])
  self.assertIn('Already inspected',a.transcript[1]['observation'])
 def test_write_invalidates_read_cache(self):
  path='inventory/total.py';fixed='def line_value(item):\n return item["price"] * item["qty"]\ndef total_value(items):\n return sum(line_value(i) for i in items)\n'
  a=self.h._agent([{'tool':'read_file','args':{'path':path}},{'tool':'write_file','args':{'path':path,'content':fixed}},{'tool':'read_file','args':{'path':path}}]);a.max_steps=3
  a.run('fix')
  self.assertNotIn('Already inspected',a.transcript[2]['observation'])
  self.assertIn('price',a.transcript[2]['observation'])
