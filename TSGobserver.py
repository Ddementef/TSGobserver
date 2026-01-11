import psutil
import time
import threading
import webbrowser
import os
import sys
import re
from tkinter import Tk, Label, Button, StringVar, Frame, Toplevel, Text, Scrollbar, messagebox
from typing import Set, Optional, Tuple, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
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
APP_VERSION = "2.2"

# URL репозитория GitHub в формате: owner/repo
GITHUB_REPO = "Ddementef/TSGobserver"


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
autostart_button: Optional[Button] = None
autostart_status_var: Optional[StringVar] = None

# Кэш процессов
_process_cache: Dict[str, Tuple[Set[str], float]] = {}  # {cache_key: (processes_set, timestamp)}
_cache_lock = threading.Lock()  # Блокировка для потокобезопасного доступа к кэшу


def setup_icon(window) -> None:
    """
    Устанавливает иконку окна из ресурсов exe файла.
    Иконка будет использоваться только если приложение упаковано в exe с иконкой.
    В Windows иконка встроена в exe, поэтому используем путь к самому exe.
    
    Args:
        window: Окно Tkinter (Tk или Toplevel) для установки иконки
    """
    try:
        # Проверяем, запущено ли приложение как exe
        if getattr(sys, 'frozen', False):
            # Используем иконку из самого exe файла
            # В Windows iconbitmap() может принимать путь к exe и извлечет иконку из его ресурсов
            window.iconbitmap(sys.executable)
    except Exception:
        # Если не получилось установить иконку (например, при запуске из скрипта),
        # просто игнорируем - это нормально
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
    Также проверяет корректность пути к исполняемому файлу.
    
    Returns:
        True если приложение в автозапуске и путь корректен, False в противном случае
    """
    try:
        startup_folder = get_startup_folder()
        app_name = get_app_name()
        bat_path = os.path.join(startup_folder, f"{app_name}.bat")
        vbs_path = os.path.join(startup_folder, f"{app_name}.vbs")
        
        # Проверяем .bat файл
        if os.path.exists(bat_path):
            try:
                with open(bat_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Ищем путь в формате: start "" "путь"
                # Регулярное выражение для поиска пути в кавычках после start ""
                match = re.search(r'start\s+""\s+"([^"]+)"', content)
                if match:
                    exe_path = match.group(1)
                    # Проверяем, существует ли файл
                    if os.path.exists(exe_path):
                        return True
                    else:
                        # Путь некорректен - удаляем файл автозапуска
                        try:
                            os.remove(bat_path)
                        except Exception:
                            pass
                        return False
            except Exception:
                # Если не удалось прочитать файл, считаем автозапуск неактивным
                return False
        
        # Проверяем .vbs файл
        if os.path.exists(vbs_path):
            try:
                with open(vbs_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Ищем путь к Python скрипту в формате: WshShell.Run """python_exe"" ""script_path"""
                # Регулярное выражение для поиска путей (формат: """путь1"" ""путь2""")
                match = re.search(r'WshShell\.Run\s+"""(.*?)""\s+""(.*?)"""', content)
                if match:
                    python_exe = match.group(1)
                    script_path = match.group(2)
                    # Проверяем, существуют ли оба файла
                    if os.path.exists(python_exe) and os.path.exists(script_path):
                        return True
                    else:
                        # Путь некорректен - удаляем файл автозапуска
                        try:
                            os.remove(vbs_path)
                        except Exception:
                            pass
                        return False
            except Exception:
                # Если не удалось прочитать файл, считаем автозапуск неактивным
                return False
        
        return False
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

