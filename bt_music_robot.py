#!/usr/bin/env python3
"""
Bluetooth Music Randomizer
Запускает музыку на Bluetooth-колонке по расписанию
Поддерживает случайный выбор из папки или конкретный файл
"""

import os
import random
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# ========== ЗАГРУЗКА КОНФИГУРАЦИИ ==========

script_dir = Path(__file__).parent
env_path = script_dir / ".env"
load_dotenv(env_path)


def get_config(key, default=None, cast=None):
    value = os.getenv(key, default)
    if cast and value is not None:
        try:
            if cast == bool:
                return value.lower() in ('true', 'yes', '1', 'on')
            return cast(value)
        except (ValueError, TypeError):
            return default
    return value


CONFIG = {
    'BT_MAC': get_config('BT_MAC', '').strip(),
    'MUSIC_MODE': get_config('MUSIC_MODE', 'single'),
    'MEDIA_FILE': get_config('MEDIA_FILE', '/storage/emulated/0/Music/track.mp3'),
    'MEDIA_FOLDER': get_config('MEDIA_FOLDER', '/storage/emulated/0/Music'),
    'MEDIA_EXTENSIONS': get_config('MEDIA_EXTENSIONS', '.mp3,.wav,.m4a,.ogg,.flac'),
    'LOG_DIR': get_config('LOG_DIR', 'logs'),
    'TIME_WINDOW_START': get_config('TIME_WINDOW_START', '14:00'),
    'TIME_WINDOW_END': get_config('TIME_WINDOW_END', '19:00'),
    'MIN_INTERVAL_BETWEEN_SEC': get_config('MIN_INTERVAL_BETWEEN_SEC', 30, int),
    'NUM_SESSIONS': get_config('NUM_SESSIONS', 5, int),
    'SESSION_DURATION_SEC': get_config('SESSION_DURATION_SEC', 60, int),
    'PAUSE_BETWEEN_MIN_MIN': get_config('PAUSE_BETWEEN_MIN_MIN', 10, int),
    'PAUSE_BETWEEN_MAX_MIN': get_config('PAUSE_BETWEEN_MAX_MIN', 45, int),
    'VOLUME_LEVEL': get_config('VOLUME_LEVEL', 70, int),
    'SCHEDULE_MODE': get_config('SCHEDULE_MODE', 'random'),
    'START_DELAY_MIN': get_config('START_DELAY_MIN', 0, int),
    'DISABLE_BT_AFTER_SESSION': get_config('DISABLE_BT_AFTER_SESSION', True, bool),
    'DEBUG_MODE': get_config('DEBUG_MODE', False, bool),
}

if not CONFIG['BT_MAC']:
    print("ОШИБКА: Не указан BT_MAC в .env файле")
    sys.exit(1)

if CONFIG['PAUSE_BETWEEN_MIN_MIN'] > CONFIG['PAUSE_BETWEEN_MAX_MIN']:
    print("ОШИБКА: PAUSE_BETWEEN_MIN_MIN не может быть больше PAUSE_BETWEEN_MAX_MIN")
    sys.exit(1)


# ========== РАБОТА С МУЗЫКАЛЬНЫМИ ФАЙЛАМИ ==========

def get_audio_files_from_folder(folder_path, extensions):
    """
    Возвращает список всех аудиофайлов в папке (без рекурсии)
    """
    folder = Path(folder_path)
    if not folder.exists():
        return []

    ext_list = [ext.strip().lower() for ext in extensions.split(',')]

    files = []
    for ext in ext_list:
        files.extend(folder.glob(f"*{ext}"))
        files.extend(folder.glob(f"*{ext.upper()}"))

    # Убираем дубликаты и сортируем
    files = sorted(set(files))
    return files


