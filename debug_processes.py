import psutil

pid = 0
for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
    if 'python' in proc.info['name'].lower():
        info = proc.info
        msg = (
            f"PID: {info['pid']}\n"
            f"Name: {info['name']}\n"
            f"Path: {info['cmdline'][1]}\n"
        )
        print(msg)
        pid = info['pid']


def get_process_info(pid: int):
    try:
        # Получаем объект процесса по его PID
        process = psutil.Process(pid)

        # Получаем использование CPU и памяти
        cpu_usage = process.cpu_percent(interval=1.0)  # Получаем процент загрузки CPU
        memory_usage = process.memory_info().rss / (1024 * 1024)  # Потребление памяти в мегабайтах
        process.exe()

        return {
            "cpu_usage_percent": cpu_usage,
            "memory_usage_mb": memory_usage
        }

    except psutil.NoSuchProcess:
        return {"error": f"Process with PID {pid} does not exist."}
    except Exception as e:
        return {"error": str(e)}


info = get_process_info(int(pid))
print(info)
