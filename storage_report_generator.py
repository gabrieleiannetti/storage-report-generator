#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright 2018 Gabriele Iannetti <g.iannetti@gsi.de>
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


import ConfigParser
import datetime
import argparse
import logging
import sys
import os

import dataset.lustre_dataset_handler as ds
import filter.group_filter_handler as gf
from lfs.disk_usage_info import lustre_total_size

from chart.quota_pct_bar_chart import QuotaPctBarChart
from chart.usage_quota_bar_chart import UsageQuotaBarChart
from chart.usage_pie_chart import UsagePieChart
from chart.trend_chart import TrendChart

from utils.matplot import check_matplotlib_version
from utils.rsync import transfer_report


def create_usage_pie_chart(title, group_info_list, file_path,
                           storage_total_size, num_top_groups):

    chart = UsagePieChart(title, group_info_list, file_path, storage_total_size,
                          num_top_groups)
    chart.create()


def create_quota_pct_bar_chart(title, group_info_list, file_path):

    chart = QuotaPctBarChart(title, group_info_list, file_path)
    chart.create()


def create_usage_quota_bar_chart(title, group_info_list, file_path):

    chart = UsageQuotaBarChart(title, group_info_list, file_path)
    chart.create()


def create_trend_chart(title, group_item_list, file_path,
                       x_label, y_label, start_date, end_date):

    chart = TrendChart(title, group_item_list, file_path,
                       x_label, y_label, start_date, end_date)

    chart.create()


def create_weekly_reports(local_mode, chart_dir, long_name, config):

    reports_path_list = list()

    #TODO: Extract where the data comes from!!!
    group_info_list = None
    storage_total_size = 0

    if local_mode:

        logging.debug('Weekly Run Mode: LOCAL/DEV')

        group_info_list = ds.create_dummy_group_info_list()
        storage_total_size = 18458963071860736

    else:

        logging.debug('Weekly Run Mode: PRODUCTIVE')

        ds.CONFIG = config

        group_info_list = \
            gf.filter_group_info_items(
                ds.get_group_info_list(
                    gf.filter_system_groups(ds.get_group_names())))

        storage_total_size = \
            lustre_total_size(config.get('storage', 'filesystem'))
    
    # QUOTA-PCT-BAR-CHART
    title = "Group Quota Usage on %s" % long_name

    chart_path = \
        chart_dir + os.path.sep + config.get('quota_pct_bar_chart', 'filename')

    create_quota_pct_bar_chart(title, group_info_list, chart_path)

    reports_path_list.append(chart_path)

    # USAGE-QUOTA-BAR-CHART
    title = "Quota and Disk Space Usage on %s" % long_name

    chart_path = chart_dir + os.path.sep + \
                 config.get('usage_quota_bar_chart', 'filename')

    create_usage_quota_bar_chart(title, group_info_list, chart_path)

    reports_path_list.append(chart_path)

    # USAGE-PIE-CHART
    title = "Storage Usage on %s" % long_name

    chart_path = \
        chart_dir + os.path.sep + config.get('usage_pie_chart', 'filename')

    num_top_groups = config.get('usage_pie_chart', 'num_top_groups')

    create_usage_pie_chart(title, group_info_list, chart_path,
                           storage_total_size, num_top_groups)

    reports_path_list.append(chart_path)

    return reports_path_list


def main():

    parser = argparse.ArgumentParser(description='Storage Report Generator.')
    parser.add_argument('-f', '--config-file', dest='config_file', type=str, required=True, help='Path of the config file.')
    parser.add_argument('-D', '--enable-debug', dest='enable_debug', required=False, action='store_true', help='Enables logging of debug messages.')
    parser.add_argument('-L', '--enable-local_mode', dest='enable_local', required=False, action='store_true', help='Enables local_mode program execution.')

    args = parser.parse_args()

    if not os.path.isfile(args.config_file):
        raise IOError("The config file does not exist or is not a file: " + args.config_file)

    logging_level = logging.INFO

    if args.enable_debug:
        logging_level = logging.DEBUG

    logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s: %(message)s')

    try:

        logging.info('START')

        start_date = datetime.datetime.now()

        check_matplotlib_version()

        # Commandline parameter.
        local_mode = args.enable_local

        # Config file parameter.
        config = ConfigParser.ConfigParser()
        config.read(args.config_file)

        run_mode = config.get('execution', 'mode')
        transfer_mode = config.get('execution', 'transfer')

        chart_dir = config.get('base_chart', 'report_dir')
        long_name = config.get('storage', 'long_name')

        if run_mode == 'weekly':

            reports_path_list = \
                create_weekly_reports(local_mode, chart_dir, long_name, config)

            if transfer_mode == 'on':
                transfer_report(run_mode, start_date, reports_path_list, config)

        elif run_mode == 'monthly':
            pass

        else:
            raise RuntimeError('Undefined run_mode detected: %s' % run_mode)

        logging.info('END')

        return 0
   
    except Exception as e:

        exc_type, exc_obj, exc_tb = sys.exc_info()
        filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]

        logging.error("Caught exception (%s): %s - %s (line: %s)"
                      % (exc_type, str(e), filename, exc_tb.tb_lineno))


if __name__ == '__main__':
   main()
