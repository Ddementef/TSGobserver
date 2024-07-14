import psutil
import time
import threading
from tkinter import Tk, Label, Button, StringVar, messagebox
import requests
import os

# Список программ для выключения
PROGRAMS_TO_TERMINATE = {
    "Telegram.exe",
    "Discord.exe",
    "WhatsApp.exe",
    "EADesktop.exe",
    "Zoom.exe",
    "Skype.exe",
    "GameCenter.exe",
    "FACEIT.exe"
}

# Список программ, которые нужно проверять на запуск
PROGRAMS_TO_CHECK = {
    "TSGLauncherA3AC.exe",
    "arma3_x64.exe"
}

# Событие для остановки мониторинга
monitoring_event = threading.Event()

def terminate_programs_and_check_running(program_list, check_list):
    running_programs = set()
    for process in psutil.process_iter(['pid', 'name']):
        try:
            name = process.info['name']
            if name in check_list:
                running_programs.add(name)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    if check_list.issubset(running_programs):
        for process in psutil.process_iter(['pid', 'name']):
            try:
                name = process.info['name']
                if name in program_list:
                    proc = psutil.Process(process.info['pid'])
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                        print(f"Terminated: {name} (PID: {process.info['pid']})")
                    except psutil.TimeoutExpired:
                        print(f"Failed to terminate: {name} (PID: {process.info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    return running_programs

def monitor_program():
    while not monitoring_event.is_set():
        running_programs = terminate_programs_and_check_running(PROGRAMS_TO_TERMINATE, PROGRAMS_TO_CHECK)
        if PROGRAMS_TO_CHECK.issubset(running_programs):
            print("Все запрещённое закрывается автоматически")
            update_status("Все запрещённое закрывается автоматически")
        else:
            print("Ожидаем запуск лаунчера и Arma 3")
            update_status("Ожидаем запуск лаунчера и Arma 3")
        time.sleep(5)

def update_status(message):
    if status_var.get() != message:
        status_var.set(message)

def start_monitoring():
    monitor_thread = threading.Thread(target=monitor_program)
    monitor_thread.daemon = True
    monitor_thread.start()

def stop_monitoring():
    monitoring_event.set()
    root.destroy()

def on_closing():
    stop_monitoring()

def open_link(event):
    import webbrowser
    webbrowser.open_new("https://tsgames.ru/user/profile/Mongren")

def get_latest_version():
    url = 'https://raw.githubusercontent.com/Ddementef/TSGobserver/main/version.txt'  # Замените на URL вашего файла с версией
    response = requests.get(url)
    if response.status_code == 200:
        return response.text.strip()
    else:
        return None

def download_latest_version():
    url = 'https://github.com/Ddementef/TSGobserver/releases/latest/download/TSGobserver.exe'  # Замените на URL вашего .exe файла
    response = requests.get(url)
    with open('TSGobserver_latest.exe', 'wb') as file:
        file.write(response.content)

def check_for_updates():
    current_version = '1.0.1'  # Текущая версия вашего приложения
    latest_version = get_latest_version()
    
    if latest_version and latest_version != current_version:
        result = messagebox.askyesno("Обновление доступно", f"Обнаружена новая версия: {latest_version}. Обновить сейчас?")
        if result:
            download_latest_version()
            os.remove('TSGobserver.exe')
            os.rename('TSGobserver_latest.exe', 'TSGobserver.exe')
            messagebox.showinfo("Обновление завершено", "Приложение обновлено до последней версии. Перезапустите его.")
            stop_monitoring()

# Окно приложения
root = Tk()
root.title("Наблюдатель")
root.geometry("400x200")
root.configure(bg="#2e2e2e")

status_var = StringVar()

creator_label = Label(root, text="Создатель: Mongren", fg="cyan", cursor="hand2", bg="#2e2e2e")
creator_label.pack(pady=10)
creator_label.bind("<Button-1>", open_link)

status_label = Label(root, textvariable=status_var, fg="white", bg="#2e2e2e")
status_label.pack(pady=10)

stop_button = Button(root, text="Остановить мониторинг", command=stop_monitoring, bg="#444444", fg="white")
stop_button.pack(pady=10)

# Добавляем обработчик для закрытия окна
root.protocol("WM_DELETE_WINDOW", on_closing)

# Проверка обновлений при запуске
check_for_updates()

# Мониторинг при запуске приложения
start_monitoring()

root.mainloop()
