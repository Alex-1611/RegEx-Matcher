import multiprocessing
import psutil

main_process = psutil.Process()
nr_cores = multiprocessing.cpu_count() - 2


class RegEx:
    def __init__(self, reg):
        self.infix = reg
        self.prefix = None
        self.infix_to_prefix()

    def infix_to_prefix(self):
        def precedence(op):
            if op == '|':
                return 1
            if op == '+':
                return 2
            if op == '*':
                return 3
            return 0

        reg = self.infix
        stack = []
        result = []

        for i in range(len(reg)):
            if (i > 0 and reg[i] not in '|+*)' and reg[i - 1] not in '|+(*') or (
                    i > 0 and reg[i].isalnum() and reg[i - 1] == '*'):
                result.append('+')
            result.append(reg[i])
        reg = result
        result = []
        for i in reg[::-1]:
            if i == ')':
                stack.append(i)
            elif i == '(':
                while stack[-1] != ')':
                    result.append(stack.pop())
                stack.pop()
            elif i in '|+*':
                if not stack or precedence(stack[-1]) <= precedence(i):
                    stack.append(i)
                else:
                    while precedence(stack[-1]) > precedence(i):
                        result.append(stack.pop())
                        if not stack:
                            break
                    stack.append(i)
            else:
                result.append(i)
        while stack:
            result.append(stack.pop())
        self.prefix = ''.join(result[::-1])

    @staticmethod
    def is_nullable(reg):
        global main_process, nr_cores
        if reg == '':
            return False
        if reg == '.':
            return True
        if len(reg) == 1:
            return False
        if reg[0] == '+':
            nr_processes = len(main_process.children(recursive=True))
            if nr_processes < nr_cores:
                with multiprocessing.Pool(2) as pool:
                    results = pool.map(RegEx.is_nullable, [reg[1:RegEx.first_regex_index(reg) + 1],
                                                           reg[RegEx.first_regex_index(reg) + 1:]])
                return results[0] and results[1]
            else:
                return RegEx.is_nullable(reg[1:RegEx.first_regex_index(reg) + 1]) and RegEx.is_nullable(
                    reg[RegEx.first_regex_index(reg) + 1:])
        if reg[0] == '|':
            nr_processes = len(main_process.children(recursive=True))
            if nr_processes < nr_cores:
                with multiprocessing.Pool(2) as pool:
                    results = pool.map(RegEx.is_nullable, [reg[1:RegEx.first_regex_index(reg) + 1],
                                                           reg[RegEx.first_regex_index(reg) + 1:]])
                return results[0] or results[1]
            else:
                return RegEx.is_nullable(reg[1:RegEx.first_regex_index(reg) + 1]) or RegEx.is_nullable(
                    reg[RegEx.first_regex_index(reg) + 1:])
        if reg[0] == '*':
            return True
        return False

    @staticmethod
    def first_regex_index(reg):
        i = 1
        j = 1
        while i > 0:
            char = reg[j]
            j += 1

            if char in "|+":
                i += 1
            elif char == '*':
                pass
            else:
                i -= 1
        return j - 1

    @staticmethod
    def derive(regex, x):
        global main_process, nr_cores

        if regex == "":
            return ''
        if regex == '.':
            return ''
        if len(regex) == 1:
            return '.' if regex[0] == x else ''
        if regex[0] == '*':
            der = RegEx.derive(regex[1:], x)
            if der:
                return "+" + der + regex if der != '.' else regex
            else:
                return ""
        else:
            pos = RegEx.first_regex_index(regex)
            is_async = False
            async_der, pool, der1, der2 = None, None, None, None
            nr_processes = len(main_process.children(recursive=True))
            if nr_processes < nr_cores:
                is_async = True
                pool = multiprocessing.Pool(2)
                async_der = pool.starmap_async(RegEx.derive, [(regex[1:pos + 1], x), (regex[pos + 1:], x)])
                pool.close()
            else:
                der1 = RegEx.derive(regex[1:pos + 1], x)
                der2 = RegEx.derive(regex[pos + 1:], x)
            if regex[0] == '+':
                nul = True if RegEx.is_nullable(regex[1:pos + 1]) else False
                if is_async:
                    der1, der2 = async_der.get()
                    pool.join()
                if der1:
                    if (nul and der2) and der1 != ".":
                        return "|+" + der1 + regex[pos + 1:] + der2
                    elif nul and der2:
                        return "|" + regex[pos + 1:] + der2
                    elif der1 != ".":
                        return "+" + der1 + regex[pos + 1:]
                    else:
                        return regex[pos + 1:]
                elif nul and der2:
                    return der2
                else:
                    return ""
            else:
                if is_async:
                    der1, der2 = async_der.get()
                    pool.join()
                if der1 == der2 == "":
                    return ""
                if der1 == "" and der2 == ".":
                    return "."
                if der2 == "" and der1 == ".":
                    return "."
                if der1 == der2:
                    return der1
                return "|" + der1 + der2

    def match(self, string):
        reg = self.prefix
        for char in string:
            reg = RegEx.derive(reg, char)
            if reg == "":
                return False
        return RegEx.is_nullable(reg)
