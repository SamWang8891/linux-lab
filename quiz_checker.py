"""Quiz question definitions and automated checkers."""
import paramiko
import requests
import lxd_manager as lxd


QUIZ_QUESTIONS = [
    {
        'order': 1,
        'title': '我是誰？',
        'description': '請在你的機器上執行指令，找出目前登入的使用者名稱。\n\n提示：使用 `whoami` 和 `id` 指令。\n\n請輸入 `whoami` 的輸出結果。',
        'hint': '試試看在終端機輸入 whoami',
        'check_type': 'text',
        'expected_answer': 'user',
    },
    {
        'order': 2,
        'title': '列出檔案',
        'description': '請列出 `/home/user/challenges/` 目錄下的所有檔案（包含隱藏檔案）。\n\n提示：使用 `ls` 指令搭配適當的參數。\n\n請輸入隱藏檔案的名稱（以 `.` 開頭的那個）。',
        'hint': '試試 ls -la',
        'check_type': 'text',
        'expected_answer': '.secret_flag',
    },
    {
        'order': 3,
        'title': '尋找檔案',
        'description': '在你的機器某處藏了一個叫做 `hidden_treasure.txt` 的檔案。請找到它，並輸入檔案內容。\n\n提示：使用 `find` 指令。',
        'hint': 'find / -name "hidden_treasure.txt" 2>/dev/null',
        'check_type': 'script',
        'check_script': 'check_file_content',
    },
    {
        'order': 4,
        'title': '查看作業系統資訊',
        'description': '請找出你的機器正在執行的 Linux 發行版名稱和版本。\n\n提示：查看 `/etc/os-release`。\n\n請輸入 PRETTY_NAME 的值。',
        'hint': 'cat /etc/os-release',
        'check_type': 'text',
        'expected_answer': 'Debian GNU/Linux 12 (bookworm)',
    },
    {
        'order': 5,
        'title': '解壓縮檔案',
        'description': '在 `/home/user/challenges/` 有兩個壓縮檔：\n- `archive1.zip`\n- `archive2.tar.gz`\n\n請解壓縮這兩個檔案，並輸入兩個檔案內的 flag 用空格隔開。\n\n提示：使用 `unzip` 和 `tar -xvf`',
        'hint': 'unzip archive1.zip 和 tar -xvf archive2.tar.gz',
        'check_type': 'script',
        'check_script': 'check_unzip',
    },
    {
        'order': 6,
        'title': '執行程式',
        'description': '在 `/home/user/challenges/` 有一個檔案叫做 `run_me`。請設定它為可執行並執行它，輸入它顯示的 flag。\n\n提示：你需要先 `chmod +x` 它。',
        'hint': 'chmod +x run_me && ./run_me',
        'check_type': 'script',
        'check_script': 'check_executable',
    },
    {
        'order': 7,
        'title': '刪除檔案',
        'description': '請刪除 `/home/user/challenges/delete_me.txt` 這個檔案。\n\n完成後輸入 "done"。',
        'hint': 'rm /home/user/challenges/delete_me.txt',
        'check_type': 'script',
        'check_script': 'check_file_deleted',
    },
    {
        'order': 8,
        'title': '查看檔案權限',
        'description': '請查看 `/home/user/challenges/permission_check` 的檔案權限。\n\n請以數字格式輸入權限（例如：755）。',
        'hint': 'stat -c "%a" /home/user/challenges/permission_check',
        'check_type': 'script',
        'check_script': 'check_permission',
    },
    {
        'order': 9,
        'title': '編輯檔案',
        'description': '請使用 nano 或 vim 編輯 `/home/user/challenges/edit_me.txt`。\n\n將檔案內容改為：`Linux is awesome`\n\n完成後輸入 "done"。',
        'hint': 'nano /home/user/challenges/edit_me.txt',
        'check_type': 'script',
        'check_script': 'check_edit_file',
    },
    {
        'order': 10,
        'title': '修改 .bashrc',
        'description': '請編輯 `/home/user/.bashrc`，在最後一行加入：\n\n`export LAB_COMPLETE=1`\n\n然後重新載入它。完成後輸入 "done"。',
        'hint': 'echo \'export LAB_COMPLETE=1\' >> ~/.bashrc && source ~/.bashrc',
        'check_type': 'script',
        'check_script': 'check_bashrc',
    },
    {
        'order': 11,
        'title': '列出連接埠',
        'description': '請列出目前機器上所有正在監聽的 TCP 連接埠。\n\n提示：使用 `ss` 或 `netstat` 指令。\n\n請輸入 SSH 服務監聽的連接埠號碼。',
        'hint': 'ss -tlnp',
        'check_type': 'text',
        'expected_answer': '22',
    },
    {
        'order': 12,
        'title': '安裝並管理服務',
        'description': '請完成以下步驟：\n1. 使用 `apt` 安裝 nginx\n2. 使用 `systemctl start nginx` 啟動它\n3. 使用 `systemctl enable nginx` 設定開機自動啟動\n\n完成後輸入 "done"。系統會自動檢查你的 port 80 是否有回應。',
        'hint': 'sudo apt install -y nginx && sudo systemctl start nginx && sudo systemctl enable nginx',
        'check_type': 'http',
    },
    {
        'order': 13,
        'title': '安裝 .deb 套件',
        'description': '在 `/home/user/challenges/` 有一個 `fastfetch.deb` 檔案。\n\n請使用 `dpkg -i` 安裝它，然後執行 `fastfetch`。\n\n輸入 fastfetch 顯示的主機名稱（Host 欄位）。',
        'hint': 'sudo dpkg -i /home/user/challenges/fastfetch.deb && fastfetch',
        'check_type': 'script',
        'check_script': 'check_dpkg',
    },
    {
        'order': 14,
        'title': '更改密碼',
        'description': '請將 user 帳號的密碼從 `user` 改為 `linux-lab-2026`。\n\n完成後輸入 "done"。系統會透過 SSH 驗證你的新密碼。',
        'hint': 'passwd  （然後依照提示輸入舊密碼和新密碼）',
        'check_type': 'ssh',
    },
]


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
        # Check both flags exist
        rc1, out1, _ = lxd.exec_in_container(container_name,
            ['cat', '/home/user/challenges/flag1.txt'])
        rc2, out2, _ = lxd.exec_in_container(container_name,
            ['cat', '/home/user/challenges/flag2.txt'])
        if rc1 != 0 or rc2 != 0:
            return False
        expected = f"{out1.strip()} {out2.strip()}"
        return answer.strip() == expected

    elif script_name == 'check_executable':
        rc, out, _ = lxd.exec_in_container(container_name,
            ['bash', '-c', 'stat -c "%a" /home/user/challenges/run_me'])
        if rc != 0:
            return False
        perms = out.strip()
        # Must be executable
        if not (int(perms) % 10 >= 5 or int(perms) // 10 % 10 >= 5 or int(perms) // 100 >= 5):
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
