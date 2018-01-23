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

import re
import socket


VERSION = "0.1.1"

NODE_PATTERN = r'((?:/?([^/]+)/)?([^%:]+)(%[0-9]+)?)(?::(.+))?'
NODE_RE = re.compile(NODE_PATTERN)


def resolv_port(service_name, protocol=None):
    """Get port by service name

    :arg str service_name: Service name
    :arg str protocol: Protocol (defaults to :obj:`None`
    :return: Port number as :func:`str` or service_name if unknown
    """
    try:
        return str(socket.getservbyname(service_name, protocol))
    except OSError:
        return service_name


def node_info(node_str):
    """Extract node info from node string

    Node string is under the form:
        [[/]partition/]addr[%iface][:port]

    :arg str node_str: Node string
    :return: Node info as :class:`tuple` (name, partition, address, iface, port)
    """
    (name, partition, address, iface, port) = NODE_RE.match(node_str).groups()
    try:
        int(port)
    except ValueError:
        port = resolv_port(port, 'tcp')
    return name, partition, address, iface, port


class F5Cfg(object):
    """F5 BigIP configuration reader

    :arg str config_filename: Configuration file name
    """

    def __init__(self, config_filename):
        """Initialization"""
        self.parser = F5CfgParser(config_filename)
        self.cfg = self.parser.cfg

    @property
    def nodes(self):
        """Direct access to configuration's nodes

        :return: Nodes data as :class:`dict`
        """
        return self.cfg.get('ltm', {}).get('node', {})

    @property
    def ssl_profiles(self):
        """Direct access to configuration's ssl profiles

        :return: SSL profiles data as :class:`dict`
        """
        return self.cfg.get('ltm', {}).get('profile', {}).get('client-ssl', {})

    @property
    def virtual_servers(self):
        """Direct access to configuration's virtual servers

        :return: Virtual servers data as :class:`dict`
        """
        return self.cfg.get('ltm', {}).get('virtual', {})

    @property
    def pools(self):
        """Direct access to configuration's pools

        :return: Pools data as :class:`dict`
        """
        return self.cfg.get('ltm', {}).get('pool', {})

    @property
    def rules(self):
        """Direct access to configuration's irules

        :return: Rules data as :class:`dict`
        """
        return self.cfg.get('ltm', {}).get('rule', {})

    @property
    def monitors(self):
        """Direct access to configuration's monitors

        :return: Monitors data as :class:`dict`
        """
        return self.cfg.get('ltm', {}).get('monitor', {})

    def get_pools_by_node(self, node_name):
        """Get pools data by node name

        :return: Pools data as :func:`list` of :class:`dict`
        """
        pools = []
        for pool, data in self.pools.items():
            for member in data.get('members', {}):
                if node_name == node_info(member)[0]:
                    pools.append(pool)
                    break
        return pools

    def get_node(self, node_name):
        """Get node by name

        :arg str node_name: Node name
        :return: Node data as :class:`dict` or :obj:`None`
        """
        return self.nodes.get(node_name)

    def get_ssl_profile(self, profile_name):
        """Get SSL profile by name

        :arg str profile_name: SSL profile name
        :return: SSL profile data as :class:`dict` or :obj:`None`
        """
        return self.ssl_profiles.get(profile_name)

    def get_ssl_profile_by_virtual_server(self, vs_name):
        """Get SSL profile by virtual server name

        :arg str vs_name: Virtual server name
        :return: SSL profile data as :class:`dict` or :obj:`None`
        """
        profile_name = None
        ssl_profile = None
        profiles = self.virtual_servers.get(vs_name, {}).get('profiles', {})
        for profile in profiles:
            ssl_profile = self.get_ssl_profile(profile)
            if ssl_profile is not None:
                profile_name = profile
                break
        return profile_name, ssl_profile

    def get_virtual_server(self, vs_name):
        """Get virtual server by name

        :arg str vs_name: Virtual server name
        :return: Virtual server data as :class:`dict` or :obj:`None`
        """
        return self.virtual_servers.get(vs_name)

    def get_virtual_servers_by_node(self, node_name):
        """Get virtual servers by node name

        :arg str node_name: Node name
        :return: Virtual servers data as [:class:`dict`,...] or :obj:`None`
        """
        virtual_servers = []
        pools = self.get_pools_by_node(node_name)
        for vserver, data in self.virtual_servers.items():
            if data.get('pool') in pools:
                virtual_servers.append(vserver)
        return virtual_servers

    def get_pool(self, pool_name):
        """Get pool by name

        :arg str pool_name: Pool name
        :return: Pool data as :class:`dict` or :obj:`None`
        """
        return self.pools.get(pool_name)

    def get_pool_members(self, pool_name):
        """Get pool members by pool name

        :arg str pool_name: Pool name
        :return: Pool members as :class:`list` or None
        """
        try:
            members = []
            for member, data in self.get_pool(pool_name)['members'].items():

                (node_name, _, address, _, port) = node_info(member)
                node = self.get_node(node_name)
                node['name'] = node_name
                node['port'] = port
                # On older version, node has no address field
                # Then assume that node name is IP[%Iface]
                if 'address' not in node:
                    node['address'] = address
                if 'description' not in node:
                    node['description'] = ''
                if 'state' not in node:
                    node['state'] = node.get('status', 'unknown')
                members.append(node)
            return members
        except AttributeError:
            # On older version, pool members may be str('none')
            return []

    def list_virtual_server_chains(self):
        """Return virtual server chains
        """
        vservers = []
        for vserver, data in self.virtual_servers.items():
            vpartition, vname = '', vserver
            if '/' in vserver:
                vpartition, vname = vserver.split('/', 1)
            (_, partition, vip, _, port) = node_info(data['destination'])
            pool_name = ""
            pool_members = []
            if data.get('pool', 'none') != 'none':
                pool_name = data['pool']
                pool_members = self.get_pool_members(pool_name)
            ssl_profile = self.get_ssl_profile_by_virtual_server(vserver)[0]
            ssl_cert = None
            if ssl_profile:
                ssl_cert = self.ssl_profiles[ssl_profile]['cert']
            rules = None
            if data['rules'] != 'none':
                rules = [self.rules.get(rname, rname)
                         for rname in data['rules']]
            vservers.append(dict({
                'partition': vpartition,
                'vserver': vname,
                'vip': vip,
                'port': port,
                'ssl_profile': ssl_profile,
                'ssl_cert': ssl_cert,
                'rules': rules,
                'pool_name': pool_name,
                'nodes': pool_members
            }))
        return vservers