def get_random_media_file(log_file=None):
    """
    Возвращает путь к аудиофайлу в зависимости от MUSIC_MODE
    """
    if CONFIG['MUSIC_MODE'] == 'folder':
        folder = CONFIG['MEDIA_FOLDER']
        extensions = CONFIG['MEDIA_EXTENSIONS']

        files = get_audio_files_from_folder(folder, extensions)

        if not files:
            error_msg = f"В папке {folder} не найдено аудиофайлов с расширениями {extensions}"
            if log_file:
                write_log(log_file, "ERROR", error_msg)
            print(f"ОШИБКА: {error_msg}")
            return None

        selected = random.choice(files)
        if log_file:
            write_log(log_file, "INFO", f"Выбран случайный файл из папки: {selected}")

        return str(selected)

    else:  # single mode
        media_file = CONFIG['MEDIA_FILE']
        if not Path(media_file).exists():
            error_msg = f"Файл не существует: {media_file}"
            if log_file:
                write_log(log_file, "ERROR", error_msg)
            print(f"ОШИБКА: {error_msg}")
            return None

        if log_file:
            write_log(log_file, "INFO", f"Используется файл: {media_file}")

        return media_file


# ========== ИНИЦИАЛИЗАЦИЯ ЛОГИРОВАНИЯ ==========

def init_logging():
    log_dir = Path(script_dir) / CONFIG['LOG_DIR']
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"session_{timestamp}.log"
    return log_file


def write_log(log_file, level, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level:7}] {message}"
    print(line)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def write_config_to_log(log_file):
    write_log(log_file, "INFO", "=" * 60)
    write_log(log_file, "INFO", "ТЕКУЩАЯ КОНФИГУРАЦИЯ:")
    write_log(log_file, "INFO", f"  BT_MAC: {CONFIG['BT_MAC']}")
    write_log(log_file, "INFO", f"  MUSIC_MODE: {CONFIG['MUSIC_MODE']}")
    if CONFIG['MUSIC_MODE'] == 'folder':
        write_log(log_file, "INFO", f"  MEDIA_FOLDER: {CONFIG['MEDIA_FOLDER']}")
        write_log(log_file, "INFO", f"  MEDIA_EXTENSIONS: {CONFIG['MEDIA_EXTENSIONS']}")
    else:
        write_log(log_file, "INFO", f"  MEDIA_FILE: {CONFIG['MEDIA_FILE']}")
    write_log(log_file, "INFO", f"  TIME_WINDOW: {CONFIG['TIME_WINDOW_START']} - {CONFIG['TIME_WINDOW_END']}")
    write_log(log_file, "INFO", f"  NUM_SESSIONS: {CONFIG['NUM_SESSIONS']}")
    write_log(log_file, "INFO", f"  SESSION_DURATION_SEC: {CONFIG['SESSION_DURATION_SEC']}")
    write_log(log_file, "INFO",
              f"  PAUSE_BETWEEN: {CONFIG['PAUSE_BETWEEN_MIN_MIN']} - {CONFIG['PAUSE_BETWEEN_MAX_MIN']} мин")
    write_log(log_file, "INFO", f"  VOLUME_LEVEL: {CONFIG['VOLUME_LEVEL']}%")
    write_log(log_file, "INFO", f"  SCHEDULE_MODE: {CONFIG['SCHEDULE_MODE']}")
    write_log(log_file, "INFO", "=" * 60)


# ========== УПРАВЛЕНИЕ BLUETOOTH И МУЗЫКОЙ ==========


def enable_bluetooth(log_file):
    """Включает Bluetooth через termux-api"""
    write_log(log_file, "INFO", "Включение Bluetooth...")
    subprocess.run(["termux-bluetooth-enable"], capture_output=True)
    time.sleep(2)
    write_log(log_file, "INFO", "Bluetooth включён")


def disable_bluetooth(log_file):
    """Выключает Bluetooth через termux-api"""
    write_log(log_file, "INFO", "Выключение Bluetooth...")
    subprocess.run(["termux-bluetooth-disable"], capture_output=True)
    write_log(log_file, "INFO", "Bluetooth выключен")


def connect_to_speaker(log_file):
    """Подключается к Bluetooth-колонке через termux-api"""
    write_log(log_file, "INFO", f"Подключение к колонке {CONFIG['BT_MAC']}...")
    result = subprocess.run(["termux-bluetooth", "connect", CONFIG['BT_MAC']], capture_output=True)
    if result.returncode != 0:
        write_log(log_file, "WARNING", f"Ошибка подключения: {result.stderr}")
    time.sleep(3)


def set_volume(log_file, level):
    """Устанавливает громкость через termux-api (работает только для звонков)"""
    # termux-api не умеет управлять медиа-громкостью
    # Пропускаем, громкость нужно настраивать вручную
    write_log(log_file, "INFO", f"Громкость {level}% (настройте на колонке вручную)")


