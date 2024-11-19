import subprocess
from backup_file.file_path import get_file_path


def restore_postgres(backup_file):
    command = [
        'docker', 'exec', '-i', 'NTMO_kontrakt',
        'psql', '-U', 'admin_user', '-d', 'NTMO_database'
    ]
    with open(backup_file, 'r') as f:
        try:
            subprocess.run(command, stdin=f, check=True)
        except subprocess.CalledProcessError as e:
            print(f"{e.stderr.decode()}")


if __name__ == "__main__":
    restore_postgres(get_file_path('backup.sql'))
