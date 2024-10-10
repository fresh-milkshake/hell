import psutil

for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
    if 'python' in proc.info['name'].lower():
        info = proc.info
        msg = (
            f"PID: {info['pid']}\n"
            f"Name: {info['name']}\n"
            f"Path: {info['cmdline'][1]}\n"
        )
        print(msg)
