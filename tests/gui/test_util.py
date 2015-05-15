import time
from datetime import date, timedelta

import pytest
from unittest.mock import Mock, call


class TestSavableEntry:

    @pytest.fixture
    def entry(self, tk_main_win):
        from alho.gui import SavableEntry
        entry = SavableEntry(tk_main_win)
        entry.widget.pack()
        return entry

    @pytest.mark.parametrize('value', ['', 'Q', 'oh say, can you seeeeee'])
    def test_initial_value(self, value, tk_main_win):
        from alho.gui import SavableEntry
        entry = SavableEntry(tk_main_win, value)
        entry.widget.pack()
        assert entry.external_value == value
        assert entry.edited_value == value
        assert entry.entry.get() == value

    def test_revert_blank(self, entry):
        entry.editable = True
        entry.entry.insert(0, 'hey guys')
        entry.revert()
        assert entry.entry.get() == ''
        assert entry.edited_value == ''

    def test_edit_value(self, entry):
        entry.editable = True
        value = 'blah blah blah'
        entry.entry.insert(0, value)
        assert entry.edited_value == value
        assert 'alternate' in entry.entry.state()

    def test_editable(self, entry):
        entry.editable = False
        assert 'readonly' in entry.entry.state()
        old_value = entry.entry.get()
        entry.entry.insert(0, '?')
        assert entry.entry.get() == old_value
        entry.editable = True
        assert 'readonly' not in entry.entry.state()
        entry.entry.insert(0, '!')
        assert entry.entry.get() == '!' + old_value

    def test_set_edited_value(self, entry):
        entry.editable = True
        new_value = 'Something Something'
        entry.edited_value = new_value
        assert entry.edited_value == new_value
        assert entry.entry.get() == new_value
        assert 'alternate' in entry.entry.state()

    def test_revert_to_external(self, entry):
        entry.editable = True
        edit_value = '123456'
        new_value = 'oi tud dret'
        entry.edited_value = edit_value
        entry.external_value = new_value
        entry.revert()
        assert entry.edited_value == entry.external_value == new_value
        assert 'alternate' not in entry.entry.state()

    def test_save_to_external(self, entry):
        entry.editable = True
        edit_value = 'success!'
        entry.edited_value = edit_value
        entry.save()
        assert entry.edited_value == entry.external_value == edit_value
        assert 'alternate' not in entry.entry.state()

    def test_save_with_external_changed(self, entry):
        entry.editable = True
        edit_value = '123456'
        ext_value = 'oi tud dret'
        entry.edited_value = edit_value
        entry.external_value = ext_value
        entry.save()
        assert entry.edited_value == entry.external_value == edit_value
        assert 'alternate' not in entry.entry.state()

    @pytest.mark.parametrize('editable', [True, False])
    def test_set_external_value_after_change(self, entry, editable):
        entry.editable = True
        edit_value = 'different'
        ext_value = 'yet another'
        entry.edited_value = edit_value
        entry.editable = editable
        entry.external_value = ext_value
        assert entry.edited_value == edit_value == entry.entry.get()
        assert entry.external_value == ext_value
        assert 'alternate' in entry.entry.state()

    @pytest.mark.parametrize('editable', [True, False])
    def test_set_external_value_when_unchanged(self, entry, editable):
        entry.editable = editable
        new_value = 'Test'
        entry.external_value = new_value
        assert entry.edited_value == new_value == entry.entry.get()
        assert 'alternate' not in entry.entry.state()
        new_value2 = 'omg'
        entry.external_value = new_value2
        assert entry.edited_value == new_value2 == entry.entry.get()
        assert 'alternate' not in entry.entry.state()
        entry.external_value = ''
        assert entry.edited_value == '' == entry.entry.get()
        assert 'alternate' not in entry.entry.state()

    def test_save_normalize(self, entry):
        entry.normalize = Mock()
        entry.normalize.return_value = 'normal'
        entry.editable = True
        entry.edited_value = 'abnormal'
        entry.save()
        assert entry.external_value == 'normal'
        assert entry.edited_value == 'normal'
        assert call('abnormal') in entry.normalize.call_args_list

    def test_proposed_value(self, entry):
        entry.normalize = Mock()
        entry.normalize.return_value = 'normal'
        entry.editable = True
        entry.edited_value = 'abnormal'
        assert entry.edited_value == 'abnormal'
        assert entry.proposed_value == 'normal'
        assert call('abnormal') in entry.normalize.call_args_list

    def test_alternate_state_normalized_same(self, entry):
        entry.normalize = Mock()
        entry.normalize.return_value = 'normal'
        entry.external_value = 'normal'
        entry.editable = True
        entry.edited_value = 'abnormal'
        assert 'alternate' not in entry.entry.state()
        assert call('abnormal') in entry.normalize.call_args_list

    def test_alternate_state_normalized_different(self, entry):
        entry.normalize = Mock()
        entry.normalize.return_value = 'normal'
        entry.external_value = 'different'
        entry.editable = True
        entry.edited_value = 'abnormal'
        assert 'alternate' in entry.entry.state()
        assert call('abnormal') in entry.normalize.call_args_list

    @pytest.mark.parametrize('editable', [True, False])
    def test_set_external_value_when_normalized_unchanged(self,entry,editable):
        entry.normalize = lambda s: s.split('|')[0]
        entry.editable = editable
        entry.external_value = 'one'
        entry.edited_value = 'one|two'
        entry.external_value = 'three'
        assert entry.edited_value == 'three'

    def test_proposed_value_invalid(self, entry):
        entry.normalize = lambda s: exec('raise ValueError')
        new_value = 'hi'
        entry.edited_value = new_value
        assert entry.proposed_value == entry.edited_value

    def test_proposed_valid(self, entry):
        entry.edited_value = 'blah'
        assert entry.proposed_valid
        assert 'invalid' not in entry.entry.state()
        entry.normalize = lambda s: exec('raise ValueError')
        entry.edited_value = 'bleh'
        assert not entry.proposed_valid
        assert 'invalid' in entry.entry.state()


