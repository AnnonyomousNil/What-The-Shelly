import os
import sys
import readline


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
    in_double_quote = False

    i = 0
    while i < len(line):
        ch = line[i]

        if ch == "\\" and not in_single_quote:
            if i+1 < len(line):
                current += line[i+1]
                i+=2
                continue
            else:
                current += "\\"
                i+=1
                continue

        elif ch == "'" and not in_double_quote:
            in_single_quote = not in_single_quote

        elif ch == '"' and not in_single_quote:
            in_double_quote = not in_double_quote

        elif ch.isspace() and not in_single_quote and not in_double_quote:
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

def extract_redirection(args):
    outfile = None
    errfile = None
    outmode = "w"
    cleaned = []

    i=0
    while i < len(args):
        if args[i] in (">", "1>"):
            if i+1 >= len(args):
                print("syntax error: expected file after '>'")
                return [], None, None, None
            outfile = args[i+1]
            outmode = "w"
            i+=2
            continue

        elif args[i] in (">>", "1>>"):
            if i+1 >= len(args):
                print("syntax error: expected file after '>>'")
                return [], None, None, None
            outfile = args[i+1]
            outmode = "a"
            i+=2
            continue

        elif args[i] == "2>":
            if i+1 >= len(args):
                print("syntax error: expected file after '2>'")
                return [], None, None, None
            errfile = args[i + 1]
            outmode = "w"
            i += 2
            continue

        elif args[i] == "2>>":
            if i+1 >= len(args):
                print("syntax error: expected file after '2>>")
                return [], None, None, None
            errfile = args[i+1]
            outmode = "a"
            i+=2
            continue


        cleaned.append(args[i])
        i+=1

    return cleaned, outfile, errfile, outmode

def get_path_executables():
    executables = set()
    path_env = os.environ.get("PATH", "")

    for directory in path_env.split(os.pathsep):
        if not os.path.isdir(directory):
            continue

        try:
            for file in os.listdir(directory):
                full_path = os.path.join(directory, file)
                if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                    executables.add(file)
        except OSError:
            continue

    return executables



last_completion_prefix = None
last_completion_matches = []

def completer(text,state):

    global last_completion_prefix, last_completion_matches

    builtin_matches = [cmd for cmd in BUILTINS if cmd.startswith(text)]
    path_matches = [exe for exe in get_path_executables() if exe.startswith(text)]

    matches = sorted(set(builtin_matches + path_matches))

    if not matches:
        return None

    # Only one match → normal completion
    if len(matches) == 1:
        return (matches[0] + " ") if state == 0 else None

    # Multiple matches case
    if state == 0:
        # First TAB press
        if last_completion_prefix != text:
            # Ring bell
            sys.stdout.write("\x07")
            sys.stdout.flush()
            last_completion_prefix = text
            last_completion_matches = matches
            return None
        else:
            # Second TAB press → print matches
            print()
            print("  ".join(matches))
            print(f"$ {text}", end="", flush=True)
            last_completion_prefix = None
            last_completion_matches = []
            return None

    return None


BUILTINS = {
    "exit": lambda code=0, *_: sys.exit(int(code)),
    "echo": lambda *args: print(" ".join(args)),
    "pwd": lambda *_: print(os.getcwd()),
    "cd": lambda path=None, *_: builtin_cd(path),
    "type": lambda cmd, *_: builtin_type(cmd),

}


def main():
    readline.set_completer(completer)
    readline.parse_and_bind("tab: complete")

    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()
        try:
            line = input()
        except EOFError:
            break

        usr_input = parse_input(line)
        if not usr_input:
            continue

        command = usr_input[0]
        args = usr_input[1:]

        args, outfile, errfile, outmode  = extract_redirection(args)

        if command in BUILTINS:
            try:
                old_stdout = sys.stdout
                old_stderr = sys.stderr

                if outfile is not None:
                    sys.stdout = open(outfile, outmode)

                if errfile is not None:
                    sys.stderr = open(errfile, outmode)

                BUILTINS[command](*args)

            finally:
                if outfile is not None:
                    sys.stdout.close()
                    sys.stdout = old_stdout

                if errfile is not None:
                    sys.stderr.close()
                    sys.stderr = old_stderr



        else:
            exe_path = find_executable(command)
            if exe_path:
                pid = os.fork()
                if pid == 0:
                    if outfile is not None:
                        try:
                            flags = os.O_WRONLY | os.O_CREAT
                            if outmode == "w":
                                flags |= os.O_TRUNC
                            else:
                                flags |= os.O_APPEND

                            fd = os.open(outfile, flags, 0o666)
                            os.dup2(fd, 1)
                            os.close(fd)
                        except OSError as e:
                            print(f"{outfile}: {e}")
                            os._exit(1)
                    if errfile is not None:
                        try:
                            flags = os.O_WRONLY | os.O_CREAT
                            if outmode == "w":
                                flags |= os.O_TRUNC
                            else:
                                flags |= os.O_APPEND

                            fd_err = os.open(errfile, flags,  0o666)
                            os.dup2(fd_err, 2)
                            os.close(fd_err)
                        except OSError as e:
                            print(f"{errfile}: {e}")
                            os._exit(1)

                    os.execvp(command, [command] + args)
                else:
                    os.waitpid(pid, 0)
            else:
                print(f"{command}: command not found")


if __name__ == "__main__":
    main()
