import psutil

def get_hell_pids():
    ''' return list of "hell" pids '''
    for proc in psutil.process_iter(attrs=['pid', 'name', 'cmdline']):
        try:
            pinfo = proc.info
        except psutil.NoSuchProcess:
            return
        if pinfo['name'] == 'python3':
            file = pinfo['cmdline'][1]
            if file.startswith('/home/pi/hell/') and file.endswith('.py'):
                yield pinfo['pid'], file
        

def main():
    for pid in get_hell_pids():
        print(pid)
        
if __name__ == "__main__":
    main()