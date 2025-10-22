* Примитивная уилита для backup'а по SSH

* Как использовать

1. Установить pyenv по этой инструкции `https://github.com/pyenv/pyenv?tab=readme-ov-file#installation`
2. Настроить локальное окружение для запуска
```bash
pyenv install 3.14.0
pyenv local 3.14.0
pip install poetry
poetry install
source .venv/bin/activate
```
3. Запустить скрипт
```bash
python src/main.py \
--hostname example.com \
--username user \
--shh_key_path /path/to/ssh/private/key \
--remote_path /path/to/directory/on/server \
--local_path /local/path/to/copy \
```