class F5CfgParser(object):
    """F5 BigIP configuration parser

    :arg str config_filename: Configuration file name
    """

    def __init__(self, config_filename):
        """Initialization"""
        self.cfg = {}

        # Try to validate utf-8 encoding of configuration file
        try:
            encoding = 'utf-8'
            with open(config_filename, encoding='utf-8') as config_test:
                config_test.read()
        except:
            # fallback to iso8859_15
            encoding = 'iso8859_15'

        self.config_fd = open(config_filename, encoding=encoding)
        self.parse()

    @staticmethod
    def _check_quotes(line, open_quote=0):
        """Count quote on line and return open quote blocks count
        """
        for idx, char in enumerate(line):
            if char == '"' and line[idx-1] != '\\':
                open_quote = (open_quote + 1) % 2
        return open_quote

    @staticmethod
    def build_hierarchy(struct, fields):
        """Build dict hierarchy from fields list
        """
        hierarchy = struct
        for field in fields:
            if field not in hierarchy:
                hierarchy.update({field: {}})
            hierarchy = hierarchy[field]
        return hierarchy

    def skip_block(self):
        """skip configuration block
        """
        for line in self.config_fd:
            line = line.strip()
            if line == '}':
                return
        raise SyntaxError('skipped block does not end with "}"')

    def get_rule_block(self):
        """Get configuration irule block as text

        :return: IRule block text as :func:`str`
        """
        open_block = 1
        text = ""
        for line in self.config_fd:
            for char in line:
                if char == '{':
                    open_block += 1
                elif char == '}':
                    open_block -= 1
            if '}' in line and open_block == 0:
                return text.strip()
            text += line
        raise SyntaxError('text block does not end with "}"')

    def get_text_field(self, text):
        """Get configuration text field content

        :return: Text field value as :func:`str`
        """
        open_quote = self._check_quotes(text)
        if open_quote == 0:
                return text.strip()

        for line in self.config_fd:
            open_quote = self._check_quotes(line, open_quote)
            text += line
            if open_quote == 0:
                return text.strip()
        raise SyntaxError('unterminated text field')

    def parse_blocks(self):
        """Get configuration instruction from a single block

        :return: Parsed block as :class:`dict`
        """
        struct = {}
        for line in self.config_fd:
            line = line.strip()

            if line == '{':
                # this block is a list of entries, convert struct to list
                if struct == {}:
                    struct = []
                struct.append(self.parse_blocks())
            elif line.endswith('{'):
                fields = line[:-2].split()
                new_section = self.build_hierarchy(struct, fields[:-1])
                if line.startswith('ltm rule '):
                    # specific handling of rules text block
                    new_section.update({fields[-1]: self.get_rule_block()})
                else:
                    block = self.parse_blocks()
                    if fields[-1] in new_section \
                        and block.get('members') == 'none':
                        # Handle a weird duplicate pools in configuration
                        continue
                    new_section.update({fields[-1]: block})
            elif line.endswith('{ }'):
                fields = line[:-3].split()
                new_section = self.build_hierarchy(struct, fields[:-1])
                new_section.update({fields[-1]: {}})
            elif line == '}':
                return struct
            else:
                fields = line.split(None, 1)
                if len(fields) == 1:
                    fields.append(None)
                elif '"' in fields[1]:
                    fields[1] = self.get_text_field(fields[1])
                struct[fields[0]] = fields[1]

        return struct

    def parse(self):
        """Parse configuration file content
        """
        self.cfg = self.parse_blocks()


if __name__ == "__main__":
    # TODO: Tests go here
    exit()
