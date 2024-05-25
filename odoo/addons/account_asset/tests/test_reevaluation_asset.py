# -*- coding: utf-8 -*-


from freezegun import freeze_time
from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo import fields


@freeze_time('2022-06-30')
@tagged('post_install', '-at_install')
class TestAccountAssetReevaluation(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref)
        cls.account_depreciation_expense = cls.company_data['default_account_assets'].copy()

    @classmethod
    def create_asset(cls, value, periodicity, periods, import_depreciation=0, acquisition_date="2022-02-01", prorata='none', **kwargs):
        return cls.env['account.asset'].create({
            'name': 'nice asset',
            'account_asset_id': cls.company_data['default_account_assets'].id,
            'account_depreciation_id': cls.account_depreciation_expense.id,
            'account_depreciation_expense_id': cls.company_data['default_account_expense'].id,
            'journal_id': cls.company_data['default_journal_misc'].id,
            'acquisition_date': acquisition_date,
            'prorata_computation_type': prorata,
            'original_value': value,
            'salvage_value': 0,
            'method_number': periods,
            'method_period': '12' if periodicity == "yearly" else '1',
            'method': "linear",
            'already_depreciated_amount_import': import_depreciation,
            **kwargs,
        })

    @classmethod
    def _get_depreciation_move_values(cls, date, depreciation_value, remaining_value, depreciated_value, state):
        return {
            'date': fields.Date.from_string(date),
            'depreciation_value': depreciation_value,
            'asset_remaining_value': remaining_value,
            'asset_depreciated_value': depreciated_value,
            'state': state,
        }

    def test_linear_start_beginning_month_reevaluation_beginning_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-01", prorata="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-01"),
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=600, remaining_value=6600, depreciated_value=600, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6000, depreciated_value=1200, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5400, depreciated_value=1800, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=4800, depreciated_value=2400, state='posted'),
            # 20 because we have 1 * 600 / 30 (1 day of a month of 30 days, with 600 per month)
            self._get_depreciation_move_values(date='2022-06-01', depreciation_value=20, remaining_value=4780, depreciated_value=2420, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=580, remaining_value=4200, depreciated_value=3000, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=3600, depreciated_value=3600, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3000, depreciated_value=4200, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2400, depreciated_value=4800, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=1800, depreciated_value=5400, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1200, depreciated_value=6000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=600, depreciated_value=6600, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=0, depreciated_value=7200, state='draft'),
        ])

    def test_linear_start_beginning_month_reevaluation_middle_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-01", prorata="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-15")
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=600, remaining_value=6600, depreciated_value=600, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6000, depreciated_value=1200, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5400, depreciated_value=1800, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=4800, depreciated_value=2400, state='posted'),
            # 300 because we have 15 * 600 / 30 (15 days of a month of 30 days, with 600 per month)
            self._get_depreciation_move_values(date='2022-06-15', depreciation_value=300, remaining_value=4500, depreciated_value=2700, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=300, remaining_value=4200, depreciated_value=3000, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=3600, depreciated_value=3600, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3000, depreciated_value=4200, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2400, depreciated_value=4800, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=1800, depreciated_value=5400, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1200, depreciated_value=6000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=600, depreciated_value=6600, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=0, depreciated_value=7200, state='draft'),
        ])

    def test_linear_start_beginning_month_reevaluation_end_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-01", prorata="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-30")
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=600, remaining_value=6600, depreciated_value=600, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6000, depreciated_value=1200, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5400, depreciated_value=1800, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=4800, depreciated_value=2400, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=600, remaining_value=4200, depreciated_value=3000, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=3600, depreciated_value=3600, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3000, depreciated_value=4200, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2400, depreciated_value=4800, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=1800, depreciated_value=5400, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1200, depreciated_value=6000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=600, depreciated_value=6600, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=0, depreciated_value=7200, state='draft'),
        ])

    def test_linear_start_middle_month_reevaluation_beginning_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-15", prorata="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-01"),
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=300, remaining_value=6900, depreciated_value=300, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6300, depreciated_value=900, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5700, depreciated_value=1500, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=5100, depreciated_value=2100, state='posted'),
            # 20 because we have 1 * 600 / 30 (1 day of a month of 30 days, with 600 per month)
            self._get_depreciation_move_values(date='2022-06-01', depreciation_value=20, remaining_value=5080, depreciated_value=2120, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=580, remaining_value=4500, depreciated_value=2700, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=3900, depreciated_value=3300, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3300, depreciated_value=3900, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2700, depreciated_value=4500, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=2100, depreciated_value=5100, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1500, depreciated_value=5700, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=900, depreciated_value=6300, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=300, depreciated_value=6900, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=300, remaining_value=0, depreciated_value=7200, state='draft'),
        ])

    def test_linear_start_middle_month_reevaluation_middle_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-15", prorata="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-15"),
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=300, remaining_value=6900, depreciated_value=300, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6300, depreciated_value=900, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5700, depreciated_value=1500, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=5100, depreciated_value=2100, state='posted'),
            # 300 because we have 15 * 600 / 30 (15 days of a month of 30 days, with 600 per month)
            self._get_depreciation_move_values(date='2022-06-15', depreciation_value=300, remaining_value=4800, depreciated_value=2400, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=300, remaining_value=4500, depreciated_value=2700, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=3900, depreciated_value=3300, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3300, depreciated_value=3900, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2700, depreciated_value=4500, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=2100, depreciated_value=5100, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1500, depreciated_value=5700, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=900, depreciated_value=6300, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=300, depreciated_value=6900, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=300, remaining_value=0, depreciated_value=7200, state='draft'),
        ])

    def test_linear_start_middle_month_reevaluation_end_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-15", prorata="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-30"),
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=300, remaining_value=6900, depreciated_value=300, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6300, depreciated_value=900, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5700, depreciated_value=1500, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=5100, depreciated_value=2100, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=600, remaining_value=4500, depreciated_value=2700, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=3900, depreciated_value=3300, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3300, depreciated_value=3900, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2700, depreciated_value=4500, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=2100, depreciated_value=5100, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1500, depreciated_value=5700, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=900, depreciated_value=6300, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=300, depreciated_value=6900, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=300, remaining_value=0, depreciated_value=7200, state='draft'),
        ])

    def test_linear_start_end_month_reevaluation_beginning_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-28", prorata="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-01"),
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=21.43, remaining_value=7178.57, depreciated_value=21.43, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6578.57, depreciated_value=621.43, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5978.57, depreciated_value=1221.43, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=5378.57, depreciated_value=1821.43, state='posted'),
            # 20 because we have 1 * 600 / 30 (1 day of a month of 30 days, with 600 per month)
            self._get_depreciation_move_values(date='2022-06-01', depreciation_value=20, remaining_value=5358.57, depreciated_value=1841.43, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=580, remaining_value=4778.57, depreciated_value=2421.43, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=4178.57, depreciated_value=3021.43, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3578.57, depreciated_value=3621.43, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2978.57, depreciated_value=4221.43, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=2378.57, depreciated_value=4821.43, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1778.57, depreciated_value=5421.43, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=1178.57, depreciated_value=6021.43, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=578.57, depreciated_value=6621.43, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=578.57, remaining_value=0, depreciated_value=7200, state='draft'),
        ])

    def test_linear_start_end_month_reevaluation_middle_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-28", prorata="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-15"),
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=21.43, remaining_value=7178.57, depreciated_value=21.43, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6578.57, depreciated_value=621.43, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5978.57, depreciated_value=1221.43, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=5378.57, depreciated_value=1821.43, state='posted'),
            # 300 because we have 15 * 600 / 30 (15 days of a month of 30 days, with 600 per month)
            self._get_depreciation_move_values(date='2022-06-15', depreciation_value=300, remaining_value=5078.57, depreciated_value=2121.43, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=300, remaining_value=4778.57, depreciated_value=2421.43, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=4178.57, depreciated_value=3021.43, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3578.57, depreciated_value=3621.43, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2978.57, depreciated_value=4221.43, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=2378.57, depreciated_value=4821.43, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1778.57, depreciated_value=5421.43, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=1178.57, depreciated_value=6021.43, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=578.57, depreciated_value=6621.43, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=578.57, remaining_value=0, depreciated_value=7200, state='draft'),
        ])

    def test_linear_start_end_month_reevaluation_end_month(self):
        asset = self.create_asset(value=7200, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-02-28", prorata="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-30"),
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=21.43, remaining_value=7178.57, depreciated_value=21.43, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=600, remaining_value=6578.57, depreciated_value=621.43, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=600, remaining_value=5978.57, depreciated_value=1221.43, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=600, remaining_value=5378.57, depreciated_value=1821.43, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=600, remaining_value=4778.57, depreciated_value=2421.43, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=600, remaining_value=4178.57, depreciated_value=3021.43, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=600, remaining_value=3578.57, depreciated_value=3621.43, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=600, remaining_value=2978.57, depreciated_value=4221.43, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=600, remaining_value=2378.57, depreciated_value=4821.43, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=600, remaining_value=1778.57, depreciated_value=5421.43, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=600, remaining_value=1178.57, depreciated_value=6021.43, state='draft'),
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=600, remaining_value=578.57, depreciated_value=6621.43, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=578.57, remaining_value=0, depreciated_value=7200, state='draft'),
        ])

    def test_linear_reevaluation_simple_decrease(self):
        asset = self.create_asset(value=10000, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-01-01", prorata="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-30"),
            'value_residual': 4000,  # -1000
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=833.33, remaining_value=9166.67, depreciated_value=833.33, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=833.34, remaining_value=8333.33, depreciated_value=1666.67, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=833.33, remaining_value=7500, depreciated_value=2500, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=833.33, remaining_value=6666.67, depreciated_value=3333.33, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=833.34, remaining_value=5833.33, depreciated_value=4166.67, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=833.33, remaining_value=5000, depreciated_value=5000, state='posted'),
            # decrease move
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=1000, remaining_value=4000, depreciated_value=6000, state='posted'),

            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=666.67, remaining_value=3333.33, depreciated_value=6666.67, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=666.67, remaining_value=2666.66, depreciated_value=7333.34, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=666.66, remaining_value=2000, depreciated_value=8000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=666.67, remaining_value=1333.33, depreciated_value=8666.67, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=666.67, remaining_value=666.66, depreciated_value=9333.34, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=666.66, remaining_value=0, depreciated_value=10000, state='draft'),
        ])

    def test_linear_reevaluation_double_decrease(self):
        asset = self.create_asset(value=60000, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-01-01", prorata="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-04-15"),
            'value_residual': asset.value_residual - 8500,
        }).modify()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-30"),
            'value_residual': 18000,  # -6000
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=5000, remaining_value=55000, depreciated_value=5000, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=5000, remaining_value=50000, depreciated_value=10000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=5000, remaining_value=45000, depreciated_value=15000, state='posted'),
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=2500, remaining_value=42500, depreciated_value=17500, state='posted'),
            # decrease move
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=8500, remaining_value=34000, depreciated_value=26000, state='posted'),

            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=2000, remaining_value=32000, depreciated_value=28000, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=4000, remaining_value=28000, depreciated_value=32000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=4000, remaining_value=24000, depreciated_value=36000, state='posted'),
            # decrease move
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=6000, remaining_value=18000, depreciated_value=42000, state='posted'),

            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=3000, remaining_value=15000, depreciated_value=45000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=3000, remaining_value=12000, depreciated_value=48000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=3000, remaining_value=9000, depreciated_value=51000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=3000, remaining_value=6000, depreciated_value=54000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=3000, remaining_value=3000, depreciated_value=57000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=3000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_linear_reevaluation_double_increase(self):
        asset = self.create_asset(value=60000, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-01-01", prorata="constant_periods")
        asset.validate()
        self.assert_counterpart_account_id = self.company_data['default_account_expense'].copy().id

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-04-15"),
            'value_residual': asset.value_residual + 8500,
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-30"),
            'value_residual': asset.value_residual + 6000,
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=5000, remaining_value=55000, depreciated_value=5000, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=5000, remaining_value=50000, depreciated_value=10000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=5000, remaining_value=45000, depreciated_value=15000, state='posted'),
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=2500, remaining_value=42500, depreciated_value=17500, state='posted'),

            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=2500, remaining_value=40000, depreciated_value=20000, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=5000, remaining_value=35000, depreciated_value=25000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=5000, remaining_value=30000, depreciated_value=30000, state='posted'),

            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=5000, remaining_value=25000, depreciated_value=35000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=5000, remaining_value=20000, depreciated_value=40000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=5000, remaining_value=15000, depreciated_value=45000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=5000, remaining_value=10000, depreciated_value=50000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=5000, remaining_value=5000, depreciated_value=55000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=5000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids[0].depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=500, remaining_value=8000, depreciated_value=500, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=1000, remaining_value=7000, depreciated_value=1500, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=1000, remaining_value=6000, depreciated_value=2500, state='posted'),

            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1000, remaining_value=5000, depreciated_value=3500, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=1000, remaining_value=4000, depreciated_value=4500, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=1000, remaining_value=3000, depreciated_value=5500, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=1000, remaining_value=2000, depreciated_value=6500, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=1000, remaining_value=1000, depreciated_value=7500, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=1000, remaining_value=0, depreciated_value=8500, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids[1].depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1000, remaining_value=5000, depreciated_value=1000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=1000, remaining_value=4000, depreciated_value=2000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=1000, remaining_value=3000, depreciated_value=3000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=1000, remaining_value=2000, depreciated_value=4000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=1000, remaining_value=1000, depreciated_value=5000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=1000, remaining_value=0, depreciated_value=6000, state='draft'),
        ])

    def test_linear_reevaluation_decrease_then_increase(self):
        asset = self.create_asset(value=60000, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-01-01", prorata="constant_periods")
        asset.validate()
        self.assert_counterpart_account_id = self.company_data['default_account_expense'].copy().id

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-04-15"),
            'value_residual': asset.value_residual - 8500,
        }).modify()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-30"),
            'value_residual': asset.value_residual + 6000,
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=5000, remaining_value=55000, depreciated_value=5000, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=5000, remaining_value=50000, depreciated_value=10000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=5000, remaining_value=45000, depreciated_value=15000, state='posted'),
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=2500, remaining_value=42500, depreciated_value=17500, state='posted'),
            # decrease move
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=8500, remaining_value=34000, depreciated_value=26000, state='posted'),

            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=2000, remaining_value=32000, depreciated_value=28000, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=4000, remaining_value=28000, depreciated_value=32000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=4000, remaining_value=24000, depreciated_value=36000, state='posted'),

            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=4000, remaining_value=20000, depreciated_value=40000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=4000, remaining_value=16000, depreciated_value=44000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=4000, remaining_value=12000, depreciated_value=48000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=4000, remaining_value=8000, depreciated_value=52000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=4000, remaining_value=4000, depreciated_value=56000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=4000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1000, remaining_value=5000, depreciated_value=1000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=1000, remaining_value=4000, depreciated_value=2000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=1000, remaining_value=3000, depreciated_value=3000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=1000, remaining_value=2000, depreciated_value=4000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=1000, remaining_value=1000, depreciated_value=5000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=1000, remaining_value=0, depreciated_value=6000, state='draft'),
        ])

    def test_linear_reevaluation_decrease_then_increase_with_lock_date(self):
        self.company_data['company'].fiscalyear_lock_date = fields.Date.to_date('2022-03-01')
        asset = self.create_asset(value=60000, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-01-01", prorata="constant_periods")
        asset.validate()
        self.assert_counterpart_account_id = self.company_data['default_account_expense'].copy().id

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-04-15"),
            'value_residual': asset.value_residual - 8500,
        }).modify()

        self.company_data['company'].fiscalyear_lock_date = fields.Date.to_date('2022-05-01')

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-30"),
            'value_residual': asset.value_residual + 6000,
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=5000, remaining_value=55000, depreciated_value=5000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=5000, remaining_value=50000, depreciated_value=10000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=5000, remaining_value=45000, depreciated_value=15000, state='posted'),
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=2500, remaining_value=42500, depreciated_value=17500, state='posted'),
            # decrease move
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=8500, remaining_value=34000, depreciated_value=26000, state='posted'),

            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=2000, remaining_value=32000, depreciated_value=28000, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=4000, remaining_value=28000, depreciated_value=32000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=4000, remaining_value=24000, depreciated_value=36000, state='posted'),

            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=4000, remaining_value=20000, depreciated_value=40000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=4000, remaining_value=16000, depreciated_value=44000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=4000, remaining_value=12000, depreciated_value=48000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=4000, remaining_value=8000, depreciated_value=52000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=4000, remaining_value=4000, depreciated_value=56000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=4000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1000, remaining_value=5000, depreciated_value=1000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=1000, remaining_value=4000, depreciated_value=2000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=1000, remaining_value=3000, depreciated_value=3000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=1000, remaining_value=2000, depreciated_value=4000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=1000, remaining_value=1000, depreciated_value=5000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=1000, remaining_value=0, depreciated_value=6000, state='draft'),
        ])

    def test_linear_reevaluation_increase_then_decrease(self):
        asset = self.create_asset(value=60000, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-01-01", prorata="constant_periods")
        asset.validate()
        self.assert_counterpart_account_id = self.company_data['default_account_expense'].copy().id

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-04-15"),
            'value_residual': asset.value_residual + 8500,
            "account_asset_counterpart_id": self.assert_counterpart_account_id,
        }).modify()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-06-30"),
            'value_residual': asset.value_residual - 6000,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=5000, remaining_value=55000, depreciated_value=5000, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=5000, remaining_value=50000, depreciated_value=10000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=5000, remaining_value=45000, depreciated_value=15000, state='posted'),
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=2500, remaining_value=42500, depreciated_value=17500, state='posted'),

            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=2500, remaining_value=40000, depreciated_value=20000, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=5000, remaining_value=35000, depreciated_value=25000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=5000, remaining_value=30000, depreciated_value=30000, state='posted'),

            # decrease move
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=6000, remaining_value=24000, depreciated_value=36000, state='posted'),

            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=4000, remaining_value=20000, depreciated_value=40000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=4000, remaining_value=16000, depreciated_value=44000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=4000, remaining_value=12000, depreciated_value=48000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=4000, remaining_value=8000, depreciated_value=52000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=4000, remaining_value=4000, depreciated_value=56000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=4000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids[0].depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=500, remaining_value=8000, depreciated_value=500, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=1000, remaining_value=7000, depreciated_value=1500, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=1000, remaining_value=6000, depreciated_value=2500, state='posted'),

            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1000, remaining_value=5000, depreciated_value=3500, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=1000, remaining_value=4000, depreciated_value=4500, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=1000, remaining_value=3000, depreciated_value=5500, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=1000, remaining_value=2000, depreciated_value=6500, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=1000, remaining_value=1000, depreciated_value=7500, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=1000, remaining_value=0, depreciated_value=8500, state='draft'),
        ])

    def test_linear_reevaluation_decrease_then_disposal(self):
        asset = self.create_asset(value=60000, periodicity="monthly", periods=12, method="linear", acquisition_date="2022-01-01", prorata="constant_periods")
        asset.validate()
        self.loss_account_id = self.company_data['default_account_expense'].copy().id

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-04-15"),
            'value_residual': asset.value_residual - 8500,
        }).modify()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'date':  fields.Date.to_date("2022-06-30"),
            'modify_action': 'dispose',
            'loss_account_id': self.loss_account_id,
        }).sell_dispose()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=5000, remaining_value=55000, depreciated_value=5000, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=5000, remaining_value=50000, depreciated_value=10000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=5000, remaining_value=45000, depreciated_value=15000, state='posted'),
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=2500, remaining_value=42500, depreciated_value=17500, state='posted'),
            # decrease move
            self._get_depreciation_move_values(date='2022-04-15', depreciation_value=8500, remaining_value=34000, depreciated_value=26000, state='posted'),

            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=2000, remaining_value=32000, depreciated_value=28000, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=4000, remaining_value=28000, depreciated_value=32000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=4000, remaining_value=24000, depreciated_value=36000, state='posted'),

            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=24000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_linear_reevaluation_increase_constant_periods(self):
        asset = self.create_asset(value=1200, periodicity="monthly", periods=12, method="linear", acquisition_date="2021-10-01", prorata="constant_periods")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-01-15"),
            'modify_action': 'modify',
            'value_residual': 2400,
            'account_asset_counterpart_id': self.company_data['default_account_revenue'].copy().id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=100, remaining_value=1100, depreciated_value=100, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=100, remaining_value=1000, depreciated_value=200, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=100, remaining_value=900, depreciated_value=300, state='posted'),
            self._get_depreciation_move_values(date='2022-01-15', depreciation_value=48.39, remaining_value=851.61, depreciated_value=348.39, state='posted'),

            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=51.61, remaining_value=800, depreciated_value=400, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=100, remaining_value=700, depreciated_value=500, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=100, remaining_value=600, depreciated_value=600, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=100, remaining_value=500, depreciated_value=700, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=100, remaining_value=400, depreciated_value=800, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=100, remaining_value=300, depreciated_value=900, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=100, remaining_value=200, depreciated_value=1000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=100, remaining_value=100, depreciated_value=1100, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=100, remaining_value=0, depreciated_value=1200, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=127.27, remaining_value=1972.73, depreciated_value=127.27, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=246.59, remaining_value=1726.14, depreciated_value=373.86, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=246.59, remaining_value=1479.55, depreciated_value=620.45, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=246.60, remaining_value=1232.95, depreciated_value=867.05, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=246.59, remaining_value=986.36, depreciated_value=1113.64, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=246.59, remaining_value=739.77, depreciated_value=1360.23, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=246.59, remaining_value=493.18, depreciated_value=1606.82, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=246.59, remaining_value=246.59, depreciated_value=1853.41, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=246.59, remaining_value=0, depreciated_value=2100, state='draft'),
        ])

    def test_linear_reevaluation_increase_daily_computation(self):
        asset = self.create_asset(value=1200, periodicity="monthly", periods=12, method="linear", acquisition_date="2021-10-01", prorata="daily_computation")
        asset.validate()

        self.env['asset.modify'].create({
            'asset_id': asset.id,
            'name': 'Test reason',
            'date':  fields.Date.to_date("2022-01-15"),
            'modify_action': 'modify',
            'value_residual': 2400,
            'account_asset_counterpart_id': self.company_data['default_account_revenue'].copy().id,
        }).modify()

        self.assertRecordValues(asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=101.92, remaining_value=1098.08, depreciated_value=101.92, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=98.63, remaining_value=999.45, depreciated_value=200.55, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=101.92, remaining_value=897.53, depreciated_value=302.47, state='posted'),
            self._get_depreciation_move_values(date='2022-01-15', depreciation_value=49.31, remaining_value=848.22, depreciated_value=351.78, state='posted'),

            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=52.60, remaining_value=795.62, depreciated_value=404.38, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=92.06, remaining_value=703.56, depreciated_value=496.44, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=101.92, remaining_value=601.64, depreciated_value=598.36, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=98.63, remaining_value=503.01, depreciated_value=696.99, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=101.91, remaining_value=401.10, depreciated_value=798.90, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=98.63, remaining_value=302.47, depreciated_value=897.53, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=101.92, remaining_value=200.55, depreciated_value=999.45, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=101.92, remaining_value=98.63, depreciated_value=1101.37, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=98.63, remaining_value=0, depreciated_value=1200, state='draft'),
        ])

        self.assertRecordValues(asset.children_ids.depreciation_move_ids.sorted(lambda mv: (mv.date, mv.id)), [
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=130.08, remaining_value=1967.45, depreciated_value=130.08, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=227.64, remaining_value=1739.81, depreciated_value=357.72, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=252.03, remaining_value=1487.78, depreciated_value=609.75, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=243.90, remaining_value=1243.88, depreciated_value=853.65, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=252.02, remaining_value=991.86, depreciated_value=1105.67, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=243.90, remaining_value=747.96, depreciated_value=1349.57, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=252.03, remaining_value=495.93, depreciated_value=1601.60, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=252.03, remaining_value=243.90, depreciated_value=1853.63, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=243.90, remaining_value=0, depreciated_value=2097.53, state='draft'),
        ])
