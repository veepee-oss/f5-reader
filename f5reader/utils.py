# coding: utf-8
#
#  F5 BigIP configuration reader (f5reader)
#
#  Copyright (C) 2018 Denis Pompilio (jawa) <dpompilio@vente-privee.com>
#
#  This file is part of f5reader
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the MIT License.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  MIT License for more details.
#
#  You should have received a copy of the MIT License along with this
#  program; if not, see <https://opensource.org/licenses/MIT>.

import json
import requests


def pdns_get_fqdn(pdns_api, api_key, ip_addr):
    """Get IP's fqdns from powerdns API

    :arg str pdns_api: PowerDNS API
    :arg str api_key: API key to authenticate onto PowerDNS API
    :arg str ip_addr: IP address
    :return: DNS names pointing IP address as :func:`list` or :obj:`None`
    """
    req = requests.get("%s/search-data" % pdns_api,
                       params={'q': ip_addr},
                       headers={'X-API-KEY': api_key},
                       verify=False)
    try:
        return [ent["name"] for ent in req.json()]
    except json.decoder.JSONDecodeError:
        return None


def output_csv(data, sep=';', mapping=None):
    """Output info as csv

    :arg list data: List of data :class:`dict`
    :arg str sep: Separator used for CSV
    :arg list mapping: Field name to map on data keys
    :return: CSV formatted data as :func:`str`
    """
    if not mapping:
        mapping = [(key, key) for key in data[0].keys()]

    headers = sep.join([ent[0] for ent in mapping])
    lines = [headers]
    for entry in data:
        field_values = []
        for field in mapping:
            field_values.append(str(entry[field[1]]))
        lines.append(sep.join(field_values))
    return '\n'.join(lines)