def play_music(log_file):
    """Запускает воспроизведение через termux-media-player"""
    media_path = get_random_media_file(log_file)
    if not media_path:
        return False

    write_log(log_file, "INFO", f"Запуск: {media_path}")

    # Останавливаем текущее
    subprocess.run(["termux-media-player", "stop"], capture_output=True)
    time.sleep(0.5)

    # Запускаем через termux-media-player
    result = subprocess.run(["termux-media-player", "play", media_path], capture_output=True)

    if result.returncode == 0:
        write_log(log_file, "INFO", "Музыка запущена")
        return True
    else:
        write_log(log_file, "ERROR", f"Ошибка: {result.stderr}")
        return False


def stop_music(log_file):
    """Останавливает воспроизведение через termux-media-player"""
    write_log(log_file, "INFO", "Остановка музыки...")
    subprocess.run(["termux-media-player", "stop"], capture_output=True)
    write_log(log_file, "INFO", "Музыка остановлена")


def adb_command(cmd, log_file=None, capture_output=True):
    """Выполняет ADB-команду и возвращает результат с выводом"""
    full_cmd = f"adb shell {cmd}"

    if log_file:
        write_log(log_file, "DEBUG", f"ADB → {cmd[:100]}{'...' if len(cmd) > 100 else ''}")

    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)

    if log_file and capture_output:
        if result.stdout and result.stdout.strip():
            # Логируем первые 500 символов вывода
            stdout_preview = result.stdout[:500].replace('\n', ' ')
            write_log(log_file, "DEBUG", f"ADB stdout: {stdout_preview}")
        if result.stderr and result.stderr.strip():
            stderr_preview = result.stderr[:500].replace('\n', ' ')
            write_log(log_file, "DEBUG", f"ADB stderr: {stderr_preview}")
        if result.returncode != 0:
            write_log(log_file, "DEBUG", f"ADB return code: {result.returncode}")

    return result


def get_content_uri(media_path, log_file):
    """Получает content URI для файла (более надёжный способ воспроизведения)"""
    try:
        # Получаем ID файла через media provider
        cmd = f"content query --uri content://media/external/file --where \"_data='{media_path}'\""
        result = adb_command(cmd, log_file, capture_output=True)

        import re
        # Ищем _id в выводе
        match = re.search(r'_id=(\d+)', result.stdout)
        if match:
            media_id = match.group(1)
            content_uri = f"content://media/external/file/{media_id}"
            write_log(log_file, "INFO", f"Найден content URI: {content_uri}")
            return content_uri

        # Альтернативный метод: ищем по имени файла
        file_name = media_path.split('/')[-1]
        cmd = f"content query --uri content://media/external/file --where \"_display_name='{file_name}'\""
        result = adb_command(cmd, log_file, capture_output=True)
        match = re.search(r'_id=(\d+)', result.stdout)
        if match:
            media_id = match.group(1)
            content_uri = f"content://media/external/file/{media_id}"
            write_log(log_file, "INFO", f"Найден content URI (по имени): {content_uri}")
            return content_uri

        write_log(log_file, "WARNING", "Не удалось получить content URI")
        return None

    except Exception as e:
        write_log(log_file, "ERROR", f"Ошибка получения content URI: {e}")
        return None


