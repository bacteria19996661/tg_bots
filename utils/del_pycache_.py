import shutil
import pathlib

# Получаем путь к директории, где находится скрипт
script_dir = pathlib.Path(__file__).parent

# Определяем корневую папку проекта (на уровень выше)
project_root = script_dir.parent

# Ищем и удаляем все папки __pycache__ в корневой папке и всех подпапках
for cache_dir in project_root.rglob('__pycache__'):
    print(f"Удаляем: {cache_dir}")
    shutil.rmtree(cache_dir, ignore_errors=True)

print("Очистка завершена!")

# import shutil
# import pathlib
#
# for cache_dir in pathlib.Path('.').rglob('__pycache__'):
#     shutil.rmtree(cache_dir, ignore_errors=True)

# import pathlib
#
# for cache_dir in pathlib.Path('.').rglob('__pycache__'):
#     if cache_dir.is_dir():
#         for item in cache_dir.iterdir():
#             item.unlink()
#         cache_dir.rmdir()
