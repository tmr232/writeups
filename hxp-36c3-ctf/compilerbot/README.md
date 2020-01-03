# compilerbot

Writeup by [@liadmord][@liad] and [@tmr232][@tamir]

<br/>

The premise of this exercise is pretty straight-forward. We were given access to a server running the following code, and the knowledge that the flag (`hxp{FLAG}`) is in a file named `flag` in the server's working directory.

```python
#!/usr/bin/env python3

import base64
import subprocess

code = base64.b64decode(input('> ')).decode()                                    # (1)
code = 'int main(void) {' + code.translate(str.maketrans('', '', '{#}')) + '}'   # (2)

result = subprocess.run(['/usr/bin/clang', '-x', 'c', '-std=c11', '-Wall',       # (3)
                         '-Wextra', '-Werror', '-Wmain', '-Wfatal-errors',
                         '-o', '/dev/null', '-'], input=code.encode(),
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        timeout=15.0)

if result.returncode == 0 and result.stdout.strip() == b'':                      # (4)
    print('OK')
else:
    print('Not OK')
```

The code (1) gets a string from the user; (2) removes all `{`, `#`, and `}` characters from the code, then place it inside the `main()` function; (3) compiles the _C_ code (not C++) with more warnings than the usual; (4) reports whether the compilation succeeded.
So we write code, the server compiles, and somehow we manage to leak the flag.

From the get go, it is clear to use that we need to `#include` the flag. But there is an issue - the code at (2) removes all `#` characters from our input, making it impossible to `#include`. Luckly, there's a way around it, and for once, our esoteric C knowledge came in handy. To enter the forbidden characters, we decided to use [digraphs][digraphs]. Digraphs (and trigraphs) are alternative token representations, added to C way back when to support some weird, non-standard 7-bit character encodings. The need is now gone, but the legacy tokens remain. With that in mind, replacing `#`, `{`, and `}` with `%:`, `<%`, and `%>` respectively allows us to `#include` and define functions:

```c
int main(void) {
%>

%: include "flag"

void f(void) <%
}
```

Or, after some "preprocessing" (the C preprocessor does not replace the alternative tokens, as they are valid C tokens):


```c
int main(void) {
}

hxp{FLAG}

void f(void) {
}
```

Great! This give us... absolutely nothing. `hxp` is not an existing identifier, `FLAG` is not an existing identifier (and possibly not even valid C, at the time we assumed it was a valid identifier name). The compiler hates us.
First, we tried to do something about the `hxp` at the start, thinking that if we isolate the `FLAG` part, we might have something to do with it. So we tried `#define hxp`, and many other preprocessor tricks, but didn't make any progress on that front.

At some point, we figured that if we can have it as a string, we might be able to do something with it. We didn't know what, but it was our only visible way forward. On the other hand, we had no idea how to do that, and StackOverflow was [not too helpful][SO Answer]. So we kept messing around, trying random preprocessor ideas until we came up with the following trick:

```c
#define test(a) const char flag_string[] = a;
#define to_string(a) test(#a)
#define hxp to_string(
#include "flag"
)
```

and after preprocessing using `clang -E` (assuming the contents of `flag` are `hxp{FLAG}`:

```c
const char flag_string[] = "{FLAG}";
```


If we understand it correctly, by replacing `hxp` with `to_string(` we allow calling a stringifying macro on `{FLAG}`. This works only because we know the flag starts with a valid identifier we can replace. Without that, we would not have been able to convert it to a string. Now all we need to do is find a way to get the string's contents...

At this point, while testing our code over on [Compiler Explorer][godbolt], we were getting tired of random warnings (unused variables, for example) slowing us down. So we went ahead and disabled all warnnings from within the code using `#pragma clang diagnostics ignote "-Weverything"`. This gave us some peace and quiet, as now only hard errors would kill the compilation.

With the compiler playing along, we were desperately looking for a way to get the flag, or at least its length. Anything!
After some experimentation, and many cycles of "I have a solution! Wait, no. I forget that we get the compiler's return code and not the program's. Sorry.", a new idea came to mind - maybe we can use compiler warnings to aid us? Lucky for us, today's compilers incorporate some fancy bounds-checking on array accesses. So by trying to access our `flag_string` at growing indices, we should be able to get the flag's length!

```c
#define test(a) const char flag_string[] = a;
#define to_string(a) test(#a)
#define hxp to_string(
#include "flag"
)

const char c = flag_string[INDEX];
```

After preprocessing:

```c
const char flag_string[] = "{FLAG}";

const char c = flag_string[INDEX];
```

And... It failed. While sneaking out of `main()` looked like a nice idea, we had to place this code inside a function. While `flag_string` is constant, it is not considered a "compile time constant" and therefore cannot be used to initialize another variable in the global scope.

```c
void f() {
  #define test(a) const char flag_string[] = a;
  #define to_string(a) test(#a)
  #define hxp to_string(
  #include "flag"
  )

  const char c = flag_string[INDEX];
}
```

That's better. Some automation (and runtime) later, we had the length! Now all we needed was the actual flag. For that, we used a slight variation of the same trick. This time, we were not using a number we control to access an array, but a character from the flag to access an array we control. 

```c
const char my_array[LENGTH] = {0};

my_array["{FLAG}"[INDEX]];
```

In each iteration, we try to guess the character at index `INDEX` in the flag. Assuming the flag is made of only letters, digits, and punctuation gives us a number between 33 and 126. If, for example, the character we're guessing is `A`, it's ordinal value (Python's `ord('A')`) is 65. This means that compilation will fail for every `LENGTH <= 65`. Once `LENGTH` reaches 66, compilation will succeed, we'll know the character is `A`, and increment `INDEX` to test the next character.
Note that here we no longer place `"{FLAG}"` in a variable, but use it as a literal. This is important, as clang will not warn on the out-of-bounds access if we dereference a variable (again, it is not a compile-time constant, so the compiler can't know).

Now all we had to do is enumerate and wait for the flag to appear on the screen. With our naive solution, it took quite a long time for the results to appear, and we wanted to get some sleep. So in the old tradition of hacking CTF solutions late at night, we just ran 7 instances at the same time, each one running from a different point. Parallelization works!

`hxp{Cl4n6_15_c00l_bu7_y0u_r34lly_0u6h7_70_7ry_gcc_-traditional-cpp_s0m3_d4y}`

The flag appeared, we posted it, first-blooded the challenge, and went to sleep.

Our full solution is [here][compilerbot.py], configured to work with a [local server][server.py] so that you can try it out. The solution is multithreaded to make it run faster than our original version; it is complete, where our original was edited and only provided either the length or the flag, but not both; but mostly the same code other than that.

[SO Answer]: https://stackoverflow.com/questions/1246301/c-c-can-you-include-a-file-into-a-string-literal 
[digraphs]: https://en.cppreference.com/w/cpp/language/operator_alternative
[compilerbot.py]: #
[server.py]: #
[@liad]: https://twitter.com/liadmord
[@tamir]: https://twitter.com/tmr232