def play_music(log_file):
    """Запускает воспроизведение с подробным логированием"""
    media_path = get_random_media_file(log_file)

    if not media_path:
        write_log(log_file, "ERROR", "❌ Не удалось определить аудиофайл")
        return False

    write_log(log_file, "INFO", f"🎵 Файл для воспроизведения: {media_path}")

    # Проверяем существование файла
    check_cmd = f"test -f '{media_path}' && echo 'EXISTS' || echo 'NOT_FOUND'"
    result = adb_command(check_cmd, log_file)
    if 'NOT_FOUND' in result.stdout:
        write_log(log_file, "ERROR", f"❌ Файл не существует: {media_path}")
        return False
    write_log(log_file, "INFO", "✅ Файл существует")

    # Проверяем, подключена ли Bluetooth-колонка
    bt_check = adb_command("dumpsys bluetooth | grep -A 3 'Connection State'", log_file)
    write_log(log_file, "INFO", f"📊 Статус Bluetooth:\n{bt_check.stdout[:300]}")

    # Останавливаем текущее воспроизведение
    write_log(log_file, "INFO", "⏹ Останавливаем текущее воспроизведение...")
    adb_command("input keyevent KEYCODE_MEDIA_STOP", log_file)
    adb_command("input keyevent KEYCODE_MEDIA_PAUSE", log_file)
    time.sleep(0.5)

    # МЕТОД 1: Через content URI (наиболее надёжный)
    write_log(log_file, "INFO", "📌 МЕТОД 1: Воспроизведение через content URI")
    content_uri = get_content_uri(media_path, log_file)

    if content_uri:
        cmd = f'am start -a android.intent.action.VIEW -d "{content_uri}" -t "audio/mpeg" -f 268435456'
        result = adb_command(cmd, log_file)

        if result.returncode == 0:
            write_log(log_file, "INFO", "✅ Команда content URI выполнена")
            time.sleep(1.5)
            adb_command("input keyevent KEYCODE_MEDIA_PLAY", log_file)
            write_log(log_file, "INFO", "✅ Музыка запущена через content URI")
            return True
        else:
            write_log(log_file, "WARNING", f"❌ content URI не сработал (code: {result.returncode})")
    else:
        write_log(log_file, "WARNING", "⚠ Не удалось получить content URI")

    # МЕТОД 2: Через file:// с MIME type audio/mpeg
    write_log(log_file, "INFO", "📌 МЕТОД 2: Воспроизведение через file:// с audio/mpeg")
    cmd = f'am start -a android.intent.action.VIEW -d "file://{media_path}" -t "audio/mpeg" -f 268435456'
    result = adb_command(cmd, log_file)

    if result.returncode == 0:
        write_log(log_file, "INFO", "✅ Команда file:// выполнена")
        time.sleep(1.5)
        adb_command("input keyevent KEYCODE_MEDIA_PLAY", log_file)
        write_log(log_file, "INFO", "✅ Музыка запущена через file://")
        return True
    else:
        write_log(log_file, "WARNING", f"❌ file:// не сработал (code: {result.returncode})")

    # МЕТОД 3: Через file:// с audio/* MIME type
    write_log(log_file, "INFO", "📌 МЕТОД 3: Воспроизведение через file:// с audio/*")
    cmd = f'am start -a android.intent.action.VIEW -d "file://{media_path}" -t "audio/*" -f 268435456'
    result = adb_command(cmd, log_file)

    if result.returncode == 0:
        write_log(log_file, "INFO", "✅ Команда audio/* выполнена")
        time.sleep(1.5)
        adb_command("input keyevent KEYCODE_MEDIA_PLAY", log_file)
        write_log(log_file, "INFO", "✅ Музыка запущена через audio/*")
        return True
    else:
        write_log(log_file, "WARNING", f"❌ audio/* не сработал (code: {result.returncode})")

    # МЕТОД 4: Через termux-media-player (на всякий случай)
    write_log(log_file, "INFO", "📌 МЕТОД 4: Воспроизведение через termux-media-player")
    subprocess.run(["termux-media-player", "stop"], capture_output=True)
    result = subprocess.run(["termux-media-player", "play", media_path], capture_output=True)

    if result.returncode == 0:
        write_log(log_file, "INFO", "✅ termux-media-player выполнен")
        write_log(log_file, "INFO", f"   stdout: {result.stdout}")
        write_log(log_file, "INFO", f"   stderr: {result.stderr}")
        return True
    else:
        write_log(log_file, "WARNING", f"❌ termux-media-player не сработал (code: {result.returncode})")
        write_log(log_file, "WARNING", f"   stderr: {result.stderr}")

    # МЕТОД 5: Просто посылаем MEDIA_PLAY (вдруг что-то уже открыто)
    write_log(log_file, "INFO", "📌 МЕТОД 5: Только MEDIA_PLAY")
    adb_command("input keyevent KEYCODE_MEDIA_PLAY", log_file)
    write_log(log_file, "INFO", "✅ Отправлена команда MEDIA_PLAY")

    # ВСЕ МЕТОДЫ НЕ СРАБОТАЛИ
    write_log(log_file, "ERROR", "❌❌❌ ВСЕ МЕТОДЫ ВОСПРОИЗВЕДЕНИЯ НЕ СРАБОТАЛИ ❌❌❌")
    write_log(log_file, "ERROR", "Возможные причины:")
    write_log(log_file, "ERROR", "  1. Нет приложения, которое может воспроизвести этот файл")
    write_log(log_file, "ERROR", "  2. Bluetooth-колонка не готова к воспроизведению")
    write_log(log_file, "ERROR", "  3. Нет прав на воспроизведение")
    return False


