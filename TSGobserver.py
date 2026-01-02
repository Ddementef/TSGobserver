import psutil
import time
import threading
import webbrowser
import base64
import tempfile
import os
import sys
from tkinter import Tk, Label, Button, StringVar, Frame, Toplevel, Text, Scrollbar, messagebox
from typing import Set, Optional, Tuple, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# Константы
MONITORING_INTERVAL = 5  # секунды между проверками
TERMINATION_TIMEOUT = 3  # секунды ожидания завершения процесса
KILL_AFTER_TERMINATE = True  # Использовать kill() если terminate() не сработал
CACHE_TTL = 2  # Время жизни кэша процессов в секундах

# Версия приложения
APP_VERSION = "2.1"

# URL репозитория GitHub в формате: owner/repo
GITHUB_REPO = "Ddementef/TSGobserver"

# Встроенная иконка приложения (base64)
ICON_BASE64 = """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"""

# Словарь программ для завершения: ключ - имя процесса, значение - отображаемое название
PROGRAMS_TO_TERMINATE: Dict[str, str] = {
    "Telegram.exe": "Telegram",
    "Discord.exe": "Discord",
    "WhatsApp.exe": "WhatsApp",
    "WhatsApp.Root.exe": "WhatsApp",
    "EADesktop.exe": "EA",
    "Zoom.exe": "Zoom",
    "Skype.exe": "Skype",
    "GameCenter.exe": "GameCenter",
    "FACEIT.exe": "FACEIT",
    "upc.exe": "Ubisoft",
    "Uplay.exe": "Ubisoft",
    "Battle.net.exe": "Battle.net",
    "VKPlay.exe": "VK Play",
    "VK.exe": "VK",
    "Facebook.exe": "Facebook",
    "Odnoklassniki.exe": "Одноклассники",
    "Viber.exe": "Viber",
    "GalaxyClient.exe": "GOG GALAXY",
    "Teams.exe": "Teams",
    "slack.exe": "Slack",
    "OMEN Gaming Hub.exe": "OMEN Gaming Hub",
    "OMENCommandCenter.exe": "OMEN Gaming Hub"
}

# Список программ, которые нужно проверять на запуск
PROGRAMS_TO_CHECK = {
    "TSGLauncherA3AC.exe",
    "arma3_x64.exe"
}

# Глобальные переменные
monitoring_event = threading.Event()
monitor_thread: Optional[threading.Thread] = None
root: Optional[Tk] = None
status_var: Optional[StringVar] = None
detected_apps_var: Optional[StringVar] = None
start_button: Optional[Button] = None
stop_button: Optional[Button] = None
detected_apps_label: Optional[Label] = None
temp_icon_path: Optional[str] = None
autostart_button: Optional[Button] = None
autostart_status_var: Optional[StringVar] = None

# Кэш процессов
_process_cache: Dict[str, Tuple[Set[str], float]] = {}  # {cache_key: (processes_set, timestamp)}
_cache_lock = threading.Lock()  # Блокировка для потокобезопасного доступа к кэшу


