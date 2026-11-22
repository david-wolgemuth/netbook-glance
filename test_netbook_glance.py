import importlib.machinery
import importlib.util
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader('glance', './netbook-glance')
spec = importlib.util.spec_from_loader(loader.name, loader)
glance = importlib.util.module_from_spec(spec)
loader.exec_module(glance)


class CollectorTests(unittest.TestCase):
    def test_cpu_delta_and_new_core(self):
        self.assertEqual(glance.cpu_percent({'0': (100, 40)}, {'0': (200, 70), '1': (1, 1)}), [('0', 70), ('1', None)])
        self.assertIsNone(glance.cpu_percent({'0': (10, 5)}, {'0': (10, 5)})[0][1])

    def test_available_memory_and_no_swap(self):
        self.assertEqual(glance.memory_values('MemTotal: 100 kB\nMemAvailable: 60 kB\nSwapTotal: 0 kB\nSwapFree: 0 kB'), (40, None))
        self.assertEqual(glance.memory_values('MemTotal: 100 kB'), (None, None))

    def test_wifi_escaped_network_and_disconnected(self):
        with patch.object(glance, 'command', return_value='*:home\\:wifi:78\n'):
            self.assertEqual(glance.wifi(), ('home:wifi', 78))
        with patch.object(glance, 'command', return_value=''):
            self.assertEqual(glance.wifi(), ('disconnected', None))
        with patch.object(glance, 'command', return_value=None):
            self.assertIsNone(glance.wifi())

    def test_battery_skips_peripheral(self):
        outputs = ['/mouse_battery\n/laptop_battery\n',
                   '  type: battery\n  power supply: no\n',
                   '  type: battery\n  power supply: yes\n  percentage: 72%\n  state: discharging\n  time to empty: 3.2 hours\n']
        with patch.object(glance, 'command', side_effect=outputs):
            self.assertEqual(glance.battery(), (72, 'discharging', '3.2 hours'))

    def test_small_terminal_and_unknown_values(self):
        data = {'cpu': [('0', 20), ('1', None)], 'memory': None, 'swap': None,
                'battery': None, 'wifi': None, 'disk': None, 'refreshed': 0}
        lines = glance.lines_for(data, 30)
        self.assertTrue(any('unavailable' in line for line, _ in lines))
        self.assertTrue(any('1 [' in line for line, _ in lines))

    def test_refresh_age(self):
        self.assertEqual(glance.age_text(59), '59s')
        self.assertEqual(glance.age_text(61), '1m 01s')
        self.assertEqual(glance.age_text(3600), '1h 00m')


if __name__ == '__main__':
    unittest.main()
