import argparse
import contextlib
import datetime
import pathlib
import typing
import zoneinfo

import paramiko

import utils


@contextlib.contextmanager
def create_sftp_client(
    hostname: str,
    username: str,
    key_filename: str,
) -> typing.Generator[tuple[paramiko.SSHClient, paramiko.SFTPClient]]:
    """Создаёт SSH и SFTP клиенты."""

    with paramiko.SSHClient() as ssh_client:
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            hostname=hostname,
            username=username,
            key_filename=key_filename,
        )
        with ssh_client.open_sftp() as sftp_client:
            yield ssh_client, sftp_client


def get_local_path(local_path: str) -> str:
    """Возвращает путь директории, куда будут скопированы файлы."""

    filename = (
        datetime.datetime.now(tz=zoneinfo.ZoneInfo("Europe/Moscow"))
        .isoformat()
        .replace(":", "-")
    )
    return str(pathlib.Path(local_path, filename))


@utils.spinner(description="Discovering files to copy")
def get_files(
    ssh_client: paramiko.SSHClient,
    remote_path: str,
) -> list[str]:
    """Возвращает список относительный путей копируемых файлов."""

    command = f"cd {remote_path} && find . -type f"
    stdout: paramiko.ChannelFile = ssh_client.exec_command(command)[1]
    return [f for f in stdout.read().decode("utf-8").split("\n") if f]


@utils.spinner(description="Creating local directories")
def create_local_directories(
    local_path: str,
    files: list[str],
) -> None:
    """Создаёт директории, куда будут скопированы файлы."""

    try:
        # Создание корневого каталога для бэкапа.
        pathlib.Path(local_path).mkdir(parents=True)

        # Создание остальных подкаталогов.
        for file in files:
            directory = pathlib.Path(local_path, pathlib.Path(file).parent)
            directory.mkdir(parents=True, exist_ok=True)

    except OSError as error:
        print(error)
        return None


def copy(
    sftp_client: paramiko.SFTPClient,
    remote_path: str,
    local_path: str,
    files: list[str],
) -> None:
    """Копирует файлы из списка."""

    file: str

    for file in utils.progress(typing.cast("utils.IterableSized[str]", files)):
        try:
            sftp_client.get(
                remotepath=pathlib.Path(remote_path, file).as_posix(),
                localpath=str(pathlib.Path(local_path, file)),
            )

        except (OSError, FileNotFoundError) as error:
            print(error, file)
            break


def backup(args: argparse.Namespace) -> None:
    """Создаёт бэкап файлов."""

    local_path = get_local_path(local_path=args.local_path)

    with create_sftp_client(
        hostname=args.hostname,
        username=args.username,
        key_filename=args.ssh_key_path,
    ) as (ssh_client, sftp_client):

        files: list[str] = get_files(
            ssh_client=ssh_client,
            remote_path=args.remote_path,
        )

        create_local_directories(
            local_path=local_path,
            files=files,
        )

        copy(
            sftp_client=sftp_client,
            remote_path=args.remote_path,
            local_path=local_path,
            files=files,
        )

    print(f"\n{utils.Y}Finished{utils._} [{local_path}]")


parser = argparse.ArgumentParser(description="SSH backup utility")
parser.add_argument("--hostname", required=True, help="Remote host")
parser.add_argument("--username", required=True, help="Remote user")
parser.add_argument("--ssh_key_path", required=True, help="Path to SSH private key")
parser.add_argument("--remote_path", required=True, help="Remote directory path")
parser.add_argument("--local_path", required=True, help="Local backup path")

backup(args=parser.parse_args())
