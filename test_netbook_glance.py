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

    def test_battery_without_type_field(self):
        info = '  power supply: yes\n  battery\n    present: yes\n    state: discharging\n    time to empty: 1.1 hours\n    percentage: 47%\n'
        with patch.object(glance, 'command', side_effect=['/org/freedesktop/UPower/devices/battery_BAT0\n', info]):
            self.assertEqual(glance.battery(), (47, 'discharging', '1.1 hours'))

    def test_small_terminal_and_unknown_values(self):
        data = {'cpu': [('0', 20), ('1', None)], 'memory': None, 'swap': None,
                'battery': None, 'wifi': None, 'disk': None, 'refreshed': 0}
        lines = glance.lines_for(data, 30)
        text = [''.join(part for part, _ in line) for line in lines]
        self.assertTrue(any('unavailable' in line for line in text))
        self.assertTrue(any(line.strip() == '1' for line in text))

    def test_wide_columns_and_controls(self):
        data = {'cpu': [('0', 4), ('1', 12)], 'memory': 62, 'swap': 26,
                'battery': (38, 'discharging', '3 hours'), 'wifi': ('Home', 68),
                'disk': (73, 3.5 * 1024**3), 'refreshed': 0}
        text = [''.join(part for part, _ in line) for line in glance.lines_for(data, 80)]
        battery = next(line for line in text if line.startswith('Battery'))
        wifi = next(line for line in text if line.startswith('Wi-Fi'))
        cpu = next(line for line in text if line.startswith('CPU'))
        self.assertEqual(battery.index('['), wifi.index('['))
        self.assertEqual(battery.index('['), cpu.index('['))
        self.assertIn('Home', wifi)
        self.assertNotIn('r: refresh, q: quit', text)
        rows = glance.lines_for(data, 80)
        battery_spans = next(row for row in rows if row and row[0][0].startswith('Battery'))
        wifi_spans = next(row for row in rows if row and row[0][0].startswith('Wi-Fi'))
        self.assertTrue(any('discharging' in part and color == 2 for part, color in battery_spans))
        self.assertTrue(any('connected' in part and color == 1 for part, color in wifi_spans))
        self.assertEqual(glance.battery_status_color('discharging', 10), 3)
        self.assertEqual(glance.battery_status_color('charging', 10), 1)

    def test_disconnected_wifi_is_red(self):
        data = {'cpu': [], 'memory': None, 'swap': None, 'battery': None,
                'wifi': ('disconnected', None), 'disk': None, 'refreshed': 0}
        rows = glance.lines_for(data, 80)
        wifi = next(row for row in rows if row and row[0][0].startswith('Wi-Fi'))
        self.assertIn(('disconnected', 3), wifi)

    def test_priority_and_signal_bar(self):
        data = {'cpu': [('0', 20)], 'memory': 40, 'swap': 0,
                'battery': (10, 'discharging', '1 hour'), 'wifi': ('Home', 80),
                'disk': (75, 1024**3), 'refreshed': 0}
        lines = glance.lines_for(data, 35)
        text = [''.join(part for part, _ in line) for line in lines]
        self.assertLess(next(i for i, line in enumerate(text) if 'Battery' in line), next(i for i, line in enumerate(text) if 'Wi-Fi' in line))
        self.assertLess(next(i for i, line in enumerate(text) if 'Wi-Fi' in line), next(i for i, line in enumerate(text) if 'CPU' in line))
        self.assertTrue(any('[########--]' in line for line in text))
        self.assertEqual(glance.metric_color(10, True), 3)
        self.assertEqual(glance.metric_color(80, True), 1)
        self.assertEqual(glance.metric_color(90), 3)
        self.assertTrue(any('1.0 GiB free' in line for line in text))

    def test_refresh_age(self):
        self.assertEqual(glance.age_text(59), '59s')
        self.assertEqual(glance.age_text(61), '1m 01s')
        self.assertEqual(glance.age_text(3600), '1h 00m')


if __name__ == '__main__':
    unittest.main()