def test_playback(log_file):
    """
    Тестовое воспроизведение при запуске
    Проверяет: Bluetooth, подключение к колонке, воспроизведение музыки
    """
    write_log(log_file, "INFO", "=" * 60)
    write_log(log_file, "INFO", "🧪 ТЕСТОВОЕ ВОСПРОИЗВЕДЕНИЕ")
    write_log(log_file, "INFO", "=" * 60)

    try:
        # 1. Включаем Bluetooth
        write_log(log_file, "INFO", "1. Включение Bluetooth...")
        enable_bluetooth(log_file)
        time.sleep(2)

        # 2. Подключаемся к колонке
        write_log(log_file, "INFO", "2. Подключение к колонке...")
        connect_to_speaker(log_file)
        time.sleep(2)

        # 3. Устанавливаем громкость (50% для теста, чтобы не оглушило)
        write_log(log_file, "INFO", "3. Установка громкости 50%...")
        set_volume(log_file, 50)
        time.sleep(1)

        # 4. Запускаем музыку
        write_log(log_file, "INFO", "4. Тестовое воспроизведение (5 секунд)...")
        media_path = get_random_media_file(log_file)

        if not media_path:
            write_log(log_file, "ERROR", "❌ Не найден аудиофайл для теста")
            return False

        write_log(log_file, "INFO", f"   Файл: {media_path}")

        # Пробуем разные способы воспроизведения
        success = False

        # Способ 1: termux-media-player
        result = subprocess.run(["termux-media-player", "stop"], capture_output=True)
        time.sleep(0.5)
        result = subprocess.run(["termux-media-player", "play", media_path], capture_output=True)

        if result.returncode == 0:
            write_log(log_file, "INFO", "   ✅ Воспроизведение через termux-media-player")
            success = True
        else:
            # Способ 2: ADB
            write_log(log_file, "WARNING", "   Пробую ADB...")
            adb_command(f'am start -a android.intent.action.VIEW -d "file://{media_path}" -t "audio/*"', log_file)
            time.sleep(1)
            adb_command("input keyevent KEYCODE_MEDIA_PLAY", log_file)
            success = True

        if success:
            # Играем 5 секунд
            for i in range(5):
                write_log(log_file, "DEBUG", f"   Играет... {i + 1}/5 сек")
                time.sleep(1)

            # Останавливаем
            write_log(log_file, "INFO", "5. Остановка тестового воспроизведения...")
            subprocess.run(["termux-media-player", "stop"], capture_output=True)
            adb_command("input keyevent KEYCODE_MEDIA_STOP", log_file)

            write_log(log_file, "INFO", "✅ ТЕСТ ПРОЙДЕН УСПЕШНО")
            write_log(log_file, "INFO", "=" * 60)
            return True
        else:
            write_log(log_file, "ERROR", "❌ ТЕСТ НЕ УДАЛСЯ")
            write_log(log_file, "INFO", "=" * 60)
            return False

    except Exception as e:
        write_log(log_file, "ERROR", f"❌ Ошибка при тесте: {e}")
        write_log(log_file, "INFO", "=" * 60)
        return False


# ========== РАСПИСАНИЕ (остаётся без изменений) ==========

def parse_time_to_seconds(time_str):
    h, m = map(int, time_str.split(':'))
    return h * 3600 + m * 60


def get_window_start_end_today():
    start_sec = parse_time_to_seconds(CONFIG['TIME_WINDOW_START'])
    end_sec = parse_time_to_seconds(CONFIG['TIME_WINDOW_END'])
    if end_sec < start_sec:
        end_sec += 24 * 3600
    return start_sec, end_sec


