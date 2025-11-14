#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025
# GNU General Public License v3.0+

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: system_info
short_description: Gather system configuration information
version_added: "2.9"
description:
    - Retrieves sudo users, NTP settings, DNS configuration, and IPv6 status
    - Works on Linux systems
options: {}
author:
    - Your Name
'''

EXAMPLES = '''
# Get system information
- name: Gather system configuration
  system_info:
  register: sys_info

- name: Display results
  debug:
    var: sys_info
'''

RETURN = '''
sudo_users:
    description: List of users with sudo privileges
    type: list
    returned: always
ntp_settings:
    description: NTP configuration details
    type: dict
    returned: always
dns_settings:
    description: DNS server configuration
    type: dict
    returned: always
ipv6_status:
    description: IPv6 enabled/disabled status
    type: dict
    returned: always
'''

from ansible.module_utils.basic import AnsibleModule
import os
import re


def get_sudo_users():
    """Get list of users with sudo privileges"""
    sudo_users = []
    
    # Check /etc/sudoers and /etc/sudoers.d/
    sudoers_files = ['/etc/sudoers']
    
    if os.path.exists('/etc/sudoers.d'):
        sudoers_d_files = [
            os.path.join('/etc/sudoers.d', f) 
            for f in os.listdir('/etc/sudoers.d')
            if os.path.isfile(os.path.join('/etc/sudoers.d', f))
        ]
        sudoers_files.extend(sudoers_d_files)
    
    for filepath in sudoers_files:
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if line.startswith('#') or not line:
                        continue
                    
                    # Match user sudo entries
                    if 'ALL=(ALL' in line or 'ALL = (ALL' in line:
                        user = line.split()[0]
                        if user not in ['root', '%sudo', '%wheel', '%admin']:
                            if not user.startswith('%'):
                                sudo_users.append(user)
        except (IOError, PermissionError):
            continue
    
    # Check sudo and wheel groups
    try:
        with open('/etc/group', 'r') as f:
            for line in f:
                if line.startswith('sudo:') or line.startswith('wheel:'):
                    parts = line.strip().split(':')
                    if len(parts) >= 4 and parts[3]:
                        sudo_users.extend(parts[3].split(','))
    except (IOError, PermissionError):
        pass
    
    return list(set(sudo_users))


def get_ntp_settings(module):
    """Get NTP configuration"""
    ntp_info = {
        'service': 'unknown',
        'enabled': False,
        'servers': [],
        'status': 'unknown'
    }
    
    # Check for chronyd
    rc, out, err = module.run_command('which chronyd')
    if rc == 0:
        ntp_info['service'] = 'chronyd'
        
        # Check if service is active
        rc, out, err = module.run_command('systemctl is-active chronyd')
        ntp_info['enabled'] = (out.strip() == 'active')
        ntp_info['status'] = out.strip()
        
        # Get NTP servers
        if os.path.exists('/etc/chrony.conf'):
            try:
                with open('/etc/chrony.conf', 'r') as f:
                    for line in f:
                        if line.strip().startswith('server') or line.strip().startswith('pool'):
                            parts = line.split()
                            if len(parts) >= 2:
                                ntp_info['servers'].append(parts[1])
            except IOError:
                pass
    
    # Check for ntpd
    rc, out, err = module.run_command('which ntpd')
    if rc == 0 and ntp_info['service'] == 'unknown':
        ntp_info['service'] = 'ntpd'
        
        rc, out, err = module.run_command('systemctl is-active ntpd')
        ntp_info['enabled'] = (out.strip() == 'active')
        ntp_info['status'] = out.strip()
        
        if os.path.exists('/etc/ntp.conf'):
            try:
                with open('/etc/ntp.conf', 'r') as f:
                    for line in f:
                        if line.strip().startswith('server'):
                            parts = line.split()
                            if len(parts) >= 2:
                                ntp_info['servers'].append(parts[1])
            except IOError:
                pass
    
    # Check for systemd-timesyncd
    rc, out, err = module.run_command('which systemd-timesyncd')
    if rc == 0 and ntp_info['service'] == 'unknown':
        ntp_info['service'] = 'systemd-timesyncd'
        
        rc, out, err = module.run_command('systemctl is-active systemd-timesyncd')
        ntp_info['enabled'] = (out.strip() == 'active')
        ntp_info['status'] = out.strip()
        
        rc, out, err = module.run_command('timedatectl show-timesync --all')
        if rc == 0:
            for line in out.split('\n'):
                if 'ServerName=' in line:
                    server = line.split('=')[1].strip()
                    if server:
                        ntp_info['servers'].append(server)
    
    return ntp_info


def get_dns_settings():
    """Get DNS configuration"""
    dns_info = {
        'nameservers': [],
        'search_domains': [],
        'resolv_conf': '/etc/resolv.conf'
    }
    
    if os.path.exists('/etc/resolv.conf'):
        try:
            with open('/etc/resolv.conf', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('nameserver'):
                        parts = line.split()
                        if len(parts) >= 2:
                            dns_info['nameservers'].append(parts[1])
                    elif line.startswith('search'):
                        parts = line.split()
                        if len(parts) >= 2:
                            dns_info['search_domains'].extend(parts[1:])
        except IOError:
            pass
    
    return dns_info


def get_ipv6_status(module):
    """Check if IPv6 is disabled"""
    ipv6_info = {
        'disabled': False,
        'disable_method': [],
        'sysctl_values': {}
    }
    
    # Check sysctl settings
    sysctl_params = [
        'net.ipv6.conf.all.disable_ipv6',
        'net.ipv6.conf.default.disable_ipv6',
        'net.ipv6.conf.lo.disable_ipv6'
    ]
    
    for param in sysctl_params:
        rc, out, err = module.run_command(f'sysctl {param}')
        if rc == 0:
            value = out.strip().split('=')[-1].strip()
            ipv6_info['sysctl_values'][param] = value
            if value == '1':
                ipv6_info['disabled'] = True
                ipv6_info['disable_method'].append('sysctl')
    
    # Check GRUB configuration
    grub_files = [
        '/etc/default/grub',
        '/boot/grub/grub.cfg',
        '/boot/grub2/grub.cfg'
    ]
    
    for grub_file in grub_files:
        if os.path.exists(grub_file):
            try:
                with open(grub_file, 'r') as f:
                    content = f.read()
                    if 'ipv6.disable=1' in content:
                        ipv6_info['disabled'] = True
                        if 'grub' not in ipv6_info['disable_method']:
                            ipv6_info['disable_method'].append('grub')
            except IOError:
                pass
    
    # Check if IPv6 address exists
    rc, out, err = module.run_command('ip -6 addr show')
    if rc == 0 and out.strip():
        # If there are IPv6 addresses (other than ::1), IPv6 is likely enabled
        has_ipv6 = False
        for line in out.split('\n'):
            if 'inet6' in line and '::1' not in line:
                has_ipv6 = True
                break
        if not has_ipv6 and ipv6_info['disabled']:
            ipv6_info['status'] = 'disabled'
        elif has_ipv6:
            ipv6_info['status'] = 'enabled'
            ipv6_info['disabled'] = False
    
    return ipv6_info


def main():
    module = AnsibleModule(
        argument_spec={},
        supports_check_mode=True
    )
    
    result = {
        'changed': False,
        'sudo_users': [],
        'ntp_settings': {},
        'dns_settings': {},
        'ipv6_status': {}
    }
    
    try:
        result['sudo_users'] = get_sudo_users()
        result['ntp_settings'] = get_ntp_settings(module)
        result['dns_settings'] = get_dns_settings()
        result['ipv6_status'] = get_ipv6_status(module)
        
        module.exit_json(**result)
    
    except Exception as e:
        module.fail_json(msg=str(e))


if __name__ == '__main__':
    main()