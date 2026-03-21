#!/bin/bash
# Reset challenge files to initial state
# Called by the web app's reset button
set -e

CHAL_DIR="/home/user/challenges"

# Remove everything in challenges dir
rm -rf "$CHAL_DIR"
mkdir -p "$CHAL_DIR"
mkdir -p /home/user/documents

# Q6: Hidden file
echo "FLAG{ls_master}" > "$CHAL_DIR/.secret_flag"

# Q8: File to edit
echo "Change this text" > "$CHAL_DIR/edit_me.txt"

# Q10: Files/dirs to delete
echo "Delete this file!" > "$CHAL_DIR/delete_me.txt"
mkdir -p "$CHAL_DIR/remove_this_dir"
echo "remove me" > "$CHAL_DIR/remove_this_dir/file.txt"
mkdir -p "$CHAL_DIR/protected_dir"
echo "protected" > "$CHAL_DIR/protected_dir/secret.txt"
chown -R root:root "$CHAL_DIR/protected_dir"

# Q11: Files/dirs to copy
echo "I am the original file." > "$CHAL_DIR/original.txt"
mkdir -p "$CHAL_DIR/sample_dir"
echo "sample file 1" > "$CHAL_DIR/sample_dir/file1.txt"
echo "sample file 2" > "$CHAL_DIR/sample_dir/file2.txt"

# Q12: Files to move/rename
echo "Move me to another location!" > "$CHAL_DIR/move_me.txt"
echo "Rename me to something else!" > "$CHAL_DIR/rename_me.txt"
mkdir -p "$CHAL_DIR/moved"

# Q13: Hidden treasure
mkdir -p /var/lib
echo "FLAG{treasure_found}" > /var/lib/hidden_treasure.txt

# Q18: Compress/extract
mkdir -p "$CHAL_DIR/compress_me"
echo "file to compress 1" > "$CHAL_DIR/compress_me/data1.txt"
echo "file to compress 2" > "$CHAL_DIR/compress_me/data2.txt"
mkdir -p /tmp/extract_content
echo "extracted file 1" > /tmp/extract_content/extracted1.txt
echo "extracted file 2" > /tmp/extract_content/extracted2.txt
(cd /tmp && tar czf "$CHAL_DIR/extract_me.tar.gz" extract_content/)
rm -rf /tmp/extract_content

# Q19-21: Script file (root-owned, not executable)
cat > "$CHAL_DIR/22.sh" << 'SCRIPT'
#!/bin/bash
echo "This is GDG NTUST."
SCRIPT
chmod 644 "$CHAL_DIR/22.sh"
chown root:root "$CHAL_DIR/22.sh"

# Set ownership
chown user:user "$CHAL_DIR"
chown user:user "$CHAL_DIR/.secret_flag"
chown user:user "$CHAL_DIR/edit_me.txt"
chown user:user "$CHAL_DIR/delete_me.txt"
chown -R user:user "$CHAL_DIR/remove_this_dir"
chown user:user "$CHAL_DIR/original.txt"
chown -R user:user "$CHAL_DIR/sample_dir"
chown user:user "$CHAL_DIR/move_me.txt"
chown user:user "$CHAL_DIR/rename_me.txt"
chown -R user:user "$CHAL_DIR/moved"
chown -R user:user "$CHAL_DIR/compress_me"
chown user:user "$CHAL_DIR/extract_me.tar.gz"

# Reset .bashrc (remove LAB_COMPLETE if present)
sed -i '/export LAB_COMPLETE=1/d' /home/user/.bashrc

# Remove fastfetch if installed (Q23 challenge)
dpkg -r fastfetch 2>/dev/null || true

# Reset user password back to 'user' (Q4 challenge)
echo "user:user" | chpasswd

echo "=== Challenges reset ==="