class TestDateChooser:

    DATES = [
        '1999-12-31',
        '2000-02-28',
        '2008-02-29',
        '1944-06-06',
        '2027-04-01',
        '2015-01-01',
    ]

    @pytest.fixture(autouse=True)
    def main_win(self, tk_main_win):
        self.win = tk_main_win

    def create_chooser(self, *args, **kwargs):
        from alho.gui import DateChooser
        return DateChooser(self.win, *args, **kwargs)

    def mkday(self, day):
        return date(*(int(n) for n in day.split('-')))

    def assert_day(self, chooser, day):
        assert chooser.day == day
        assert chooser.entry.edited_value == day.strftime('%Y-%m-%d')

    @pytest.mark.parametrize('day', DATES)
    def test_init_day(self, day):
        day = self.mkday(day)
        chooser = self.create_chooser(day=day)
        self.assert_day(chooser, day)

    @pytest.mark.parametrize('day', DATES)
    def test_init_day_default(self, day, fake_time):
        day = self.mkday(day)
        fake_time.value = time.mktime(day.timetuple())
        chooser = self.create_chooser()
        self.assert_day(chooser, day)

    @pytest.mark.parametrize('day', DATES)
    def test_set_day(self, day, fake_time):
        day = self.mkday(day)
        chooser = self.create_chooser()
        chooser.day = day
        self.assert_day(chooser, day)

    @pytest.mark.parametrize('day', DATES)
    def test_set_day_via_entry_save(self, day, fake_time):
        day = self.mkday(day)
        chooser = self.create_chooser()
        chooser.entry.edited_value = day.strftime('%Y-%m-%d')
        chooser.entry.save()
        self.assert_day(chooser, day)

    @pytest.mark.parametrize('day', DATES)
    def test_inc_button(self, day):
        day = self.mkday(day)
        chooser = self.create_chooser(day=day)
        day += timedelta(days=1)
        chooser.inc_button.invoke()
        self.assert_day(chooser, day)

    @pytest.mark.parametrize('day', DATES)
    def test_dec_button(self, day):
        day = self.mkday(day)
        chooser = self.create_chooser(day=day)
        day -= timedelta(days=1)
        chooser.dec_button.invoke()
        self.assert_day(chooser, day)

    @pytest.mark.parametrize('day', DATES)
    def test_today_button(self, day, fake_time):
        day = self.mkday(day)
        chooser = self.create_chooser(day=date(2000, 1, 1))
        fake_time.value = time.mktime(day.timetuple())
        chooser.today_button.invoke()
        self.assert_day(chooser, day)

    def test_editable(self):
        chooser = self.create_chooser()
        widgets = [chooser.inc_button, chooser.dec_button,
                   chooser.today_button]
        chooser.editable = True
        assert chooser.editable
        assert chooser.entry.editable
        for widget in widgets:
            assert 'disabled' not in widget.state()
        chooser.editable = False
        assert not chooser.editable
        assert not chooser.entry.editable
        for widget in widgets:
            assert 'disabled' in widget.state()

    def test_today_button_with_invalid_entry(self, fake_time):
        today = date(2015, 4, 21)
        fake_time.value = time.mktime(today.timetuple())
        chooser = self.create_chooser(day=date(2006, 2, 1))
        chooser.entry.edited_value = 'not a date'
        chooser.today_button.invoke()
        assert (chooser.entry.external_value ==
                today.strftime('%Y-%m-%d') ==
                chooser.entry.edited_value)

    def test_editable_with_invalid_entry(self, fake_time):
        chooser = self.create_chooser()
        chooser.editable = True
        chooser.entry.edited_value = 'supercalifragilisticexpialidocious'
        assert chooser.editable
        assert chooser.entry.editable
        for widget in [chooser.inc_button, chooser.dec_button]:
            assert 'disabled' in widget.state()
        assert 'disabled' not in chooser.today_button.state()