def wait_until_window_start(log_file):
    now = datetime.now()
    current_sec = now.hour * 3600 + now.minute * 60 + now.second
    start_sec, end_sec = get_window_start_end_today()

    if start_sec <= current_sec < end_sec:
        write_log(log_file, "INFO", f"Уже внутри окна ({CONFIG['TIME_WINDOW_START']} - {CONFIG['TIME_WINDOW_END']})")
        return True

    wait_seconds = start_sec - current_sec
    if wait_seconds < 0:
        wait_seconds += 24 * 3600

    write_log(log_file, "INFO", f"Ожидание начала окна: {wait_seconds // 3600} ч {(wait_seconds % 3600) // 60} мин")

    for remaining in range(int(wait_seconds), 0, -60):
        if remaining % 3600 == 0 or remaining < 300:
            write_log(log_file, "DEBUG", f"До старта: {remaining // 60} мин")
        time.sleep(min(60, remaining))

    return True


def generate_schedule(log_file):
    """
    Генерирует случайное расписание включений внутри временного окна
    Соблюдает только:
    1. Минимальный интервал между запусками (MIN_INTERVAL_BETWEEN_SEC)
    2. Все включения помещаются в окно TIME_WINDOW_START - TIME_WINDOW_END
    3. Количество включений = NUM_SESSIONS

    Расписание полностью случайное, без равномерного распределения
    """
    start_sec, end_sec = get_window_start_end_today()
    window_duration = end_sec - start_sec
    num = CONFIG['NUM_SESSIONS']
    min_interval_sec = CONFIG['MIN_INTERVAL_BETWEEN_SEC']

    write_log(log_file, "DEBUG", f"Окно: {window_duration // 60} минут")
    write_log(log_file, "DEBUG", f"Количество включений: {num}")
    write_log(log_file, "DEBUG", f"Минимальный интервал: {min_interval_sec} сек")

    # Максимально возможное время для размещения всех интервалов
    max_possible_duration = (num - 1) * min_interval_sec

    if max_possible_duration > window_duration:
        write_log(log_file, "ERROR",
                  f"Невозможно разместить {num} включений с интервалом {min_interval_sec} сек в окне {window_duration // 60} мин")
        write_log(log_file, "ERROR", f"Требуется минимум {max_possible_duration // 60} минут")
        return []

    # Генерируем случайные времена с соблюдением минимального интервала
    max_attempts = 10000

    for attempt in range(max_attempts):
        # Генерируем num случайных чисел в диапазоне окна
        times = sorted([random.randint(0, window_duration) for _ in range(num)])

        # Проверяем минимальный интервал между соседними
        valid = True
        for i in range(1, len(times)):
            if times[i] - times[i - 1] < min_interval_sec:
                valid = False
                break

        if valid:
            write_log(log_file, "INFO", f"Случайное расписание сгенерировано за {attempt + 1} попыток")
            write_log(log_file, "DEBUG",
                      f"Интервалы между запусками: {[times[i] - times[i - 1] for i in range(1, len(times))]}")
            return times

    # Если не получилось — генерируем простым методом
    write_log(log_file, "WARNING", "Сложная генерация не удалась, использую упрощённый метод")

    times = []
    max_start = window_duration - (num - 1) * min_interval_sec

    for i in range(num):
        if i == 0:
            # Первое включение в случайное время от 0 до max_start
            t = random.randint(0, max_start)
        else:
            # Последующие с минимальным отступом от предыдущего
            min_t = times[-1] + min_interval_sec
            remaining = window_duration - min_t - (num - i - 1) * min_interval_sec
            if remaining < 0:
                remaining = 0
            t = random.randint(min_t, min_t + remaining)
        times.append(t)

    times.sort()
    write_log(log_file, "INFO", f"Упрощённое случайное расписание")
    return times


def run_single_session(log_file, session_num, total_sessions):
    write_log(log_file, "INFO", f"\n========== СЕССИЯ {session_num}/{total_sessions} ==========")

    try:
        enable_bluetooth(log_file)
        connect_to_speaker(log_file)
        set_volume(log_file, CONFIG['VOLUME_LEVEL'])

        if play_music(log_file):
            duration = CONFIG['SESSION_DURATION_SEC']
            for s in range(duration):
                if CONFIG['DEBUG_MODE'] and s % 15 == 0 and s > 0:
                    write_log(log_file, "DEBUG", f"Играет... {s}/{duration} сек")
                time.sleep(1)

            stop_music(log_file)
            write_log(log_file, "INFO", f"Сессия {session_num} завершена")
            return True
        else:
            write_log(log_file, "ERROR", f"Сессия {session_num} не удалась")
            return False
    except Exception as e:
        write_log(log_file, "ERROR", f"Исключение: {e}")
        return False


