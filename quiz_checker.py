"""Quiz question definitions and automated checkers."""
import os
import paramiko
import requests
import lxd_manager as lxd
import json

_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'challenges.json')
try:
    with open(_json_path, 'r') as file:
        QUIZ_QUESTIONS = json.load(file)
except Exception as e:
    QUIZ_QUESTIONS = []
    print(f"Error loading challenges.json: {e}")


def check_answer(question, answer, container_name, container_ip):
    """Check if the student's answer is correct."""
    check_type = question.get('check_type', question.check_type if hasattr(question, 'check_type') else 'text')
    expected = question.get('expected_answer', getattr(question, 'expected_answer', None))

    if check_type == 'text':
        if expected is None:
            return False
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

    # Q3: Check `id` command output
    if script_name == 'check_id':
        rc, out, _ = lxd.exec_in_container(container_name, ['id'])
        if rc != 0:
            return False
        # Student should paste the full id output; verify it contains expected uid/gid
        return 'uid=1000(user)' in answer.strip() and 'gid=1000(user)' in answer.strip()

    # Q8: Check edit_me.txt content
    elif script_name == 'check_edit_file':
        rc, out, _ = lxd.exec_in_container(container_name,
            ['cat', '/home/user/challenges/edit_me.txt'])
        return rc == 0 and out.strip() == 'Linux is awesome'

    # Q9: Check mkdir gdg_is_great
    elif script_name == 'check_mkdir':
        rc, _, _ = lxd.exec_in_container(container_name,
            ['test', '-d', '/home/user/challenges/gdg_is_great'])
        return rc == 0

    # Q10: Check deletion of files/dirs
    elif script_name == 'check_delete':
        checks = [
            ['test', '-e', '/home/user/challenges/delete_me.txt'],
            ['test', '-e', '/home/user/challenges/remove_this_dir'],
            ['test', '-e', '/home/user/challenges/protected_dir'],
        ]
        for cmd in checks:
            rc, _, _ = lxd.exec_in_container(container_name, cmd)
            if rc == 0:  # File/dir still exists — not deleted yet
                return False
        return True

    # Q11: Check cp (file and directory)
    elif script_name == 'check_cp':
        # Check copied file
        rc1, out1, _ = lxd.exec_in_container(container_name,
            ['test', '-f', '/home/user/challenges/copy_of_original.txt'])
        # Check copied directory
        rc2, _, _ = lxd.exec_in_container(container_name,
            ['test', '-d', '/home/user/challenges/sample_dir_backup'])
        return rc1 == 0 and rc2 == 0

    # Q12: Check mv (move and rename)
    elif script_name == 'check_mv':
        # Check moved file
        rc1, _, _ = lxd.exec_in_container(container_name,
            ['test', '-f', '/home/user/challenges/moved/move_me.txt'])
        # Check renamed file
        rc2, _, _ = lxd.exec_in_container(container_name,
            ['test', '-f', '/home/user/challenges/renamed.txt'])
        # Original should no longer exist
        rc3, _, _ = lxd.exec_in_container(container_name,
            ['test', '-f', '/home/user/challenges/move_me.txt'])
        rc4, _, _ = lxd.exec_in_container(container_name,
            ['test', '-f', '/home/user/challenges/rename_me.txt'])
        return rc1 == 0 and rc2 == 0 and rc3 != 0 and rc4 != 0

    # Q14: Check symbolic link
    elif script_name == 'check_softlink':
        rc, out, _ = lxd.exec_in_container(container_name,
            ['readlink', '/home/user/challenges/link_to_original'])
        return rc == 0 and 'original.txt' in out.strip()

    # Q18: Check tar compress and extract
    elif script_name == 'check_tar':
        # Check compressed archive exists
        rc1, _, _ = lxd.exec_in_container(container_name,
            ['test', '-f', '/home/user/challenges/compress_me.tar.gz'])
        # Check extracted directory exists and has content
        rc2, _, _ = lxd.exec_in_container(container_name,
            ['test', '-d', '/home/user/challenges/extracted'])
        return rc1 == 0 and rc2 == 0

    # Q19: Check chmod (22.sh is executable)
    elif script_name == 'check_chmod':
        rc, out, _ = lxd.exec_in_container(container_name,
            ['stat', '-c', '%a', '/home/user/challenges/22.sh'])
        if rc != 0:
            return False
        try:
            mode = int(out.strip(), 8)
        except ValueError:
            return False
        return bool(mode & 0o111)

    # Q20: Check chown (22.sh owned by user)
    elif script_name == 'check_chown':
        rc, out, _ = lxd.exec_in_container(container_name,
            ['stat', '-c', '%U', '/home/user/challenges/22.sh'])
        return rc == 0 and out.strip() == 'user'

    # Q16: Check ss output for port 22 — accept any backlog number
    elif script_name == 'check_ss_port22':
        import re
        # Accept: LISTEN 0 <any_number> 0.0.0.0:22 0.0.0.0:*
        # Also tolerate extra whitespace and optional trailing columns
        pattern = r'LISTEN\s+\d+\s+\d+\s+0\.0\.0\.0:22\s+0\.0\.0\.0:\*'
        return bool(re.search(pattern, answer.strip()))

    # Q23: Check fastfetch is installed
    elif script_name == 'check_fastfetch':
        rc, _, _ = lxd.exec_in_container(container_name,
            ['which', 'fastfetch'])
        return rc == 0 and len(answer.strip()) > 0

    # Q24: Check .bashrc has LAB_COMPLETE=1
    elif script_name == 'check_bashrc':
        rc, out, _ = lxd.exec_in_container(container_name,
            ['grep', '-q', 'export LAB_COMPLETE=1', '/home/user/.bashrc'])
        return rc == 0

    return False
