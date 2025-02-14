from regex_matcher import RegEx

if __name__ == '__main__':
    reg = RegEx("a*|b*")
    print(reg.match("aaaaa"))  # Should print True
    print(reg.match("bbbbb"))  # Should print True
    print(reg.match("ab"))  # Should print False
    print(reg.match("ba"))  # Should print False