#!/usr/bin/env python3

from mip_helper import io_helper

import logging
import json
import math
import sys
import argparse
import itertools

from collections import OrderedDict
from numpy import arange
from numpy import histogram
import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)

BINS_PARAM = "bins"
STRICT_PARAM = "strict"
EXIT_ON_ERROR_PARAM = "exit_on_error"
DEFAULT_BINS = 20
DEFAULT_STRICT = False
DEFAULT_EXIT_ON_ERROR = True


class UserError(Exception):

    pass


def main():
    """Calculate histogram of dependent variable in a single-node mode and return output in highcharts JSON."""
    try:
        # Read inputs
        inputs = io_helper.fetch_data()
        try:
            dep_var = inputs["data"]["dependent"][0]
        except KeyError:
            logging.warning("Cannot find dependent variables data")
            dep_var = []
        try:
            indep_vars = inputs["data"]["independent"]
        except KeyError:
            logging.warning("Cannot find independent variables data")
            indep_vars = []
        nb_bins = get_bins_param(inputs["parameters"], BINS_PARAM)

        # Compute histograms (JSON formatted for HighCharts)
        histograms_results = compute_histograms(dep_var, indep_vars, nb_bins)

        # Store results
        io_helper.save_results(histograms_results, '', 'application/highcharts+json')
    except UserError as e:
        try:
            logging.error(e)
            strict = get_boolean_param(inputs["parameters"], STRICT_PARAM, DEFAULT_STRICT)
            if (strict):
                # Store error
                io_helper.save_results('', str(e), 'text/plain+error')
            else:
                # Display something to the user
                histograms_results = error_histograms(dep_var, indep_vars)
                io_helper.save_results(histograms_results, '', 'application/highcharts+json')
            exit_on_error = get_boolean_param(inputs["parameters"], EXIT_ON_ERROR_PARAM, DEFAULT_EXIT_ON_ERROR)
            if exit_on_error:
                sys.exit(1)
        except Exception as e:
            logging.error(e, exc_info=True)


def aggregate_histograms(job_ids):
    """Get all histograms from all nodes and sum them together.
    :input job_ids: list of job_ids with intermediate results
    """
    # Read intermediate inputs from jobs
    logging.info("Fetching intermediate data...")
    data = _load_intermediate_data(job_ids)

    # group by label (e.g. `Histogram - agegroup`)
    results = []
    data = sorted(data, key=lambda d: d['label'])
    for key, hists in itertools.groupby(data, key=lambda d: d['label']):
        hists = list(hists)

        # use pandas for easier manipulation
        series = {s['name']: np.array(s['data']) for s in hists[0]['series']}

        # add data from other histograms
        result = hists[0]
        for hist in hists[1:]:
            assert hist['xAxis']['categories'] == result['xAxis']['categories']
            for s in hist['series']:
                if s['name'] not in series:
                    series[s['name']] = s['data']
                else:
                    series[s['name']] += s['data']

        # turn series into original form
        result['series'] = [{'name': k, 'data': list(v)} for k, v in series.items()]
        results.append(result)

    logging.info("Results:\n{}".format(results))
    io_helper.save_results(pd.json.dumps(results), '', 'application/highcharts+json')


def _load_intermediate_data(job_ids):
    jobs_data = [io_helper.get_results(job_id).data for job_id in job_ids]
    # chain all results together, ignore empty results
    data = list(itertools.chain(*[json.loads(d) for d in jobs_data if d]))

    if not data:
        raise UserError('Intermediate jobs {} do not have any data.'.format(job_ids))

    return data


def compute_histograms(dep_var, indep_vars, nb_bins=DEFAULT_BINS):
    histograms = list()
    if len(dep_var) > 0:
        histograms.append(compute_histogram(dep_var, nb_bins=nb_bins))
        grouping_vars = [indep_var for indep_var in indep_vars if is_nominal(indep_var)]
        for grouping_var in grouping_vars:
            histograms.append(compute_histogram(dep_var, grouping_var, nb_bins))
    return json.dumps(histograms)

def compute_histogram(dep_var, grouping_var=None, nb_bins=DEFAULT_BINS):
    label = "Histogram"
    title = '%s histogram' % dep_var['name']
    if grouping_var:
        label += " - %s" % grouping_var["name"]
        title += " by %s" % grouping_var["name"]
    categories, categories_labels = compute_categories(dep_var, nb_bins)
    series = compute_series(dep_var, categories, grouping_var)
    histo = {
        "chart": {"type": 'column'},
        "label": label,
        "title": {"text": title},
        "xAxis": {"categories": categories_labels},
        "yAxis": {
            "allowDecimals": False,
            "min": 0,
            "title": {
                "text": 'Number of participants'
            }
        },
        "series": series
    }
    return histo

def error_histograms(dep_var, indep_vars):
    histograms = list()
    if len(dep_var) > 0:
        histograms.append(error_histogram(dep_var))
        grouping_vars = [indep_var for indep_var in indep_vars if is_nominal(indep_var)]
        for grouping_var in grouping_vars:
            histograms.append(error_histogram(dep_var, grouping_var))
    return json.dumps(histograms)

