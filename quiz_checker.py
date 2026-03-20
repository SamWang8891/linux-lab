"""Quiz question definitions and automated checkers."""
import paramiko
import requests
import lxd_manager as lxd
import json

try:
    with open('questions.json', r) as file:
        QUIZ_QUESTIONS = json.load(file)
except Exception:
    QUIZ_QUESTIONS = []
    print("Error loading questions.json")



def check_answer(question, answer, container_name, container_ip):
    """Check if the student's answer is correct."""
    check_type = question.get('check_type', question.check_type if hasattr(question, 'check_type') else 'text')
    expected = question.get('expected_answer', getattr(question, 'expected_answer', None))

    if check_type == 'text':
        return answer.strip().lower() == expected.strip().lower()

    elif check_type == 'http':
        try:
            r = requests.get(f'http://{container_ip}', timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    elif check_type == 'ssh':
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(container_ip, username='user', password='linux-lab-2026', timeout=5)
            client.close()
            return True
        except Exception:
            return False

    elif check_type == 'script':
        script_name = question.get('check_script', getattr(question, 'check_script', ''))
        return _run_check_script(script_name, answer, container_name, container_ip)

    return False


def _run_check_script(script_name, answer, container_name, container_ip):
    """Run specific check scripts inside the container."""
    if script_name == 'check_file_content':
        rc, out, _ = lxd.exec_in_container(container_name,
            ['cat', '/var/hidden/hidden_treasure.txt'])
        return rc == 0 and answer.strip() == out.strip()

    elif script_name == 'check_unzip':
        # Accept the known flags directly — students may extract anywhere
        expected = "FLAG{zip_cracked} FLAG{tar_expert}"
        return answer.strip() == expected

    elif script_name == 'check_executable':
        rc, out, _ = lxd.exec_in_container(container_name,
            ['bash', '-c', 'stat -c "%a" /home/user/challenges/run_me'])
        if rc != 0:
            return False
        perms = out.strip()
        # Must be executable (check execute bit in octal)
        try:
            mode = int(perms, 8)
        except ValueError:
            return False
        if not (mode & 0o111):
            return False
        rc, out, _ = lxd.exec_in_container(container_name,
            ['/home/user/challenges/run_me'])
        return answer.strip() == out.strip()

    elif script_name == 'check_file_deleted':
        rc, _, _ = lxd.exec_in_container(container_name,
            ['test', '-f', '/home/user/challenges/delete_me.txt'])
        return rc != 0  # File should NOT exist

    elif script_name == 'check_permission':
        rc, out, _ = lxd.exec_in_container(container_name,
            ['stat', '-c', '%a', '/home/user/challenges/permission_check'])
        return rc == 0 and answer.strip() == out.strip()

    elif script_name == 'check_edit_file':
        rc, out, _ = lxd.exec_in_container(container_name,
            ['cat', '/home/user/challenges/edit_me.txt'])
        return rc == 0 and out.strip() == 'Linux is awesome'

    elif script_name == 'check_bashrc':
        rc, out, _ = lxd.exec_in_container(container_name,
            ['bash', '-c', 'source /home/user/.bashrc && echo $LAB_COMPLETE'])
        return rc == 0 and out.strip() == '1'

    elif script_name == 'check_dpkg':
        rc, _, _ = lxd.exec_in_container(container_name,
            ['which', 'fastfetch'])
        return rc == 0 and len(answer.strip()) > 0

    return False