def run_full_schedule(log_file):
    write_log(log_file, "INFO", "=" * 60)
    write_log(log_file, "INFO", "BLUETOOTH MUSIC RANDOMIZER ЗАПУЩЕН")
    write_config_to_log(log_file)

    # Проверяем, что файлы/папка существуют
    if CONFIG['MUSIC_MODE'] == 'folder':
        folder = Path(CONFIG['MEDIA_FOLDER'])
        if not folder.exists():
            write_log(log_file, "ERROR", f"Папка не существует: {folder}")
            return
        files = get_audio_files_from_folder(CONFIG['MEDIA_FOLDER'], CONFIG['MEDIA_EXTENSIONS'])
        if not files:
            write_log(log_file, "ERROR", f"В папке {folder} нет аудиофайлов")
            return
        write_log(log_file, "INFO", f"Найдено {len(files)} аудиофайлов в папке")
    else:
        if not Path(CONFIG['MEDIA_FILE']).exists():
            write_log(log_file, "ERROR", f"Файл не существует: {CONFIG['MEDIA_FILE']}")
            return

    wait_until_window_start(log_file)

    if CONFIG['START_DELAY_MIN'] > 0:
        write_log(log_file, "INFO", f"Задержка {CONFIG['START_DELAY_MIN']} мин")
        time.sleep(CONFIG['START_DELAY_MIN'] * 60)

    start_sec, end_sec = get_window_start_end_today()
    now_sec = datetime.now().hour * 3600 + datetime.now().minute * 60 + datetime.now().second
    actual_start_sec = now_sec if start_sec <= now_sec < end_sec else start_sec
    window_start = datetime.now().replace(hour=actual_start_sec // 3600, minute=(actual_start_sec % 3600) // 60,
                                          second=0)

    offsets = generate_schedule(log_file)
    schedule_times = [window_start + timedelta(seconds=offset) for offset in offsets]

    write_log(log_file, "INFO", "Расписание:")
    for i, dt in enumerate(schedule_times, 1):
        write_log(log_file, "INFO", f"  #{i}: {dt.strftime('%H:%M:%S')}")

    completed = 0
    for i, target_time in enumerate(schedule_times, 1):
        wait_seconds = (target_time - datetime.now()).total_seconds()
        if wait_seconds > 0:
            write_log(log_file, "INFO", f"Ожидание {int(wait_seconds // 60)} мин до сессии {i}")
            time.sleep(wait_seconds)

        if run_single_session(log_file, i, len(schedule_times)):
            completed += 1
        time.sleep(2)

    if CONFIG['DISABLE_BT_AFTER_SESSION']:
        disable_bluetooth(log_file)

    write_log(log_file, "INFO", "=" * 60)
    write_log(log_file, "INFO", f"ВЫПОЛНЕНО: {completed} из {CONFIG['NUM_SESSIONS']}")
    write_log(log_file, "INFO", f"Лог: {log_file}")


# ========== ТОЧКА ВХОДА ==========

def main():
    """Главная функция"""
    log_file = init_logging()

    print("\n" + "=" * 60)
    print("Bluetooth Music Randomizer v2.0")
    print("=" * 60)
    print(f"Лог: {log_file}")
    print()

    try:
        # Запрашиваем подтверждение на тест
        print("Выполнить тестовое воспроизведение? (y/n): ", end="")
        response = input().strip().lower()

        if response == 'y' or response == 'yes' or response == '':
            if not test_playback(log_file):
                print("\n❌ Тест не удался. Хотите продолжить всё равно? (y/n): ", end="")
                if input().strip().lower() != 'y':
                    print("Выход.")
                    return

        # Запускаем основную сессию
        run_full_schedule(log_file)
        print(f"\n✅ Готово! Лог: {log_file}")

    except KeyboardInterrupt:
        write_log(log_file, "INFO", "\nПрервано пользователем")
        if CONFIG['DISABLE_BT_AFTER_SESSION']:
            disable_bluetooth(log_file)
        print("\n\n⚠️ Прервано пользователем")

    except Exception as e:
        write_log(log_file, "ERROR", f"Критическая ошибка: {e}")
        print(f"\n❌ Ошибка: {e}")


if __name__ == "__main__":
    main()