def error_histogram(dep_var, grouping_var=None):
    label = "Histogram"
    title = '%s histogram (no data or error)' % dep_var['name']
    if grouping_var:
        label += " - %s" % grouping_var["name"]
        title += " by %s" % grouping_var["name"]
    histo = {
        "chart": {"type": 'column'},
        "label": label,
        "title": {"text": title},
        "xAxis": {"categories": []},
        "yAxis": {
            "allowDecimals": False,
            "min": 0,
            "title": {
                "text": 'Number of participants'
            }
        },
        "series": []
    }
    return histo


def compute_categories(dep_var, nb_bins=DEFAULT_BINS):
    values = pd.Series(dep_var['series'])

    if len(values) == 0:
        raise UserError('Dependent variable {} is empty.'.format(dep_var['name']))

    has_nulls = None in dep_var['series']
    if is_nominal(dep_var):
        categories = [str(c) for c in dep_var['type']['enumeration']]
        categories_labels = categories
        if has_nulls:
            categories.append('None')
            categories_labels.append('No data')
    else:
        # calculate min and max if not available in variable
        values = dep_var['series']
        minimum = dep_var.get('minValue', min(values))
        maximum = dep_var.get('maxValue', max(values))

        if is_integer(dep_var):
            step = math.ceil((maximum - minimum) / nb_bins)
            categories = list(arange(minimum, maximum, step).tolist())
            categories_labels = ["%d - %d" % (v, v + step) for v in categories]
        else:
            step = (maximum - minimum) / nb_bins
            categories = list(arange(minimum, maximum, step).tolist())
            categories_labels = ["%s - %s" % ("{:.2f}".format(v), "{:.2f}".format(v + step)) for v in categories]
            categories.append(categories[-1] + step)
            if has_nulls:
                categories.append('None')
                categories_labels.append('No data')
    return categories, categories_labels


def compute_series(dep_var, categories, grouping_var=None):
    series = list()
    has_nulls = None in dep_var['series']
    if is_nominal(dep_var):
        if not grouping_var:
            series.append({"name": "all", "data": count(dep_var['series'], categories)})
        else:
            for series_name in grouping_var['type']['enumeration']:
                filtered_data = [v for v, d in zip(dep_var['series'], grouping_var['series']) if d == series_name]
                series.append({"name": series_name, "data": count(filtered_data, categories)})
    else:
        if not grouping_var:
            # remove NULL values
            values = pd.Series(dep_var['series']).dropna()
            series.append({"name": 'all', "data": [int(i) for i in histogram(values, categories)[0]]})
        else:
            values = pd.Series(dep_var['series'])
            grouping_values = pd.Series(grouping_var['series']).fillna('NaN')

            # remove NULL
            ix = values.notnull()
            values = values.loc[ix]
            grouping_values = grouping_values.loc[ix]

            for series_name in grouping_var['type']['enumeration']:
                filtered_data = [v for v, d in zip(values, grouping_values) if d == series_name]
                series.append({"name": series_name, "data": [int(i) for i in histogram(filtered_data, categories)[0]]})
    return series


def count(data, categories):
    items_count = OrderedDict([(c, 0) for c in categories])
    for v in data:
        try:
            if v is None:
                items_count['None'] += 1
            else:
                items_count[str(v)] += 1
        except KeyError:
            logging.warning("Unknown category %s" % str(v))
            logging.warning("Data: %s" % data)
    return list(items_count.values())


def get_bins_param(params_list, param_name):
    for p in params_list:
        if p["name"] == param_name:
            try:
                return int(p["value"])
            except ValueError:
                logging.warning("%s cannot be cast to integer !")
    logging.info("Using default number of bins: %s" % DEFAULT_BINS)
    return DEFAULT_BINS

def get_boolean_param(params_list, param_name, default_value):
    for p in params_list:
        if p["name"] == param_name:
            try:
                return p["value"].lower() in ("yes", "true", "t", "1")
            except ValueError:
                logging.warning("%s cannot be cast to boolean !")
    logging.info("Using default value: %s for %s" % (default_value, param_name))
    return default_value

def is_nominal(var):
    return var['type']['name'] in ['binominal', 'polynominal']


def is_integer(var):
    return var['type']['name'] in ['integer']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('compute', choices=['compute'])
    parser.add_argument('--mode', choices=['intermediate', 'aggregate'], default='intermediate')
    # QUESTION: (job_id, node) is a primary key of `job_result` table. Does it mean I'll need node ids as well in order
    # to query unique job?
    parser.add_argument('--job-ids', type=str, nargs="*", default=[])

    args = parser.parse_args()

    # > compute --mode intermediate
    if args.mode == 'intermediate':
        main()
    # > compute --mode aggregate --job-ids 12 13 14
    elif args.mode == 'aggregate':
        aggregate_histograms(args.job_ids)
