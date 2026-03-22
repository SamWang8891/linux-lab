"""LXD container management via CLI (no pylxd dependency)."""
import subprocess
import json
import time


def _run(cmd, check=True, timeout=120):
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if check and result.returncode != 0:
        raise RuntimeError(f"LXD command failed: {' '.join(cmd)}\n{result.stderr}")
    return result


def create_container(name, image='images:debian/12', profile='lab-student',
                     network='lab-net', memory='512MB', cpu='1'):
    """Create and start a student container. Deletes existing one if leftover."""
    # Clean up leftover container if exists
    delete_container(name)

    cmd = [
        'lxc', 'launch', image, name,
        '-p', profile,
        '-c', f'limits.memory={memory}',
        '-c', f'limits.cpu={cpu}',
        '-c', 'limits.processes=256',
    ]
    _run(cmd)

    # Wait for network (first launch may need image download + boot time)
    for _ in range(60):
        ip = get_container_ip(name)
        if ip:
            return ip
        time.sleep(2)
    raise RuntimeError(f"Container {name} did not get an IP after 120s")


def delete_container(name):
    """Stop and delete a container."""
    _run(['lxc', 'stop', name, '--force'], check=False)
    _run(['lxc', 'delete', name, '--force'], check=False)


def get_container_ip(name):
    """Get the IPv4 address of a container."""
    result = _run(['lxc', 'list', name, '--format=json'], check=False)
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
        if not data:
            return None
        for net_name, net_info in data[0].get('state', {}).get('network', {}).items():
            if net_name == 'lo':
                continue
            for addr in net_info.get('addresses', []):
                if addr['family'] == 'inet' and addr['scope'] == 'global':
                    return addr['address']
    except (json.JSONDecodeError, KeyError, IndexError):
        pass
    return None


def get_container_status(name):
    """Get container status: running/stopped/error."""
    result = _run(['lxc', 'list', name, '--format=json'], check=False)
    if result.returncode != 0:
        return 'error'
    try:
        data = json.loads(result.stdout)
        if not data:
            return 'not_found'
        return data[0].get('status', 'unknown').lower()
    except (json.JSONDecodeError, KeyError, IndexError):
        return 'error'


def exec_in_container(name, command, timeout=600):
    """Execute a command inside a container."""
    result = _run(['lxc', 'exec', name, '--'] + command, check=False, timeout=timeout)
    return result.returncode, result.stdout, result.stderr


def push_file(name, local_path, remote_path):
    """Push a file into a container."""
    _run(['lxc', 'file', 'push', local_path, f'{name}/{remote_path}'])


def start_container(name):
    """Start a stopped container."""
    _run(['lxc', 'start', name])


def stop_container(name):
    """Stop a running container."""
    _run(['lxc', 'stop', name])


def restart_container(name):
    """Restart a container."""
    _run(['lxc', 'restart', name, '--force'])


def apply_network_limit(name, download_kbps=0, upload_kbps=0):
    """Apply network speed limits to a container.

    download_kbps/upload_kbps: speed in kbps, 0 = unlimited (removes limit).

    LXD bridged NIC limits:
      limits.ingress = traffic FROM container TO bridge (= container upload)
      limits.egress  = traffic FROM bridge TO container (= container download)

    If eth0 is inherited from a profile, we must override it at the instance
    level first before setting properties on it.
    """
    # Ensure eth0 exists as an instance-level device override
    _run(['lxc', 'config', 'device', 'override', name, 'eth0'], check=False)

    if download_kbps > 0:
        _run(['lxc', 'config', 'device', 'set', name, 'eth0',
              f'limits.egress={download_kbps}kbit'], check=False)
    else:
        _run(['lxc', 'config', 'device', 'set', name, 'eth0',
              'limits.egress='], check=False)

    if upload_kbps > 0:
        _run(['lxc', 'config', 'device', 'set', name, 'eth0',
              f'limits.ingress={upload_kbps}kbit'], check=False)
    else:
        _run(['lxc', 'config', 'device', 'set', name, 'eth0',
              'limits.ingress='], check=False)


def apply_cpu_limit(name, cpu='1'):
    """Apply CPU limit to an existing container."""
    _run(['lxc', 'config', 'set', name, f'limits.cpu={cpu}'], check=False)


def get_container_stats(name):
    """Get CPU/memory/disk stats for a container."""
    result = _run(['lxc', 'info', name, '--format=json'], check=False)
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
        state = data.get('state', {})
        return {
            'cpu_usage': state.get('cpu', {}).get('usage', 0),
            'memory_usage': state.get('memory', {}).get('usage', 0),
            'memory_limit': state.get('memory', {}).get('limit', 0),
            'disk': state.get('disk', {}),
            'pid': state.get('pid', 0),
            'status': state.get('status', 'unknown'),
        }
    except (json.JSONDecodeError, KeyError):
        return None
