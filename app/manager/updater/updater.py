import zipfile
from pathlib import Path

import git
from loguru import logger


def handle_path(path: Path | str) -> Path:
    if isinstance(path, str):
        return Path(path)
    elif isinstance(path, Path):
        return path
    else:
        raise ValueError(f"Expected pathlib.Path or str, but got {type(path)}")


class VersionControl:
    def __init__(self):
        self._update_source = None
        self._target = None
        self._repo = None
        self._local_path = None
        self._archive_path = None
        self._repo_url = None

    def update_from(self, target: str, update_source: Path | str, parent_folder: Path | str) -> bool:
        """
        Updates the repository from `update_source` to `target`
        """
        parent_folder = handle_path(parent_folder)

        self._target = target
        self._update_source = handle_path(update_source)

        if self._is_url(self._update_source):
            self._repo_url = str(self._update_source)
            self._archive_path = None
        else:
            self._archive_path = self._update_source
            self._repo_url = None

        self._local_path = parent_folder / (self._archive_path.stem if self._archive_path else self._target)

        try:
            if self._archive_path and not self._local_path.exists():
                if not self._extract_archive():
                    return False

            self._init_repo()

            if self._repo_url:
                return self._clone_or_update()
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении из источника: {e}")
            return False

    def _is_url(self, path: Path | str) -> bool:
        return isinstance(path, str) and (path.startswith('http://') or path.startswith('https://') or path.startswith('git@'))

    def get_untracked_files(self, include_ignored: bool = False):
        if not self._repo:
            logger.warning('No repository initialized.')
            return []

        if include_ignored:
            ignored_untracked = self._repo.git.ls_files('--others', '--ignored', '--exclude-standard').splitlines()
            return [self._decode_utf8_escapes(file) for file in ignored_untracked]
        return self._repo.untracked_files

    @staticmethod
    def _decode_utf8_escapes(file: str) -> str:
        return bytes(file, "utf-8").decode("unicode_escape").encode("latin1").decode("utf-8")

    def _clone_or_update(self, clean_untracked: bool = False) -> bool:
        if self._local_path.exists() and (self._local_path / ".git").exists():
            if not self._repo:
                self._init_repo()

            logger.info(f"Repository '{self._local_path.name}' уже клонирован. Проверка обновлений...")
            self._repo.remotes.origin.fetch()

            if clean_untracked:
                logger.info("Очистка неотслеживаемых файлов...")
                self._repo.git.clean('-fd')

            if self._repo.is_dirty(untracked_files=False) or self._repo.index.diff(None):
                logger.info("Локальный репозиторий имеет изменения. Сброс до удаленного состояния.")
                self._repo.git.reset('--hard')

            self._repo.remotes.origin.pull()
            logger.info("Репозиторий обновлен до последней версии.")
        else:
            logger.info(f"Клонирование репозитория '{self._repo_url}' в '{self._local_path}'...")
            self._repo = git.Repo.clone_from(self._repo_url, self._local_path)
            logger.info(f"Репозиторий '{self._local_path.name}' успешно клонирован.")

        return True

    def check_integrity(self) -> bool:
        return self._clone_or_update()

    def _extract_archive(self) -> bool:
        if not self._archive_path.exists():
            logger.error(f"Архив '{self._archive_path}' не существует.")
            return False

        self._local_path.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(self._archive_path) as file:
                file.extractall(self._local_path.parent)
            logger.info(f"Архив '{self._archive_path.name}' успешно извлечен.")
            return True
        except zipfile.BadZipFile as e:
            logger.error(f"Не удалось извлечь архив: {e}")
            return False

    def _init_repo(self) -> bool:
        if not self._local_path.is_dir() or not self._local_path.exists():
            logger.error(f"Директория репозитория '{self._local_path}' не существует.")
            return False

        try:
            self._repo = git.Repo(self._local_path)
            logger.info(f"Репозиторий инициализирован по пути '{self._local_path}'.")
            return True
        except git.exc.InvalidGitRepositoryError:
            logger.error(f"Неверный Git репозиторий по пути '{self._local_path}'.")
            return False

    def update_from_file(self, archive_path: Path | str) -> bool:
        archive_path = handle_path(archive_path)
        if not archive_path.exists():
            logger.error(f"Архив '{archive_path}' не существует.")
            return False

        return self._extract_archive()

    def reset_to_head(self):
        if self._repo:
            self._clone_or_update(clean_untracked=True)

    def get_status(self):
        status = {
            'repository_exists': self._local_path.exists(),
            'git_initialized': (self._local_path / ".git").exists() if self._local_path else False,
            'repo_dirty': self._repo.is_dirty() if self._repo else False,
            'untracked_files': self.get_untracked_files()
        }
        logger.info(f"Статус репозитория: {status}")
        return status
