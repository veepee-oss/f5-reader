# coding: utf-8

import re


VERSION = "0.1.1"

NODE_PATTERN = r'((?:/([^/]+)/)?([^%:]+)(%[0-9]+)?)(?::([0-9]+))?'
NODE_RE = re.compile(NODE_PATTERN)


def node_info(node_string):
    """Extract node info from node string

    Node string is under the form:
        [/partition/]addr[%iface][:port]

    :arg str node_string: Node string
    :return: Node info as :class:`tuple` (name, partition, address, iface, port)
    """
    return NODE_RE.match(node_string).groups()


class F5Cfg(object):
    """F5 BigIP configuration reader

    :arg str config_filename: Configuration file name
    """

    def __init__(self, config_filename):
        """Initialization"""
        self.parser = F5CfgParser(config_filename)
        self.cfg = self.parser.cfg

        self.monitors = {}
        self.rules = {}

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
        members = []
        for member in self.get_pool(pool_name)['members']:
            (_, partition, address, _, port) = node_info(member)
            node = self.get_node(member.split(':')[0])
            description = node.get('description', '')
            members.append((partition, address, port, description))
        return members

    def output_csv(self):
        """Output virtual servers info as csv
        """
        print("Product name;VIP name;VIP;Port;SSL profile;Pool name;Nodes")
        for vserver, data in self.virtual_servers.items():
            (_, partition, vip, _, port) = node_info(data['destination'])
            pool_name = ""
            pool_members = []
            if 'pool' in data:
                pool_name = data['pool']
                pool_members = self.get_pool_members(pool_name)

            pool_info = ', '.join(['%s:%s (%s)' % (ent[1], ent[2], ent[3])
                                   for ent in pool_members])

            ssl_profile = self.get_ssl_profile_by_virtual_server(vserver)[0]

            print(";%s;%s;%s;%s;%s;%s" % (
                vserver,
                vip, port, ssl_profile,
                pool_name, pool_info
            ))


class F5CfgParser(object):
    """F5 BigIP configuration parser

    :arg str config_filename: Configuration file name
    """

    def __init__(self, config_filename):
        """Initialization"""
        self.cfg = {}

        self.config_fd = open(config_filename)
        self.parse()

    @staticmethod
    def _check_quotes(line, open_quote=0):
        """Count quote on line and return open quote blocks count
        """
        for char in line:
            if char == '"':
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
                    new_section.update({fields[-1]: self.parse_blocks()})
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
