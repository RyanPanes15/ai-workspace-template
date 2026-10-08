class A:
    def m(self, x):
        if x:
            return 1
        return 2

def f():
    return A().m(1)
