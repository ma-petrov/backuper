import argparse
import contextlib
import datetime
import logging
import pathlib
import stat
import typing
import zoneinfo

import paramiko

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s | %(message)s",
)
logger = logging.getLogger(__name__)

DIR_NAME_FORMAT = r"%d.%m.%Y_%H:%M:%S.%"


@contextlib.contextmanager
def create_sftp_client(
    hostname: str,
    username: str,
    key_filename: str,
) -> typing.Generator[paramiko.SFTPClient]:
    """Создаёт SFTP клиент"""

    with paramiko.SSHClient() as ssh_client:
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            hostname=hostname,
            username=username,
            key_filename=key_filename,
        )
        with ssh_client.open_sftp() as sftp_client:
            yield sftp_client


def get_local_path(local_path: str) -> str:
    """Возвращает путь директории, куда будут скопированы файлы"""

    now = datetime.datetime.now(tz=zoneinfo.ZoneInfo("Europe/Moscow"))
    return pathlib.Path(local_path, now.isoformat())


def copy_recursive(
    sftp_client: paramiko.SFTPClient,
    remote_path: str,
    local_path: str,
) -> None:
    """Рекурсивно копирует файлы и директории"""

    pathlib.Path(local_path).mkdir(parents=True, exist_ok=True)

    for item in sftp_client.listdir_attr(path=remote_path):
        remote = str(pathlib.Path(remote_path, item.filename))
        local = str(pathlib.Path(local_path, item.filename))

        if stat.S_ISDIR(item.st_mode):
            copy_recursive(
                sftp_client=sftp_client,
                remote_path=remote,
                local_path=local,
            )

        else:
            sftp_client.get(remotepath=remote, localpath=local)
            logger.info(f"Copied: {remote} -> {local}")


def backup(args: argparse.Namespace) -> None:
    """Создаёт бэкап файлов"""

    local_path = get_local_path(local_path=args.local_path)

    # Попытка создать каталог backup"а, если каталог уже существует или его
    # невозможно создать скрипт завершается.
    try:
        pathlib.Path(local_path).mkdir(parents=True)
    except OSError as error:
        logger.error(error)
        return None

    # Копирование файлов
    with create_sftp_client(
        hostname=args.hostname,
        username=args.username,
        key_filename=args.ssh_key_path,
    ) as sftp_client:
        copy_recursive(sftp_client, args.remote_path, local_path)

    logger.info(f"Backup created: {local_path}")


parser = argparse.ArgumentParser(description="SSH backup utility")
parser.add_argument("--hostname", required=True, help="Remote host")
parser.add_argument("--username", required=True, help="Remote user")
parser.add_argument("--ssh_key_path", required=True, help="Path to SSH private key")
parser.add_argument("--remote_path", required=True, help="Remote directory path")
parser.add_argument("--local_path", required=True, help="Local backup path")

backup(args=parser.parse_args())
