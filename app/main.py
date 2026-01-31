import os
import sys


def find_executable(cmd):
    path_env=os.environ.get("PATH","")
    for directory in path_env.split(os.pathsep):
        if not directory:
            continue
        full_path=os.path.join(directory,cmd)
        if os.path.isfile(full_path) and os.access(full_path,os.X_OK):
            return full_path
    return None

def builtin_cd(path=None):
    if not path:
        return

    if path == "~":
        path = os.getenv("HOME")

    if os.path.isdir(path):
        os.chdir(path)
    else:
        print(f"cd: {path}: No such file or directory")

def parse_input(line):
    args = []
    current = ""
    in_single_quote = False

    i = 0
    while i < len(line):
        ch = line[i]

        if ch == "'":
            in_single_quote = not in_single_quote
        elif ch.isspace() and not in_single_quote:
            if current:
                args.append(current)
                current = ""
        else:
            current += ch

        i += 1

    if current:
        args.append(current)

    return args


def builtin_type(cmd):
    if cmd in BUILTINS:
        print(f"{cmd} is a shell builtin")
        return

    exe = find_executable(cmd)
    if exe:
        print(f"{cmd} is {exe}")
    else:
        print(f"{cmd}: not found")




BUILTINS = {
    "exit": lambda code=0, *_: sys.exit(int(code)),
    "echo": lambda *args: print(" ".join(args)),
    "pwd": lambda *_: print(os.getcwd()),
    "cd": lambda path=None, *_: builtin_cd(path),
    "type": lambda cmd, *_: builtin_type(cmd),

}


def main():
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()
        try:
            line = input()
        except EOFError:
            break
        usr_input= parse_input(line)
        if not usr_input:
            continue

        command = usr_input[0]
        args = usr_input[1:]
        if command in BUILTINS:
            BUILTINS[command](*args)
        else:
            exe_path = find_executable(command)
            if exe_path:
                pid = os.fork()
                if pid == 0:
                    os.execvp(command, [command] + args)
                else:
                    os.waitpid(pid, 0)
            else:
                print(f"{command}: command not found")


if __name__ == "__main__":
    main()