def setup_icon(window) -> None:
    """
    Устанавливает иконку окна из встроенных данных.
    Создает временный .ico файл из base64 данных.
    
    Args:
        window: Окно Tkinter (Tk или Toplevel) для установки иконки
    """
    global temp_icon_path
    
    try:
        # Декодируем base64 данные
        icon_data = base64.b64decode(ICON_BASE64)
        
        # Создаем временный файл
        temp_dir = tempfile.gettempdir()
        temp_icon_path = os.path.join(temp_dir, "tsg_observer_icon.ico")
        
        if PIL_AVAILABLE:
            # Используем PIL для конвертации PNG в ICO
            from io import BytesIO
            img = Image.open(BytesIO(icon_data))
            img.save(temp_icon_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        else:
            # Если PIL недоступен, сохраняем как PNG и используем напрямую
            temp_icon_path = temp_icon_path.replace('.ico', '.png')
            with open(temp_icon_path, 'wb') as f:
                f.write(icon_data)
        
        # Устанавливаем иконку
        try:
            window.iconbitmap(temp_icon_path)
        except:
            # Если не получилось установить иконку, игнорируем ошибку
            pass
            
    except Exception:
        # Если что-то пошло не так, просто игнорируем
        pass


def get_startup_folder() -> str:
    """
    Получает путь к папке автозапуска Windows.
    
    Returns:
        Путь к папке автозапуска
    """
    startup_folder = os.path.join(os.getenv('APPDATA'), 
                                   'Microsoft', 
                                   'Windows', 
                                   'Start Menu', 
                                   'Programs', 
                                   'Startup')
    return startup_folder


def get_app_name() -> str:
    """
    Получает имя приложения для файла автозапуска.
    
    Returns:
        Имя для .bat или .vbs файла (без расширения)
    """
    return "TSG Observer"


def is_in_autostart() -> bool:
    """
    Проверяет, добавлено ли приложение в автозапуск Windows.
    
    Returns:
        True если приложение в автозапуске, False в противном случае
    """
    try:
        startup_folder = get_startup_folder()
        app_name = get_app_name()
        # Проверяем наличие .bat или .vbs файла
        bat_path = os.path.join(startup_folder, f"{app_name}.bat")
        vbs_path = os.path.join(startup_folder, f"{app_name}.vbs")
        return os.path.exists(bat_path) or os.path.exists(vbs_path)
    except Exception:
        return False


def add_to_autostart() -> bool:
    """
    Добавляет приложение в автозапуск Windows путем создания .bat или .vbs файла.
    Для .exe используется .bat, для Python скрипта - .vbs (чтобы скрыть консоль).
    
    Returns:
        True если успешно добавлено, False в противном случае
    """
    try:
        startup_folder = get_startup_folder()
        os.makedirs(startup_folder, exist_ok=True)
        
        app_name = get_app_name()
        is_frozen = getattr(sys, 'frozen', False)
        
        if is_frozen:
            # Это скомпилированное .exe приложение - используем .bat
            exe_path = sys.executable
            bat_path = os.path.join(startup_folder, f"{app_name}.bat")
            with open(bat_path, 'w', encoding='utf-8') as f:
                f.write(f'@echo off\nstart "" "{exe_path}"\n')
            return os.path.exists(bat_path)
        else:
            # Это скрипт Python - используем .vbs для скрытия консоли
            python_exe = sys.executable
            script_path = os.path.abspath(__file__)
            vbs_path = os.path.join(startup_folder, f"{app_name}.vbs")
            
            # Создаем VBScript, который запускает Python скрипт без консоли
            vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """{python_exe}"" ""{script_path}""", 0, False
Set WshShell = Nothing
'''
            with open(vbs_path, 'w', encoding='utf-8') as f:
                f.write(vbs_content)
            return os.path.exists(vbs_path)
            
    except Exception:
        return False


def remove_from_autostart() -> bool:
    """
    Удаляет приложение из автозапуска Windows.
    
    Returns:
        True если успешно удалено, False в противном случае
    """
    try:
        startup_folder = get_startup_folder()
        app_name = get_app_name()
        
        # Пробуем удалить .bat файл
        bat_path = os.path.join(startup_folder, f"{app_name}.bat")
        if os.path.exists(bat_path):
            os.remove(bat_path)
            return True
        
        # Пробуем удалить .vbs файл
        vbs_path = os.path.join(startup_folder, f"{app_name}.vbs")
        if os.path.exists(vbs_path):
            os.remove(vbs_path)
            return True
        
        return False
    except Exception:
        return False


def show_autostart_dialog() -> bool:
    """
    Показывает диалоговое окно с вопросом о добавлении в автозапуск.
    
    Returns:
        True если пользователь согласился, False в противном случае
    """
    if root is None:
        return False
    
    result = messagebox.askyesno(
        "Автозапуск",
        "Рекомендуем добавить TSG Observer в автозапуск Windows,\n"
        "чтобы программа запускалась автоматически при включении компьютера.\n\n"
        "Добавить в автозапуск?",
        icon='question'
    )
    return result


def check_autostart_on_startup() -> None:
    """
    Проверяет автозапуск при запуске приложения и показывает диалог если нужно.
    """
    if root is None:
        return
    
    # Если уже в автозапуске, ничего не делаем
    if is_in_autostart():
        return
    
    # Показываем диалог
    if show_autostart_dialog():
        # Пользователь согласился - добавляем в автозапуск
        if add_to_autostart():
            # Обновляем UI
            global autostart_status_var, autostart_button
            if autostart_status_var:
                autostart_status_var.set("Автозапуск: Включен")
            if autostart_button:
                autostart_button.config(text="✗ Выключить автозапуск", bg="#ef4444", activebackground="#ef4444")
            messagebox.showinfo("Автозапуск", "TSG Observer добавлен в автозапуск")
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить в автозапуск")
    else:
        # Пользователь отказался - просто закрываем диалог, приложение продолжает работать
        pass


def get_latest_release_info() -> Optional[Dict]:
    """
    Получает информацию о последнем релизе из GitHub.
    
    Returns:
        Словарь с информацией о релизе (tag_name, html_url) или None в случае ошибки
    """
    if not REQUESTS_AVAILABLE:
        return None
    
    if not GITHUB_REPO:
        return None
    
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "tag_name": data.get("tag_name", ""),
                "html_url": data.get("html_url", ""),
                "name": data.get("name", "")
            }
        return None
    except Exception:
        return None


def compare_versions(current_version: str, latest_version: str) -> bool:
    """
    Сравнивает две версии и возвращает True, если latest_version новее.
    
    Args:
        current_version: Текущая версия (например, "2.0")
        latest_version: Версия для сравнения (например, "v2.1" или "2.1")
        
    Returns:
        True если latest_version новее current_version
    """
    try:
        # Убираем префикс "v" если есть
        current = current_version.lstrip("vV")
        latest = latest_version.lstrip("vV")
        
        # Разбиваем на части
        current_parts = [int(x) for x in current.split(".")]
        latest_parts = [int(x) for x in latest.split(".")]
        
        # Нормализуем длины (добавляем нули если нужно)
        max_len = max(len(current_parts), len(latest_parts))
        current_parts.extend([0] * (max_len - len(current_parts)))
        latest_parts.extend([0] * (max_len - len(latest_parts)))
        
        # Сравниваем по частям
        for i in range(max_len):
            if latest_parts[i] > current_parts[i]:
                return True
            elif latest_parts[i] < current_parts[i]:
                return False
        
        return False  # Версии равны
    except Exception:
        return False


def show_update_dialog(latest_version: str, release_url: str, release_name: str = "") -> None:
    """
    Показывает диалоговое окно о новом обновлении.
    
    Args:
        latest_version: Версия нового релиза
        release_url: URL страницы релиза
        release_name: Название релиза (опционально)
    """
    if root is None:
        return
    
    version_text = f"Версия {latest_version}"
    if release_name:
        version_text = f"{release_name} ({latest_version})"
    
    result = messagebox.askyesno(
        "Вышло новое обновление",
        f"Доступна новая версия программы:\n\n"
        f"{version_text}\n\n"
        f"Текущая версия: {APP_VERSION}\n\n"
        f"Открыть страницу последнего релиза для скачивания?",
        icon='question'
    )
    
    if result:
        webbrowser.open_new(release_url)


def check_for_updates() -> None:
    """
    Проверяет наличие обновлений и показывает диалог, если найдено.
    Запускается в отдельном потоке, чтобы не блокировать UI.
    """
    if not REQUESTS_AVAILABLE:
        return
    
    if not GITHUB_REPO:
        return
    
    def check_in_thread():
        try:
            release_info = get_latest_release_info()
            if release_info:
                latest_version = release_info["tag_name"]
                release_url = release_info["html_url"]
                release_name = release_info.get("name", "")
                
                if compare_versions(APP_VERSION, latest_version):
                    # Показываем диалог в главном потоке
                    if root:
                        root.after(0, lambda: show_update_dialog(latest_version, release_url, release_name))
        except Exception:
            pass  # Игнорируем ошибки при проверке обновлений
    
    # Запускаем проверку в отдельном потоке
    update_thread = threading.Thread(target=check_in_thread, daemon=True)
    update_thread.start()


def toggle_autostart() -> None:
    """
    Переключает состояние автозапуска (включает/выключает).
    """
    global autostart_status_var, autostart_button
    
    if is_in_autostart():
        if remove_from_autostart():
            if autostart_status_var:
                autostart_status_var.set("Автозапуск: Выключен")
            if autostart_button:
                autostart_button.config(text="✓ Включить автозапуск", bg="#4ade80", activebackground="#4ade80")
            messagebox.showinfo("Автозапуск", "Автозапуск выключен")
        else:
            messagebox.showerror("Ошибка", "Не удалось отключить автозапуск")
    else:
        if add_to_autostart():
            if autostart_status_var:
                autostart_status_var.set("Автозапуск: Включен")
            if autostart_button:
                autostart_button.config(text="✗ Выключить автозапуск", bg="#ef4444", activebackground="#ef4444")
            messagebox.showinfo("Автозапуск", "Автозапуск включен")
        else:
            messagebox.showerror("Ошибка", "Не удалось включить автозапуск")


def get_display_name(process_name: str) -> str:
    """
    Возвращает отображаемое имя процесса.
    
    Args:
        process_name: Имя процесса (например, "Telegram.exe")
        
    Returns:
        Отображаемое имя (например, "Telegram")
    """
    return PROGRAMS_TO_TERMINATE.get(process_name, process_name.replace(".exe", ""))


def _get_all_processes_cached() -> Dict[str, List[Tuple[int, str]]]:
    """
    Получает все процессы с кэшированием.
    
    Returns:
        Словарь {имя_процесса: [(pid, name), ...]}
    """
    current_time = time.time()
    cache_key = "all_processes"
    
    with _cache_lock:
        # Проверяем кэш
        if cache_key in _process_cache:
            cached_data, cache_time = _process_cache[cache_key]
            if current_time - cache_time < CACHE_TTL:
                return cached_data
        
        # Кэш устарел или отсутствует, обновляем
        processes_dict: Dict[str, List[Tuple[int, str]]] = {}
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = proc.info['name']
                    pid = proc.info['pid']
                    if name not in processes_dict:
                        processes_dict[name] = []
                    processes_dict[name].append((pid, name))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception:
            pass
        
        # Сохраняем в кэш
        _process_cache[cache_key] = (processes_dict, current_time)
        return processes_dict


def get_running_processes(process_names: Set[str]) -> Set[str]:
    """
    Получает набор запущенных процессов из указанного списка.
    Использует кэширование для оптимизации.
    
    Args:
        process_names: Множество имен процессов для проверки
        
    Returns:
        Множество имен запущенных процессов
    """
    running = set()
    processes_dict = _get_all_processes_cached()
    
    for name in process_names:
        if name in processes_dict:
            running.add(name)
    
    return running


def get_child_processes(process: psutil.Process) -> List[psutil.Process]:
    """
    Получает список всех дочерних процессов (рекурсивно).
    
    Args:
        process: Родительский процесс
        
    Returns:
        Список дочерних процессов
    """
    try:
        if not process.is_running():
            return []
        
        # Получаем всех потомков рекурсивно одним вызовом
        return process.children(recursive=True)
            
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return []
    except Exception:
        return []


def terminate_process(process: psutil.Process, name: str, pid: int, terminate_children: bool = True) -> bool:
    """
    Завершает процесс с таймаутом и его дочерние процессы.
    
    Args:
        process: Объект процесса psutil
        name: Имя процесса
        pid: PID процесса
        terminate_children: Завершать ли дочерние процессы
        
    Returns:
        True если процесс успешно завершен, False в противном случае
    """
    try:
        # Проверяем, что процесс еще существует
        if not process.is_running():
            return False
        
        # Сначала завершаем дочерние процессы
        if terminate_children:
            try:
                children = get_child_processes(process)
                for child in children:
                    try:
                        if child.is_running():
                            child.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
            except Exception:
                pass
        
        # Завершаем основной процесс
        process.terminate()
        process.wait(timeout=TERMINATION_TIMEOUT)
        
        # Принудительно завершаем дочерние процессы, если они еще живы
        if terminate_children:
            try:
                children = get_child_processes(process)
                for child in children:
                    try:
                        if child.is_running():
                            child.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
            except Exception:
                pass
        
        return True
    except psutil.TimeoutExpired:
        if KILL_AFTER_TERMINATE:
            try:
                # Проверяем еще раз перед kill
                if not process.is_running():
                    return True  # Уже завершен
                
                # Принудительно завершаем дочерние процессы перед kill основного
                if terminate_children:
                    try:
                        children = get_child_processes(process)
                        for child in children:
                            try:
                                if child.is_running():
                                    child.kill()
                            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                                pass
                    except Exception:
                        pass
                
                process.kill()
                process.wait(timeout=1)
                return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Процесс уже завершен или нет доступа
                return False
            except Exception:
                return False
        else:
            return False
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        # Процесс уже завершен или нет доступа
        return False
    except Exception:
        return False


def _terminate_single_process(args: Tuple[psutil.Process, str, int]) -> bool:
    """
    Вспомогательная функция для асинхронного завершения процесса.
    
    Args:
        args: Кортеж (process, name, pid)
        
    Returns:
        True если процесс успешно завершен
    """
    process, name, pid = args
    return terminate_process(process, name, pid, terminate_children=True)


def terminate_forbidden_programs() -> int:
    """
    Завершает запрещенные программы асинхронно.
    Использует кэширование и параллельное завершение процессов.
    
    Returns:
        Количество успешно завершенных процессов
    """
    processes_to_terminate = []
    processes_dict = _get_all_processes_cached()
    
    # Собираем все процессы для завершения из кэша
    for name in PROGRAMS_TO_TERMINATE:
        if name in processes_dict:
            for pid, _ in processes_dict[name]:
                try:
                    process = psutil.Process(pid)
                    if process.is_running():
                        processes_to_terminate.append((process, name, pid))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
                except Exception:
                    pass
    
    if not processes_to_terminate:
        return 0
    
    # Асинхронное завершение процессов
    terminated_count = 0
    max_workers = min(len(processes_to_terminate), 10)  # Ограничиваем количество потоков
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Запускаем завершение всех процессов параллельно
        future_to_process = {
            executor.submit(_terminate_single_process, (proc, name, pid)): (name, pid)
            for proc, name, pid in processes_to_terminate
        }
        
        # Собираем результаты
        for future in as_completed(future_to_process):
            try:
                if future.result():
                    terminated_count += 1
            except Exception:
                pass
    
    # Очищаем кэш после завершения процессов
    with _cache_lock:
        _process_cache.clear()
    
    return terminated_count


def check_and_terminate_if_needed() -> Tuple[bool, int, Set[str]]:
    """
    Проверяет запущены ли целевые программы и завершает запрещенные при необходимости.
    Использует кэширование и асинхронное завершение.
    
    Returns:
        Кортеж (все_целевые_программы_запущены, количество_завершенных_процессов, обнаруженные_запрещенные_процессы)
    """
    # Используем кэшированные данные
    processes_dict = _get_all_processes_cached()
    
    # Проверяем целевые программы
    running_check = set()
    for name in PROGRAMS_TO_CHECK:
        if name in processes_dict:
            running_check.add(name)
    
    all_target_running = PROGRAMS_TO_CHECK.issubset(running_check)
    
    # Ищем запрещенные программы
    detected_forbidden = set()
    for name in PROGRAMS_TO_TERMINATE:
        if name in processes_dict:
            detected_forbidden.add(name)
    
    terminated_count = 0
    
    # Завершаем процессы только если все целевые запущены
    if all_target_running and detected_forbidden:
        terminated_count = terminate_forbidden_programs()
    
    return all_target_running, terminated_count, detected_forbidden


def update_status(message: str) -> None:
    """
    Безопасно обновляет статусное сообщение в UI из любого потока.
    
    Args:
        message: Текст статуса
    """
    if root is None or status_var is None:
        return
    
    # Безопасное обновление GUI из другого потока
    def update():
        if status_var.get() != message:
            status_var.set(message)
    
    root.after(0, update)


def format_apps_list(apps: list, first_line_max: int = 2, other_lines_max: int = 3) -> str:
    """
    Форматирует список приложений с переносами строк.
    """
    if not apps:
        return ""
    
    lines = []
    
    # Первая строка - максимум first_line_max приложений
    if len(apps) > 0:
        first_line_apps = apps[:first_line_max]
        lines.append(", ".join(first_line_apps))
        remaining_apps = apps[first_line_max:]
        
        # Остальные строки - по other_lines_max приложений
        for i in range(0, len(remaining_apps), other_lines_max):
            line_apps = remaining_apps[i:i + other_lines_max]
            lines.append(", ".join(line_apps))
    
    return "\n".join(lines)


def update_detected_apps(detected_apps: Set[str], all_target_running: bool) -> None:
    """
    Безопасно обновляет список обнаруженных приложений в UI из любого потока.
    
    Args:
        detected_apps: Множество имен обнаруженных запрещенных процессов
        all_target_running: Флаг, запущены ли целевые программы
    """
    if root is None or detected_apps_var is None:
        return
    
    # Безопасное обновление GUI из другого потока
    def update():
        global detected_apps_label
        
        # Проверяем статус мониторинга
        is_monitoring_running = monitor_thread is not None and monitor_thread.is_alive()
        
        if all_target_running and detected_apps:
            # Преобразуем имена процессов в отображаемые имена
            display_names = sorted([get_display_name(name) for name in detected_apps])
            # Первая строка с текстом содержит максимум 2 приложения, далее по 3
            first_line_apps = display_names[:2]
            remaining_apps = display_names[2:]
            
            if remaining_apps:
                # Если есть приложения после первых двух, форматируем остальные по 3 на строку
                first_line = ", ".join(first_line_apps)
                other_lines = []
                for i in range(0, len(remaining_apps), 3):
                    line_apps = remaining_apps[i:i + 3]
                    other_lines.append(", ".join(line_apps))
                apps_list = f"{first_line}\n" + "\n".join(other_lines)
            else:
                # Если приложений 2 или меньше, все в одной строке
                apps_list = ", ".join(first_line_apps)
            
            text = f"Закрываются приложения: {apps_list}"
            detected_apps_var.set(text)
            if detected_apps_label:
                detected_apps_label.config(fg="#fbbf24")  # warning_color
        elif detected_apps:
            # Преобразуем имена процессов в отображаемые имена
            display_names = sorted([get_display_name(name) for name in detected_apps])
            # Первая строка с текстом содержит максимум 2 приложения, далее по 3
            first_line_apps = display_names[:2]
            remaining_apps = display_names[2:]
            
            if remaining_apps:
                # Если есть приложения после первых двух, форматируем остальные по 3 на строку
                first_line = ", ".join(first_line_apps)
                other_lines = []
                for i in range(0, len(remaining_apps), 3):
                    line_apps = remaining_apps[i:i + 3]
                    other_lines.append(", ".join(line_apps))
                apps_list = f"{first_line}\n" + "\n".join(other_lines)
            else:
                # Если приложений 2 или меньше, все в одной строке
                apps_list = ", ".join(first_line_apps)
            
            text = f"Обнаружены (закроются при запуске Arma 3): {apps_list}"
            detected_apps_var.set(text)
            if detected_apps_label:
                detected_apps_label.config(fg="#fbbf24")  # warning_color
        else:
            if is_monitoring_running:
                detected_apps_var.set("Ничего не обнаружено")
                if detected_apps_label:
                    detected_apps_label.config(fg="#4ade80")  # success_color (зеленый)
            else:
                detected_apps_var.set("Запустите мониторинг")
                if detected_apps_label:
                    detected_apps_label.config(fg="#ef4444")  # красный цвет
    
    root.after(0, update)


def monitor_program() -> None:
    """
    Функция для мониторинга и завершения процессов.
    Запускается в отдельном потоке.
    """
    while not monitoring_event.is_set():
        try:
            all_running, terminated_count, detected_forbidden = check_and_terminate_if_needed()
            
            # Обновляем список обнаруженных приложений
            update_detected_apps(detected_forbidden, all_running)
            
            # Ожидание с проверкой события для быстрой остановки
            monitoring_event.wait(timeout=MONITORING_INTERVAL)
            
        except Exception:
            time.sleep(MONITORING_INTERVAL)


def start_monitoring() -> None:
    """
    Запускает поток мониторинга.
    """
    global monitor_thread
    
    if monitor_thread is not None and monitor_thread.is_alive():
        return
    
    monitoring_event.clear()
    monitor_thread = threading.Thread(target=monitor_program, daemon=True)
    monitor_thread.start()
    
    update_status("✓ Мониторинг запущен")
    
    # Сразу проверяем и отображаем обнаруженные приложения
    try:
        running_check = get_running_processes(PROGRAMS_TO_CHECK)
        all_target_running = PROGRAMS_TO_CHECK.issubset(running_check)
        detected_forbidden = get_running_processes(set(PROGRAMS_TO_TERMINATE.keys()))
        update_detected_apps(detected_forbidden, all_target_running)
    except Exception:
        pass
    
    if start_button:
        start_button.config(state="disabled", bg="#3d5a3d", cursor="arrow")
    if stop_button:
        stop_button.config(state="normal", bg="#5a3d3d", cursor="hand2")


def stop_monitoring() -> None:
    """
    Останавливает мониторинг и обновляет UI.
    """
    global monitor_thread
    
    monitoring_event.set()
    
    # Ждем завершения потока (с таймаутом)
    if monitor_thread is not None and monitor_thread.is_alive():
        monitor_thread.join(timeout=2)
    
    # Проверяем, что окно еще существует, прежде чем обновлять UI
    if root is None:
        return
    
    try:
        # Проверяем, что окно не уничтожено
        root.winfo_exists()
    except:
        return
    
    try:
        update_status("○ Мониторинг остановлен")
        update_detected_apps(set(), False)
        if start_button:
            start_button.config(state="normal", bg="#4a5568", cursor="hand2")
        if stop_button:
            stop_button.config(state="disabled", bg="#3a3a3a", cursor="arrow")
    except:
        # Игнорируем ошибки, если окно уже уничтожено
        pass


def on_closing() -> None:
    """
    Обработчик закрытия окна.
    """
    stop_monitoring()
    if root:
        root.destroy()


def open_link(event=None) -> None:
    """
    Открывает ссылку в браузере.
    
    Args:
        event: Событие клика (опционально)
    """
    webbrowser.open_new("https://tsgames.ru/user/profile/Mongren")


def on_button_hover(event, button: Button, hover_color: str) -> None:
    """Обработчик наведения на кнопку."""
    if button.cget("state") == "normal":
        button.config(bg=hover_color)


def on_button_leave(event, button: Button, default_color: str) -> None:
    """Обработчик ухода курсора с кнопки."""
    if button.cget("state") == "normal":
        button.config(bg=default_color)


def show_help() -> None:
    """
    Отображает окно справки с описанием работы программы и списком отслеживаемых приложений.
    """
    help_window = Toplevel(root)
    help_window.title("Справка - TSG Observer")
    help_window.geometry("600x500")
    
    # Устанавливаем иконку окна
    setup_icon(help_window)
    
    # Цветовая схема
    bg_color = "#1a1a2e"
    card_color = "#16213e"
    text_color = "#eaeaea"
    accent_color = "#60a5fa"
    
    help_window.configure(bg=bg_color)
    help_window.resizable(False, False)
    
    # Центрирование окна
    help_window.update_idletasks()
    width = help_window.winfo_width()
    height = help_window.winfo_height()
    x = (help_window.winfo_screenwidth() // 2) - (width // 2)
    y = (help_window.winfo_screenheight() // 2) - (height // 2)
    help_window.geometry(f"{600}x{500}+{x}+{y}")
    
    # Главный контейнер
    main_frame = Frame(help_window, bg=bg_color)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Заголовок
    title_label = Label(
        main_frame,
        text="Справка",
        fg=text_color,
        bg=bg_color,
        font=("Segoe UI", 16, "bold")
    )
    title_label.pack(pady=(0, 15))
    
    # Описание работы
    desc_frame = Frame(main_frame, bg=card_color, relief="flat", bd=0)
    desc_frame.pack(fill="both", expand=True, pady=(0, 10))
    
    desc_title = Label(
        desc_frame,
        text="Как работает программа:",
        fg="#9ca3af",
        bg=card_color,
        font=("Segoe UI", 10, "bold"),
        anchor="w"
    )
    desc_title.pack(anchor="w", padx=15, pady=(12, 8))
    
    desc_text = Label(
        desc_frame,
        text="Программа автоматически завершает указанные приложения только когда\n"
             "одновременно запущены оба процесса:\n"
             "• TSGLauncherA3AC.exe (лаунчер проекта)\n"
             "• arma3_x64.exe (игра Arma 3)\n\n"
             "Если хотя бы один из этих процессов не запущен,\n"
             "приложения НЕ будут закрываться.",
        fg=text_color,
        bg=card_color,
        font=("Segoe UI", 9),
        justify="left",
        anchor="w"
    )
    desc_text.pack(anchor="w", padx=15, pady=(0, 12))
    
    # Список отслеживаемых приложений
    apps_frame = Frame(main_frame, bg=card_color, relief="flat", bd=0)
    apps_frame.pack(fill="both", expand=True)
    
    apps_title = Label(
        apps_frame,
        text="Отслеживаемые приложения:",
        fg="#9ca3af",
        bg=card_color,
        font=("Segoe UI", 10, "bold"),
        anchor="w"
    )
    apps_title.pack(anchor="w", padx=15, pady=(12, 8))
    
    # Получаем отсортированный список отображаемых названий
    display_names = sorted(set(PROGRAMS_TO_TERMINATE.values()))
    apps_text = ", ".join(display_names)
    
    apps_label = Label(
        apps_frame,
        text=apps_text,
        fg=text_color,
        bg=card_color,
        font=("Segoe UI", 9),
        justify="left",
        wraplength=540,
        anchor="w"
    )
    apps_label.pack(anchor="w", padx=15, pady=(0, 12))
    
    # Кнопка закрытия
    close_button = Button(
        main_frame,
        text="Закрыть",
        command=help_window.destroy,
        bg="#4a5568",
        fg=text_color,
        font=("Segoe UI", 10, "bold"),
        relief="flat",
        bd=0,
        padx=30,
        pady=8,
        cursor="hand2",
        activebackground="#5a6678",
        activeforeground=text_color
    )
    close_button.pack(pady=(15, 0))


def create_gui() -> None:
    """
    Создает и настраивает графический интерфейс.
    """
    global root, status_var, detected_apps_var, start_button, stop_button, detected_apps_label, autostart_button, autostart_status_var
    
    root = Tk()
    root.title("TSG Observer")
    root.geometry("600x405")
    
    # Устанавливаем иконку окна
    setup_icon(root)
    
    # Современная темная цветовая схема
    bg_color = "#1a1a2e"
    card_color = "#16213e"
    text_color = "#eaeaea"
    accent_color = "#0f3460"
    success_color = "#4ade80"
    warning_color = "#fbbf24"
    button_color = "#4a5568"
    button_hover = "#5a6678"
    button_stop = "#5a3d3d"
    button_stop_hover = "#6a4d4d"
    
    root.configure(bg=bg_color)
    root.resizable(False, False)
    
    # Центрирование окна
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    status_var = StringVar()
    detected_apps_var = StringVar()
    
    # Главный контейнер с отступами
    main_frame = Frame(root, bg=bg_color)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Заголовок с кнопкой справки
    header_frame = Frame(main_frame, bg=bg_color)
    header_frame.pack(fill="x", pady=(0, 5))
    
    title_label = Label(
        header_frame,
        text="TSG Observer",
        fg=text_color,
        bg=bg_color,
        font=("Segoe UI", 18, "bold")
    )
    title_label.pack(side="left")
    
    # Кнопка справки
    help_button = Button(
        header_frame,
        text="?",
        command=show_help,
        bg="#4a5568",
        fg=text_color,
        font=("Segoe UI", 12, "bold"),
        relief="flat",
        bd=0,
        width=3,
        height=1,
        cursor="hand2",
        activebackground="#5a6678",
        activeforeground=text_color
    )
    help_button.pack(side="right")
    help_button.bind("<Enter>", lambda e: help_button.config(bg="#5a6678"))
    help_button.bind("<Leave>", lambda e: help_button.config(bg="#4a5568"))
    
    # Карточка статуса
    status_frame = Frame(main_frame, bg=card_color, relief="flat", bd=0)
    status_frame.pack(fill="x", pady=(0, 15))
    
    status_title = Label(
        status_frame,
        text="Статус:",
        fg="#9ca3af",
        bg=card_color,
        font=("Segoe UI", 9),
        anchor="w"
    )
    status_title.pack(anchor="w", padx=15, pady=(12, 5))
    
    status_label = Label(
        status_frame,
        textvariable=status_var,
        fg=text_color,
        bg=card_color,
        font=("Segoe UI", 11),
        wraplength=540,
        justify="left"
    )
    status_label.pack(anchor="w", padx=15, pady=(0, 12))
    
    # Карточка обнаруженных приложений
    apps_frame = Frame(main_frame, bg=card_color, relief="flat", bd=0)
    apps_frame.pack(fill="x", pady=(0, 20))
    
    apps_title = Label(
        apps_frame,
        text="Обнаруженные приложения:",
        fg="#9ca3af",
        bg=card_color,
        font=("Segoe UI", 9),
        anchor="w"
    )
    apps_title.pack(anchor="w", padx=15, pady=(12, 5))
    
    detected_apps_label = Label(
        apps_frame,
        textvariable=detected_apps_var,
        fg=warning_color,
        bg=card_color,
        font=("Segoe UI", 10),
        wraplength=540,
        justify="left",
        anchor="nw"
    )
    detected_apps_label.pack(anchor="nw", padx=15, pady=(0, 12))
    
    # Кнопка управления автозапуском
    autostart_frame = Frame(main_frame, bg=bg_color)
    autostart_frame.pack(fill="x", pady=(10, 0))
    
    autostart_status_var = StringVar()
    autostart_status_label = Label(
        autostart_frame,
        textvariable=autostart_status_var,
        fg="#9ca3af",
        bg=bg_color,
        font=("Segoe UI", 9),
        anchor="w"
    )
    autostart_status_label.pack(side="left")
    
    # Обновляем статус автозапуска
    if is_in_autostart():
        autostart_status_var.set("Автозапуск: Включен")
        autostart_btn_text = "✗ Выключить автозапуск"
        autostart_btn_color = "#ef4444"
    else:
        autostart_status_var.set("Автозапуск: Выключен")
        autostart_btn_text = "✓ Включить автозапуск"
        autostart_btn_color = "#4ade80"
    
    autostart_button = Button(
        autostart_frame,
        text=autostart_btn_text,
        command=toggle_autostart,
        bg=autostart_btn_color,
        fg=text_color,
        font=("Segoe UI", 9, "bold"),
        relief="flat",
        bd=0,
        padx=15,
        pady=6,
        cursor="hand2",
        activebackground=autostart_btn_color,
        activeforeground=text_color
    )
    autostart_button.pack(side="right")
    
    # Контейнер для кнопок
    button_frame = Frame(main_frame, bg=bg_color)
    button_frame.pack(fill="x", pady=(10, 0))
    
    # Кнопка запуска
    start_button = Button(
        button_frame,
        text="▶ Запустить мониторинг",
        command=start_monitoring,
        bg=button_color,
        fg=text_color,
        font=("Segoe UI", 11, "bold"),
        relief="flat",
        bd=0,
        padx=30,
        pady=12,
        cursor="hand2",
        activebackground=button_hover,
        activeforeground=text_color
    )
    start_button.pack(side="left", expand=True, fill="x", padx=(0, 8))
    start_button.bind("<Enter>", lambda e: on_button_hover(e, start_button, button_hover))
    start_button.bind("<Leave>", lambda e: on_button_leave(e, start_button, button_color))
    
    # Кнопка остановки
    stop_button = Button(
        button_frame,
        text="■ Остановить мониторинг",
        command=stop_monitoring,
        bg="#3a3a3a",
        fg=text_color,
        font=("Segoe UI", 11, "bold"),
        relief="flat",
        bd=0,
        padx=30,
        pady=12,
        cursor="arrow",
        state="disabled",
        activebackground=button_stop,
        activeforeground=text_color
    )
    stop_button.pack(side="left", expand=True, fill="x", padx=(8, 0))
    stop_button.bind("<Enter>", lambda e: on_button_hover(e, stop_button, button_stop_hover))
    stop_button.bind("<Leave>", lambda e: on_button_leave(e, stop_button, button_stop))
    
    # Информация о создателе на главном экране
    creator_frame = Frame(main_frame, bg=bg_color)
    creator_frame.pack(fill="x", pady=(15, 0))
    
    creator_label = Label(
        creator_frame,
        text="Создатель: Mongren",
        fg="#60a5fa",
        cursor="hand2",
        bg=bg_color,
        font=("Segoe UI", 9)
    )
    creator_label.pack()
    creator_label.bind("<Button-1>", open_link)
    creator_label.bind("<Enter>", lambda e: creator_label.config(fg="#93c5fd"))
    creator_label.bind("<Leave>", lambda e: creator_label.config(fg="#60a5fa"))
    
    # Обработчик закрытия окна
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Проверяем автозапуск и показываем диалог при первом запуске
    if not is_in_autostart():
        # Используем root.after для показа диалога после полной инициализации окна
        root.after(100, check_autostart_on_startup)
    
    # Проверяем наличие обновлений (после небольшой задержки, чтобы не мешать инициализации)
    root.after(500, check_for_updates)
    
    # Запускаем мониторинг по умолчанию
    start_monitoring()


def main() -> None:
    """
    Главная функция приложения.
    """
    try:
        create_gui()
        if root:
            root.mainloop()
    except Exception:
        raise
    finally:
        # Очистка при завершении
        monitoring_event.set()


if __name__ == "__main__":
    main()

